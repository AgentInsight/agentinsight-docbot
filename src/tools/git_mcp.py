"""GitMCPAdapter: 系统自带 MCP 子进程管理.

mcp-server-git + mcp-server-filesystem 由 server.py lifespan 启动子进程,
GitMCPAdapter 提供高级 API 供 skills/docbot/ 调用, 不直接管理子进程生命周期.

设计约束:
- 系统自带 MCP (非用户配置), 不入 mcp_configs 表, 所有用户共享
- 所有方法包裹在 trace_tool span 内 (as_type=tool)
- 敏感字段 (token/password/ssh_key) AES-GCM 加密存储 (属第 11 章安全硬约束)
- 仓库克隆到 temp/repos/{user_id}/{repo_id}/, 任务结束清理
- 仓库大小限制 max_repo_size_mb (默认 1024MB), 超出拒绝克隆
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import shutil
import stat
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from src.config.settings import Settings, get_settings
from src.observability.tracing import trace_tool

logger = logging.getLogger(__name__)

# 跳过的目录 (枚举文件时排除)
_SKIP_DIRS: frozenset[str] = frozenset({
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    ".next",
    "target",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
})

# 默认跳过的文件名
_SKIP_FILES: frozenset[str] = frozenset({
    ".DS_Store",
    "Thumbs.db",
})


class GitMCPAdapter:
    """用户代码仓库 MCP 适配器.

    系统自带 MCP (mcp-server-git + mcp-server-filesystem) 由 server.py lifespan
    启动子进程, 本类不管理子进程生命周期, 仅提供高级 API.

    所有方法都包裹在 trace_tool span 内.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._clone_root = Path(self.settings.repo_clone_root)

    def _repo_path(self, user_id: str, repo_id: str) -> Path:
        """计算仓库克隆路径: {clone_root}/{user_id}/{repo_id}/."""
        return self._clone_root / user_id / repo_id

    def _build_auth_url(
        self, repo_url: str, repo_config: dict
    ) -> tuple[str, str | None]:
        """构造认证 URL + 临时 SSH key 文件路径.

        支持:
        - none: 公开仓库, 直接返回原 URL
        - token: GitHub/GitLab PAT 嵌入 URL (https://oauth2:{token}@host/path)
        - password: Basic Auth 嵌入 URL (https://{user}:{pass}@host/path)
        - ssh_key: SSH key 写入临时文件, 返回原 SSH URL + key 文件路径

        Returns:
            (auth_url, ssh_key_path) - ssh_key_path 仅 ssh_key 模式非空
        """
        auth_type = (repo_config.get("auth_type") or "none").lower()
        if auth_type == "none":
            return repo_url, None

        if auth_type == "ssh_key":
            # SSH key 模式: URL 保持原样 (git+ssh), key 通过 GIT_SSH_COMMAND 注入
            return repo_url, None

        # token / password 模式: 解析 HTTPS URL 并嵌入凭据
        parts = urlsplit(repo_url)
        if parts.scheme not in ("http", "https"):
            # 非 HTTP(S) URL (如 git://), 不嵌入凭据, 调用方自行处理
            return repo_url, None

        if auth_type == "token":
            # token 模式: oauth2:{token} (GitHub/GitLab 兼容)
            token = repo_config.get("token") or ""
            if not token:
                return repo_url, None
            userinfo = f"oauth2:{quote(token, safe='')}"
        elif auth_type == "password":
            # password 模式: {user}:{pass}
            username = repo_config.get("username") or ""
            password = repo_config.get("password") or ""
            if not username and not password:
                return repo_url, None
            userinfo = f"{quote(username, safe='')}:{quote(password, safe='')}"
        else:
            return repo_url, None

        authed = urlunsplit(
            (parts.scheme, f"{userinfo}@{parts.netloc}", parts.path, parts.query, parts.fragment)
        )
        return authed, None

    def _write_ssh_key(self, ssh_key: str, passphrase: str | None = None) -> str:
        """将 SSH 私钥写入临时文件 (chmod 600).

        Returns:
            临时文件路径 (调用方负责清理)
        """
        # 确保 .ssh 目录存在
        ssh_dir = Path(tempfile.gettempdir()) / ".ssh_docbot"
        ssh_dir.mkdir(parents=True, exist_ok=True)

        key_path = ssh_dir / f"id_rsa_{uuid.uuid4().hex[:8]}"
        key_path.write_text(ssh_key, encoding="utf-8")
        # chmod 600 (SSH 强制要求)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

        # 写 passphrase 到环境变量 (GIT_SSH_COMMAND 读取)
        # 注意: passphrase 通过 ssh-add 或 ssh-agent 注入, 这里仅写 key 文件
        return str(key_path)

    def _build_ssh_command(self, key_path: str) -> str:
        """构造 GIT_SSH_COMMAND 环境变量值."""
        return f"ssh -i {key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes"

    async def _run_git(
        self,
        args: list[str],
        *,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 300,
    ) -> tuple[int, str, str]:
        """异步执行 git 命令.

        Returns:
            (returncode, stdout, stderr)
        """
        cmd = ["git"] + args
        logger.debug("执行 git 命令: %s (cwd=%s)", " ".join(cmd[:3]) + " ...", cwd)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **(env or {})},
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            return process.returncode or 0, stdout, stderr
        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            raise TimeoutError(f"git 命令超时 ({timeout}s): {' '.join(args[:3])}") from None

    def _check_repo_size(self, repo_path: Path) -> None:
        """校验已克隆仓库大小, 超出 max_repo_size_mb 抛 ValueError."""
        max_bytes = self.settings.max_repo_size_mb * 1024 * 1024
        total = 0
        for root, _dirs, files in os.walk(repo_path):
            # 跳过 .git 目录 (历史对象可能很大, 但不计入业务大小)
            if ".git" in Path(root).parts:
                continue
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    continue
        if total > max_bytes:
            raise ValueError(
                f"仓库大小 {total / (1024 * 1024):.2f}MB 超出限制 "
                f"{self.settings.max_repo_size_mb}MB"
            )

    def _check_git_domain(self, repo_url: str) -> None:
        """域名白名单校验 (防 LLM 注入内网渗透).

        大小写不敏感: host 与 allowed 列表均转小写后比较.
        """
        allowed = self.settings.allowed_git_domains_list
        if not allowed:
            return
        parts = urlsplit(repo_url)
        host = parts.hostname or ""
        if not host:
            return
        host_lower = host.lower()
        for d in allowed:
            d_lower = d.lower()
            if host_lower == d_lower or host_lower.endswith("." + d_lower):
                return
        raise ValueError(f"Git 域名 {host} 不在白名单: {allowed}")

    async def clone_repo(self, repo_config: dict, user_id: str, repo_id: str) -> str:
        """克隆仓库到 temp/repos/{user_id}/{repo_id}/, 已存在则 git pull.

        repo_config 字段:
            repo_url, default_branch, clone_depth, auth_type,
            token, username, password, ssh_key, ssh_passphrase

        Returns:
            仓库本地路径 (str)
        """
        async with trace_tool(
            name="docbot.git.clone_repo",
            input={"repo_id": repo_id, "user_id": user_id, "repo_url": repo_config.get("repo_url", "")},
            metadata={"tool_name": "git.clone", "auth_type": repo_config.get("auth_type", "none")},
            user_id=user_id,
        ) as span:
            repo_url = repo_config.get("repo_url", "")
            if not repo_url:
                raise ValueError("repo_url 不能为空")

            # 域名白名单校验
            self._check_git_domain(repo_url)

            target = self._repo_path(user_id, repo_id)
            # 确保父目录存在
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)

            auth_url, _ = self._build_auth_url(repo_url, repo_config)
            auth_type = (repo_config.get("auth_type") or "none").lower()
            ssh_key_path: str | None = None
            ssh_env: dict[str, str] = {}

            try:
                if auth_type == "ssh_key":
                    ssh_key = repo_config.get("ssh_key") or ""
                    if ssh_key:
                        ssh_key_path = self._write_ssh_key(
                            ssh_key, repo_config.get("ssh_passphrase")
                        )
                        ssh_env["GIT_SSH_COMMAND"] = self._build_ssh_command(ssh_key_path)

                # 已存在则 git pull
                if target.exists() and (target / ".git").exists():
                    logger.info("仓库已存在, 执行 git pull: %s", target)
                    rc, _out, err = await self._run_git(
                        ["pull", "--ff-only"],
                        cwd=target,
                        env=ssh_env,
                        timeout=300,
                    )
                    if rc != 0:
                        raise RuntimeError(f"git pull 失败: {err[:500]}")
                else:
                    # 不存在则 git clone
                    # 清理残留目录 (防止半克隆状态)
                    if target.exists():
                        await asyncio.to_thread(shutil.rmtree, target, ignore_errors=True)

                    clone_args = ["clone"]
                    depth = int(repo_config.get("clone_depth") or 0)
                    if depth > 0:
                        clone_args += ["--depth", str(depth)]
                    branch = repo_config.get("default_branch")
                    if branch:
                        clone_args += ["--branch", branch]
                    clone_args += [auth_url, str(target)]

                    rc, _out, err = await self._run_git(
                        clone_args, env=ssh_env, timeout=600
                    )
                    if rc != 0:
                        # 清理失败残留
                        await asyncio.to_thread(shutil.rmtree, target, ignore_errors=True)
                        raise RuntimeError(f"git clone 失败: {err[:500]}")

                # 校验仓库大小 (克隆后)
                self._check_repo_size(target)

                span.update(
                    output={"repo_path": str(target)},
                    metadata={"tool_name": "git.clone", "success": True},
                )
                return str(target)

            finally:
                # 清理临时 SSH key 文件
                if ssh_key_path:
                    try:
                        await asyncio.to_thread(os.remove, ssh_key_path)
                    except OSError:
                        pass

    async def list_files(self, repo_path: str, pattern: str = "**/*") -> list[str]:
        """枚举文件, 跳过 .git/node_modules/__pycache__/dist/build/.venv/.next/target/."""
        async with trace_tool(
            name="docbot.git.list_files",
            input={"repo_path": repo_path, "pattern": pattern},
            metadata={"tool_name": "git.list_files"},
        ) as span:
            root = Path(repo_path)
            if not root.exists():
                raise FileNotFoundError(f"仓库路径不存在: {repo_path}")

            def _walk() -> list[str]:
                files: list[str] = []
                for p in root.glob(pattern):
                    if not p.is_file():
                        continue
                    rel = p.relative_to(root)
                    parts = rel.parts
                    # 跳过指定目录下的文件
                    if any(part in _SKIP_DIRS for part in parts[:-1]):
                        continue
                    # 跳过指定文件名
                    if p.name in _SKIP_FILES:
                        continue
                    files.append(str(rel).replace("\\", "/"))
                return sorted(files)

            files = await asyncio.to_thread(_walk)
            span.update(
                output={"count": len(files)},
                metadata={"tool_name": "git.list_files", "success": True, "matched": len(files)},
            )
            return files

    async def read_file(self, repo_path: str, file_path: str, max_size_mb: int = 10) -> str:
        """读取文件内容, 限制 10MB."""
        async with trace_tool(
            name="docbot.git.read_file",
            input={"repo_path": repo_path, "file_path": file_path},
            metadata={"tool_name": "git.read_file"},
        ) as span:
            root = Path(repo_path)
            # 防路径穿越 (file_path 不能含 .. 或绝对路径)
            if file_path.startswith("/") or ".." in Path(file_path).parts:
                raise ValueError(f"非法 file_path: {file_path}")

            target = root / file_path
            # 二次校验: 解析后必须在 root 内
            try:
                target.resolve().relative_to(root.resolve())
            except ValueError as e:
                raise ValueError(f"file_path 越界仓库根目录: {file_path}") from e

            if not target.exists() or not target.is_file():
                raise FileNotFoundError(f"文件不存在: {file_path}")

            max_bytes = max_size_mb * 1024 * 1024
            size = target.stat().st_size
            if size > max_bytes:
                raise ValueError(
                    f"文件大小 {size / (1024 * 1024):.2f}MB 超出限制 {max_size_mb}MB"
                )

            content = await asyncio.to_thread(
                target.read_text, encoding="utf-8", errors="replace"
            )
            span.update(
                output={"size": size},
                metadata={"tool_name": "git.read_file", "success": True, "size_bytes": size},
            )
            return content

    async def get_file_history(
        self, repo_path: str, file_path: str, limit: int = 20
    ) -> list[dict]:
        """获取文件提交历史 (git log --format=%H|%an|%ae|%ad|%s)."""
        async with trace_tool(
            name="docbot.git.get_file_history",
            input={"repo_path": repo_path, "file_path": file_path, "limit": limit},
            metadata={"tool_name": "git.get_file_history"},
        ) as span:
            # 防路径穿越
            if file_path.startswith("/") or ".." in Path(file_path).parts:
                raise ValueError(f"非法 file_path: {file_path}")

            fmt = "%H|%an|%ae|%ad|%s"
            rc, stdout, stderr = await self._run_git(
                [
                    "log",
                    f"--format={fmt}",
                    "--date=iso",
                    f"-n{limit}",
                    "--",
                    file_path,
                ],
                cwd=repo_path,
                timeout=60,
            )
            if rc != 0:
                raise RuntimeError(f"git log 失败: {stderr[:500]}")

            history: list[dict] = []
            for line in stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split("|", 4)
                if len(parts) < 5:
                    continue
                history.append({
                    "commit": parts[0],
                    "author_name": parts[1],
                    "author_email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                })

            span.update(
                output={"count": len(history)},
                metadata={"tool_name": "git.get_file_history", "success": True, "matched": len(history)},
            )
            return history

    async def search_code(
        self, repo_path: str, query: str, max_results: int = 50
    ) -> list[dict]:
        """代码搜索 (git grep 模式).

        优先用 git grep (无需安装额外工具); 失败降级到 ripgrep (如已安装).
        Returns:
            [{"file": ..., "line": ..., "content": ...}]
        """
        async with trace_tool(
            name="docbot.git.search_code",
            input={"repo_path": repo_path, "query": query, "max_results": max_results},
            metadata={"tool_name": "git.search_code"},
        ) as span:
            if not query.strip():
                return []

            # git grep 在工作树中搜索 (含未提交变更)
            # -n: 行号 / -I: 忽略二进制 / --: 终止选项
            rc, stdout, stderr = await self._run_git(
                ["grep", "-n", "-I", query, "--", "*.py", "*.js", "*.ts", "*.go",
                 "*.java", "*.md", "*.yml", "*.yaml", "*.json", "*.toml"],
                cwd=repo_path,
                timeout=60,
            )
            # git grep 在无匹配时返回 1, 不是错误
            if rc not in (0, 1):
                raise RuntimeError(f"git grep 失败: {stderr[:500]}")

            results: list[dict] = []
            for line in stdout.splitlines():
                if not line.strip():
                    continue
                # 格式: file:line:content
                # 注意: 文件名可能含冒号, 仅按前两个冒号拆分
                first_colon = line.find(":")
                second_colon = line.find(":", first_colon + 1)
                if first_colon < 0 or second_colon < 0:
                    continue
                file = line[:first_colon]
                try:
                    line_no = int(line[first_colon + 1 : second_colon])
                except ValueError:
                    continue
                content = line[second_colon + 1 :]
                results.append({"file": file, "line": line_no, "content": content})
                if len(results) >= max_results:
                    break

            span.update(
                output={"count": len(results)},
                metadata={"tool_name": "git.search_code", "success": True, "matched": len(results)},
            )
            return results

    async def get_head_commit_hash(self, repo_path: str) -> str:
        """获取仓库当前 HEAD commit hash (P1-5.3.2 文档漂移检测用).

        使用 git rev-parse HEAD 获取当前 HEAD 的完整 commit hash.
        用于记录上次生成文档时的 commit, 下次同步时对比检测代码变更.

        Args:
            repo_path: 仓库本地路径

        Returns:
            完整 commit hash (40 字符 SHA-1)

        Raises:
            RuntimeError: git rev-parse 失败 (非 git 仓库 / 无提交)
        """
        async with trace_tool(
            name="docbot.git.get_head_commit_hash",
            input={"repo_path": repo_path},
            metadata={"tool_name": "git.get_head_commit_hash"},
        ) as span:
            rc, stdout, stderr = await self._run_git(
                ["rev-parse", "HEAD"],
                cwd=repo_path,
                timeout=30,
            )
            if rc != 0:
                raise RuntimeError(f"git rev-parse HEAD 失败: {stderr[:500]}")

            commit_hash = stdout.strip()
            if not commit_hash or len(commit_hash) < 7:
                raise RuntimeError(
                    f"git rev-parse HEAD 返回无效 hash: '{commit_hash}'"
                )

            span.update(
                output={"commit_hash": commit_hash[:12]},  # 仅记录短 hash 到 trace
                metadata={"tool_name": "git.get_head_commit_hash", "success": True},
            )
            return commit_hash

    async def list_changed_files(
        self,
        repo_path: str,
        from_commit: str,
        to_commit: str = "HEAD",
    ) -> list[str]:
        """获取两个 commit 之间变更的文件列表 (P1-5.3.2 文档漂移检测用).

        使用 git diff --name-only 列出 from_commit 到 to_commit 之间变更的文件.
        用于检测代码变更是否影响已生成文档引用的文件.

        Args:
            repo_path: 仓库本地路径
            from_commit: 起始 commit hash (上次文档生成时的 commit)
            to_commit: 结束 commit hash (默认 HEAD)

        Returns:
            变更文件路径列表 (相对路径)

        Raises:
            RuntimeError: git diff 失败 (无效 commit hash 等)
        """
        async with trace_tool(
            name="docbot.git.list_changed_files",
            input={
                "repo_path": repo_path,
                "from_commit": from_commit[:12],
                "to_commit": to_commit[:12],
            },
            metadata={"tool_name": "git.list_changed_files"},
        ) as span:
            # 安全校验: commit hash 应为十六进制字符 (防止命令注入)
            import re

            if not re.match(r"^[0-9a-fA-F]{7,40}$", from_commit):
                raise ValueError(f"非法 from_commit hash: {from_commit}")
            if not re.match(r"^[0-9a-fA-F]{7,40}$", to_commit):
                raise ValueError(f"非法 to_commit hash: {to_commit}")

            rc, stdout, stderr = await self._run_git(
                ["diff", "--name-only", from_commit, to_commit],
                cwd=repo_path,
                timeout=60,
            )
            if rc != 0:
                raise RuntimeError(f"git diff 失败: {stderr[:500]}")

            changed = [
                line.strip()
                for line in stdout.splitlines()
                if line.strip()
            ]

            span.update(
                output={"changed_file_count": len(changed)},
                metadata={"tool_name": "git.list_changed_files", "success": True},
            )
            return changed

    async def test_connection(self, repo_config: dict) -> dict[str, Any]:
        """通过 git ls-remote 探活 (不实际克隆).

        Returns:
            {"success": bool, "error": str | None}
            success=True 表示可访问, error 为 None
            success=False 表示不可访问, error 含具体失败原因
        """
        async with trace_tool(
            name="docbot.git.test_connection",
            input={"repo_url": repo_config.get("repo_url", ""), "auth_type": repo_config.get("auth_type", "none")},
            metadata={"tool_name": "git.test_connection"},
        ) as span:
            repo_url = repo_config.get("repo_url", "")
            if not repo_url:
                span.update(metadata={"tool_name": "git.test_connection", "success": False})
                return {"success": False, "error": "仓库 URL 为空"}

            try:
                self._check_git_domain(repo_url)
            except ValueError as e:
                span.update(metadata={"tool_name": "git.test_connection", "success": False, "reason": "domain_not_allowed"})
                return {"success": False, "error": str(e)}

            auth_url, _ = self._build_auth_url(repo_url, repo_config)
            auth_type = (repo_config.get("auth_type") or "none").lower()
            ssh_key_path: str | None = None
            ssh_env: dict[str, str] = {}

            try:
                if auth_type == "ssh_key":
                    ssh_key = repo_config.get("ssh_key") or ""
                    if ssh_key:
                        ssh_key_path = self._write_ssh_key(
                            ssh_key, repo_config.get("ssh_passphrase")
                        )
                        ssh_env["GIT_SSH_COMMAND"] = self._build_ssh_command(ssh_key_path)

                rc, _out, err = await self._run_git(
                    ["ls-remote", "--heads", auth_url],
                    env=ssh_env,
                    timeout=30,
                )
                success = rc == 0
                error_msg = None if success else (err.strip()[:500] if err.strip() else "git ls-remote 失败 (退出码非零)")
                span.update(
                    output={"success": success, "stderr_head": err[:200]},
                    metadata={
                        "tool_name": "git.test_connection",
                        "success": success,
                        "stderr_head": err[:200],
                    },
                )
                return {"success": success, "error": error_msg}
            except Exception as e:  # noqa: BLE001
                logger.warning("test_connection 异常: %s", e)
                span.update(
                    output={"success": False, "error": str(e)[:200]},
                    metadata={"tool_name": "git.test_connection", "success": False, "error": str(e)[:200]},
                )
                return {"success": False, "error": str(e)[:500]}
            finally:
                if ssh_key_path:
                    try:
                        await asyncio.to_thread(os.remove, ssh_key_path)
                    except OSError:
                        pass

    async def close(self) -> None:
        """清理资源 (不终止 MCP 子进程, 由 lifespan 管理).

        本类不持有子进程句柄, 此方法仅为接口对称.
        """
        # 主动释放可能的临时资源 (当前实现无长期持有资源)
        return


# ========== AES-GCM 加密辅助函数 ==========
# 用于 user_git_repos 表敏感字段 (token/password/ssh_key) 加密存储
# 密钥由 settings.git_credential_key 环境变量注入 (32 字节十六进制或 base64)
# 输出格式: base64(nonce + ciphertext + tag) (AESGCM 默认 tag=16 字节)


def _decode_credential_key(key: str) -> bytes:
    """解析加密密钥 (支持 32 字节 hex 字符串或 base64).

    Returns:
        32 字节原始密钥

    Raises:
        ValueError: 密钥格式无效或长度不为 32 字节
    """
    key = key.strip()
    # 优先尝试 hex (64 字符 = 32 字节)
    if len(key) == 64:
        try:
            return bytes.fromhex(key)
        except ValueError:
            pass
    # 尝试 base64
    try:
        decoded = base64.b64decode(key, validate=True)
        if len(decoded) == 32:
            return decoded
    except (ValueError, base64.binascii.Error):
        pass
    # 直接当 UTF-8 字符串取前 32 字节 (兼容用户填短密钥, 不推荐)
    raw = key.encode("utf-8")
    if len(raw) >= 32:
        return raw[:32]
    # 不足 32 字节, 用 PKCS7 填充到 32 字节 (兼容, 但不推荐生产用)
    padded = raw + b"\0" * (32 - len(raw))
    return padded


def encrypt_credential(plaintext: str | None, key: str | None) -> str | None:
    """AES-GCM 加密.

    key 为 32 字节十六进制字符串或 base64.
    返回 base64(nonce + ciphertext + tag).
    """
    if not plaintext or not key:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:
        raise RuntimeError("cryptography 库未安装, 无法加密敏感字段") from e

    key_bytes = _decode_credential_key(key)
    aesgcm = AESGCM(key_bytes)
    # 12 字节 nonce (AES-GCM 推荐), 随机生成
    nonce = os.urandom(12)
    # 明文编码
    plaintext_bytes = plaintext.encode("utf-8")
    # encrypt 返回 ciphertext + tag (tag 默认 16 字节)
    ct = aesgcm.encrypt(nonce, plaintext_bytes, associated_data=None)
    # 拼接 nonce + ciphertext + tag, base64 编码
    encrypted = base64.b64encode(nonce + ct).decode("ascii")
    return encrypted


def decrypt_credential(encrypted: str | None, key: str | None) -> str | None:
    """AES-GCM 解密.

    输入: base64(nonce + ciphertext + tag)
    """
    if not encrypted or not key:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:
        raise RuntimeError("cryptography 库未安装, 无法解密敏感字段") from e

    try:
        key_bytes = _decode_credential_key(key)
        aesgcm = AESGCM(key_bytes)
        raw = base64.b64decode(encrypted)
        # 前 12 字节 nonce, 其余 ciphertext + tag
        if len(raw) < 12 + 16:
            raise ValueError("加密数据长度不足")
        nonce = raw[:12]
        ct = raw[12:]
        plaintext_bytes = aesgcm.decrypt(nonce, ct, associated_data=None)
        return plaintext_bytes.decode("utf-8")
    except Exception as e:  # noqa: BLE001
        logger.warning("解密敏感字段失败: %s", e)
        return None


# ========== 模块级单例 (业务代码复用) ==========
_adapter: GitMCPAdapter | None = None


def get_git_mcp_adapter() -> GitMCPAdapter:
    """获取 GitMCPAdapter 单例 (复用, 避免重复创建)."""
    global _adapter
    if _adapter is None:
        _adapter = GitMCPAdapter()
    return _adapter


__all__ = [
    "GitMCPAdapter",
    "encrypt_credential",
    "decrypt_credential",
    "get_git_mcp_adapter",
]
