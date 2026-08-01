"""仓库克隆 / 文件枚举 / 分块 / 索引技能.

职责 (见 AGENTS.md 第 7 章代码仓库索引策略):
1. clone_repo: 通过 GitMCPAdapter 克隆 / 拉取仓库到 temp/repos/{user_id}/{repo_id}/
2. build_file_index: 枚举所有文件, 跳过 .git/node_modules/__pycache__/dist/build/.venv 等
3. select_key_files: 选取关键文件 (README / 入口文件 / 配置文件 / 核心模块)
4. read_files: 批量读取文件内容 (限制单文件 max_chars, 总 max_chars)
5. chunk_file: 按文件类型分块 (代码 AST / 配置整体 / 文档按章节)
6. index_repo_to_qdrant: 嵌入 + 写入 Qdrant, namespace=agentinsight-docbot:{user_id}:{repo_id}

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.observability.tracing import trace_chain, trace_tool
from src.tools.git_mcp import GitMCPAdapter

logger = logging.getLogger(__name__)

# 跳过的目录 (枚举文件时排除, 与 tools/git_mcp.py _SKIP_DIRS 一致)
_SKIP_DIRS: frozenset[str] = frozenset(
    {
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
        "Packages",  # O4: .NET NuGet 包缓存目录 (体积大, 无需索引)
    }
)

# 跳过的文件名
_SKIP_FILES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db"})

# 关键文件名 (select_key_files 优先选取) — 按 P1-5.2.3 优化扩展
# 新增: llms.txt / CLAUDE.md / CHANGELOG.md (业界代码理解 Agent 通用约定)
_KEY_FILE_NAMES: frozenset[str] = frozenset(
    {
        # 文档型 (最高优先级, 供任务一代码学习优先读入)
        "README.md",
        "README.rst",
        "README.txt",
        "README",
        "readme.md",
        "llms.txt",
        "AGENTS.md",
        "CLAUDE.md",
        "ARCHITECTURE.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        # 依赖清单 (高优先级)
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        # 入口文件 (中优先级)
        "main.py",
        "app.py",
        "server.py",
        "index.ts",
        "index.js",
        "main.go",
        "main.rs",
        "Application.java",
        # 配置文件 (中优先级)
        "settings.py",
        "config.py",
        "Dockerfile",
        "docker-compose.yml",
    }
)

# 关键文件优先级分组 (P1-5.2.3: 文档型 > 清单 > 入口 > 配置)
# 数值越小优先级越高; 未命中的关键文件默认优先级 50; 普通代码文件优先级 100
_PRIORITY_DOC_FILES: frozenset[str] = frozenset(
    {
        "llms.txt",
        "README.md",
        "README.rst",
        "README.txt",
        "README",
        "readme.md",
        "AGENTS.md",
        "CLAUDE.md",
        "ARCHITECTURE.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
    }
)
_PRIORITY_MANIFEST_FILES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
    }
)
_PRIORITY_ENTRY_FILES: frozenset[str] = frozenset(
    {
        "main.py",
        "app.py",
        "server.py",
        "index.ts",
        "index.js",
        "main.go",
        "main.rs",
        "Application.java",
    }
)
_PRIORITY_CONFIG_FILES: frozenset[str] = frozenset(
    {"settings.py", "config.py", "Dockerfile", "docker-compose.yml"}
)

# 关键文件扩展名 (代码入口 / 配置)
_KEY_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".md", ".rst"}
)

# 单文件读取最大字符数 (默认 200_000, 约 50K token)
_DEFAULT_MAX_CHARS_PER_FILE: int = 200_000

# 批量读取总字符数上限 (默认 500_000, 与 CONTEXT_MAX_CHARS 一致)
_DEFAULT_MAX_CHARS_TOTAL: int = 500_000

# 代码文件扩展名 (chunk_file 按函数 / 类分块)
_CODE_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java"}
)

# 配置文件扩展名 (chunk_file 整体作为一个 chunk)
_CONFIG_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env"}
)

# 文档文件扩展名 (chunk_file 按章节分块)
_DOC_FILE_EXTENSIONS: frozenset[str] = frozenset({".md", ".rst", ".txt"})


async def clone_repo(
    repo_config: dict,
    user_id: str,
    repo_id: str,
    *,
    settings: Any | None = None,
) -> str:
    """克隆 / 拉取仓库到 temp/repos/{user_id}/{repo_id}/.

    Args:
        repo_config: 仓库配置 (含 repo_url / auth_type / token / ...)
        user_id: 用户 ID
        repo_id: 仓库 ID
        settings: Settings 实例 (可选)

    Returns:
        仓库本地路径 (str)
    """
    adapter = GitMCPAdapter(settings)
    return await adapter.clone_repo(repo_config, user_id, repo_id)


async def list_files(
    repo_path: str,
    *,
    pattern: str = "**/*",
    settings: Any | None = None,
) -> list[str]:
    """枚举仓库所有文件 (跳过 _SKIP_DIRS / _SKIP_FILES).

    Args:
        repo_path: 仓库本地路径
        pattern: glob 模式 (默认 **/* 枚举所有)
        settings: Settings 实例 (可选, 仅用于 trace 上下文)

    Returns:
        相对路径文件列表
    """
    adapter = GitMCPAdapter(settings)
    async with trace_tool(
        name="docbot.repo.list_files",
        input={"repo_path": repo_path, "pattern": pattern},
    ) as span:
        files = await adapter.list_files(repo_path, pattern=pattern)
        # 过滤跳过目录与文件 (二次过滤, adapter 内部已过滤一次)
        filtered = [f for f in files if not _is_skipped(f)]
        span.update(output={"file_count": len(filtered)})
        return filtered


def _is_skipped(file_path: str) -> bool:
    """判断文件是否应跳过 (路径包含跳过目录或文件名命中跳过集合)."""
    parts = Path(file_path).parts
    for part in parts:
        if part in _SKIP_DIRS:
            return True
    return Path(file_path).name in _SKIP_FILES


async def build_file_index(
    repo_path: str,
    *,
    settings: Any | None = None,
) -> dict:
    """构建文件索引 (枚举 + 分类 + 大小统计).

    Args:
        repo_path: 仓库本地路径
        settings: Settings 实例 (可选)

    Returns:
        {
            "files": [{"path": str, "name": str, "size": int, "ext": str, "category": str}],
            "summary": str (人类可读摘要, 供 LLM prompt 使用),
            "total_size_bytes": int,
            "file_count": int,
        }
    """
    async with trace_chain(
        name="docbot.repo.build_file_index",
        input={"repo_path": repo_path},
    ) as span:
        files_raw = await list_files(repo_path, settings=settings)
        files: list[dict] = []
        total_size = 0
        for f in files_raw:
            try:
                full_path = Path(repo_path) / f
                size = full_path.stat().st_size if full_path.exists() else 0
            except OSError:
                size = 0
            total_size += size
            ext = Path(f).suffix.lower()
            files.append(
                {
                    "path": f,
                    "name": Path(f).name,
                    "size": size,
                    "ext": ext,
                    "category": _categorize_file(ext),
                }
            )

        summary = _build_summary(files, total_size)
        span.update(
            output={
                "file_count": len(files),
                "total_size_bytes": total_size,
            }
        )
        return {
            "files": files,
            "summary": summary,
            "total_size_bytes": total_size,
            "file_count": len(files),
        }


def _categorize_file(ext: str) -> str:
    """根据扩展名分类文件 (code / config / doc / other)."""
    if ext in _CODE_FILE_EXTENSIONS:
        return "code"
    if ext in _CONFIG_FILE_EXTENSIONS:
        return "config"
    if ext in _DOC_FILE_EXTENSIONS:
        return "doc"
    return "other"


def _build_summary(files: list[dict], total_size: int) -> str:
    """构建文件索引人类可读摘要 (供 LLM prompt 使用)."""
    by_category: dict[str, int] = {}
    for f in files:
        cat = f.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1
    parts = [
        f"文件总数: {len(files)}",
        f"总大小: {total_size} 字节 (~{total_size // 1024} KB)",
        "分类统计: " + ", ".join(f"{k}={v}" for k, v in sorted(by_category.items())),
    ]
    return "\n".join(parts)


def _file_priority(name: str) -> int:
    """返回关键文件优先级 (数值越小优先级越高).

    P1-5.2.3 优先级队列: 文档型(10) > 依赖清单(20) > 入口文件(30) > 配置文件(40)
    > 其他关键文件(50) > 普通代码文件(100)
    """
    if name in _PRIORITY_DOC_FILES:
        return 10
    if name in _PRIORITY_MANIFEST_FILES:
        return 20
    if name in _PRIORITY_ENTRY_FILES:
        return 30
    if name in _PRIORITY_CONFIG_FILES:
        return 40
    if name in _KEY_FILE_NAMES:
        return 50
    return 100


def _path_depth(path: str) -> int:
    """返回文件路径深度 (根目录=0, 越深数值越大; 用于同优先级内根目录优先)."""
    parts = Path(path).parts
    # 去掉文件名本身, 仅统计目录层数
    return max(0, len(parts) - 1)


# 按 report_type 提升路径/文件名匹配优先级的通用模式 (禁止绑定具体业务仓)
# 数值越小越优先; 在基础 priority 上叠加 type_boost (负值=提升)
_REPORT_TYPE_PATH_BOOSTS: dict[str, tuple[tuple[str, int], ...]] = {
    "api_doc": (
        ("controller", -40),
        ("router", -40),
        ("routes", -40),
        ("handler", -35),
        ("openapi", -40),
        ("swagger", -35),
        ("endpoint", -30),
        ("api/", -25),
        ("apis/", -25),
    ),
    "architecture": (
        ("docker-compose", -40),
        ("dockerfile", -40),
        ("helm/", -30),
        ("k8s/", -30),
        ("kubernetes/", -30),
        ("graph/", -25),
        ("builder", -20),
        ("deploy", -20),
    ),
    "design": (
        ("models/", -35),
        ("schemas/", -35),
        ("interfaces/", -35),
        ("dto", -25),
        ("entity", -20),
        ("domain/", -25),
    ),
    "requirements": (
        ("readme", -30),
        ("agents.md", -35),
        ("routes/", -25),
        ("router", -25),
        ("openapi", -25),
        ("docs/", -20),
    ),
    "testcase": (
        ("tests/", -45),
        ("test/", -45),
        ("_test.", -40),
        (".spec.", -40),
        (".test.", -40),
        ("__tests__/", -45),
        ("fixtures/", -25),
    ),
    "optimization": (
        ("cache/", -35),
        ("db/", -30),
        ("database/", -30),
        ("redis", -25),
        ("pool", -25),
        ("async", -15),
        ("queue", -20),
    ),
    "performance": (
        ("cache/", -30),
        ("db/", -30),
        ("database/", -30),
        ("hot", -15),
        ("bench", -25),
        ("perf", -25),
        ("profile", -25),
    ),
    "defect": (
        ("exception", -30),
        ("error", -25),
        ("middleware", -25),
        ("lock", -25),
        ("mutex", -25),
        ("security", -25),
        ("auth", -20),
        ("permission", -20),
        ("validate", -20),
        ("sanitiz", -20),
        ("resource", -15),
        ("pool", -15),
        ("async", -10),
        ("thread", -15),
        ("concurrent", -15),
    ),
}


def _report_type_boost(path: str, name: str, report_type: str | None) -> int:
    """按 report_type 对路径打分 boost (负值提升优先级); 未知类型返回 0."""
    if not report_type:
        return 0
    patterns = _REPORT_TYPE_PATH_BOOSTS.get(report_type)
    if not patterns:
        return 0
    haystack = f"{path}/{name}".replace("\\", "/").lower()
    best = 0
    for needle, boost in patterns:
        if needle.lower() in haystack:
            if boost < best:
                best = boost
    return best


def select_key_files(
    file_index: dict,
    *,
    max_files: int = 50,
    report_type: str | None = None,
) -> list[str]:
    """选取关键文件 (README / 入口 / 配置 / 核心模块).

    P1-5.2.3 优化: 按优先级分组选取 (文档型 > 依赖清单 > 入口 > 配置 > 其他关键 > 代码补足),
    同优先级内根目录文件优先 (路径深度小的优先), 再按路径字母序稳定排序.

    P0 (code-learning-v1): 传入 report_type 时, 按类型对路径模式叠加 boost,
    使 api_doc 更倾向 controller/router, testcase 更倾向 tests/ 等.

    Args:
        file_index: build_file_index 返回的索引
        max_files: 最大返回文件数 (避免 LLM 上下文超限)
        report_type: 报告类型 (可选, 用于按学习侧重调整选取)

    Returns:
        关键文件路径列表 (相对路径)
    """
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    # (effective_priority, depth, path)
    key_files: list[tuple[int, int, str]] = []
    other_files: list[tuple[int, int, str]] = []
    for f in files:
        if not isinstance(f, dict):
            continue
        name = f.get("name", "")
        path = f.get("path", "")
        ext = f.get("ext", "")
        base_priority = _file_priority(name)
        boost = _report_type_boost(path, name, report_type)
        # 类型命中的普通代码文件也进入候选 (否则仅靠补足槽位)
        effective = base_priority + boost
        depth = _path_depth(path)
        entry = (effective, depth, path)
        if base_priority < 100 or boost < 0:
            key_files.append(entry)
        elif ext in _KEY_FILE_EXTENSIONS:
            other_files.append(entry)
    key_files.sort()
    other_files.sort(key=lambda x: (x[0], x[1], x[2]))
    result = [p for _, _, p in key_files[:max_files]]
    if len(result) < max_files:
        remaining = [p for _, _, p in other_files if p not in result]
        result.extend(remaining[: max_files - len(result)])
    return result

async def read_files(
    repo_path: str,
    file_paths: list[str],
    *,
    max_chars_per_file: int = _DEFAULT_MAX_CHARS_PER_FILE,
    max_chars_total: int = _DEFAULT_MAX_CHARS_TOTAL,
    settings: Any | None = None,
) -> str:
    """批量读取文件内容 (限制单文件与总字符数).

    Args:
        repo_path: 仓库本地路径
        file_paths: 文件路径列表 (相对路径)
        max_chars_per_file: 单文件最大字符数
        max_chars_total: 总字符数上限
        settings: Settings 实例 (可选)

    Returns:
        拼接后的文件内容 (格式: ``== {path} ==\n{content}\n\n``)
    """
    adapter = GitMCPAdapter(settings)
    parts: list[str] = []
    total_chars = 0
    async with trace_chain(
        name="docbot.repo.read_files",
        input={"file_count": len(file_paths), "repo_path": repo_path},
    ) as span:
        for path in file_paths:
            if total_chars >= max_chars_total:
                break
            try:
                content = await adapter.read_file(repo_path, path)
            except Exception as e:  # noqa: BLE001
                logger.warning("读取文件失败 (跳过): %s, error: %s", path, e)
                continue
            if len(content) > max_chars_per_file:
                content = content[:max_chars_per_file] + "\n... (truncated)"
            parts.append(f"== {path} ==\n{content}")
            total_chars += len(content)
        span.update(
            output={
                "files_read": len(parts),
                "total_chars": total_chars,
            }
        )
        return "\n\n".join(parts)


def chunk_file(
    file_path: str,
    content: str,
    *,
    max_chunk_size: int = 4000,
) -> list[dict]:
    """按文件类型分块 (代码 AST / 配置整体 / 文档按章节).

    Args:
        file_path: 文件路径 (用于推断类型)
        content: 文件内容
        max_chunk_size: 单 chunk 最大字符数 (超出则按字符切分)

    Returns:
        [{"chunk_type": str, "content": str, "metadata": dict}]
    """
    ext = Path(file_path).suffix.lower()
    if ext in _CODE_FILE_EXTENSIONS:
        return _chunk_code_file(file_path, content, max_chunk_size)
    if ext in _CONFIG_FILE_EXTENSIONS:
        return _chunk_config_file(file_path, content, max_chunk_size)
    if ext in _DOC_FILE_EXTENSIONS:
        return _chunk_doc_file(file_path, content, max_chunk_size)
    # 其他类型整体作为一个 chunk
    return [
        {
            "chunk_type": "whole",
            "content": content[:max_chunk_size],
            "metadata": {"file_path": file_path, "ext": ext},
        }
    ]


def _chunk_code_file(file_path: str, content: str, max_size: int) -> list[dict]:
    """代码文件分块 (按函数 / 类, 简化版: 按顶级 def/class 行分割)."""
    lines = content.split("\n")
    chunks: list[dict] = []
    current: list[str] = []
    current_header = "header"
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("def ", "class ", "async def ")) and current:
            chunks.append(
                {
                    "chunk_type": "code_block",
                    "content": "\n".join(current)[:max_size],
                    "metadata": {
                        "file_path": file_path,
                        "header": current_header,
                    },
                }
            )
            current = [line]
            current_header = stripped[:80]
        else:
            current.append(line)
    if current:
        chunks.append(
            {
                "chunk_type": "code_block",
                "content": "\n".join(current)[:max_size],
                "metadata": {"file_path": file_path, "header": current_header},
            }
        )
    return chunks or [
        {
            "chunk_type": "code_block",
            "content": content[:max_size],
            "metadata": {"file_path": file_path},
        }
    ]


def _chunk_config_file(file_path: str, content: str, max_size: int) -> list[dict]:
    """配置文件分块 (整体作为一个 chunk)."""
    return [
        {
            "chunk_type": "config",
            "content": content[:max_size],
            "metadata": {"file_path": file_path},
        }
    ]


def _chunk_doc_file(file_path: str, content: str, max_size: int) -> list[dict]:
    """文档文件分块 (按 Markdown 标题层级)."""
    lines = content.split("\n")
    chunks: list[dict] = []
    current: list[str] = []
    current_title = "intro"
    for line in lines:
        if line.startswith("#"):
            if current:
                chunks.append(
                    {
                        "chunk_type": "doc_section",
                        "content": "\n".join(current)[:max_size],
                        "metadata": {
                            "file_path": file_path,
                            "title": current_title,
                        },
                    }
                )
            current = [line]
            current_title = line.lstrip("# ").strip()[:80]
        else:
            current.append(line)
    if current:
        chunks.append(
            {
                "chunk_type": "doc_section",
                "content": "\n".join(current)[:max_size],
                "metadata": {"file_path": file_path, "title": current_title},
            }
        )
    return chunks or [
        {
            "chunk_type": "doc_section",
            "content": content[:max_size],
            "metadata": {"file_path": file_path},
        }
    ]


async def index_repo_to_qdrant(
    repo_path: str,
    *,
    user_id: str,
    repo_id: str,
    agent_id: str = "agentinsight-docbot",
    settings: Any | None = None,
) -> dict:
    """将仓库代码索引到 Qdrant (namespace=agentinsight-docbot:{user_id}:{repo_id}).

    Args:
        repo_path: 仓库本地路径
        user_id: 用户 ID
        repo_id: 仓库 ID
        agent_id: Agent 标识 (默认 agentinsight-docbot)
        settings: Settings 实例 (可选)

    Returns:
        {"namespace": str, "indexed_count": int, "errors": list[str]}
    """
    namespace = f"{agent_id}:{user_id}:{repo_id}"
    async with trace_chain(
        name="docbot.repo.index_to_qdrant",
        input={
            "repo_path": repo_path,
            "namespace": namespace,
            "user_id": user_id,
            "repo_id": repo_id,
        },
    ) as span:
        # 延迟导入, 避免 skills 模块加载时强依赖 rag.* (与现有 agent 文件一致)
        try:
            from src.rag.qdrant_manager import QdrantManager
        except Exception as e:  # noqa: BLE001
            logger.warning("RAG 模块导入失败 (跳过索引): %s", e)
            span.update(metadata={"success": False, "error": str(e)})
            return {
                "namespace": namespace,
                "indexed_count": 0,
                "errors": [f"rag_module_unavailable: {e}"],
            }

        try:
            qdrant_mgr = QdrantManager(settings)
            await qdrant_mgr.ensure_collection()
        except Exception as e:  # noqa: BLE001
            logger.warning("RAG 客户端初始化失败 (跳过索引): %s", e)
            span.update(metadata={"success": False, "error": str(e)})
            return {
                "namespace": namespace,
                "indexed_count": 0,
                "errors": [f"rag_init_failed: {e}"],
            }

        file_index = await build_file_index(repo_path, settings=settings)
        files = file_index.get("files", [])
        indexed_count = 0
        errors: list[str] = []
        # 批量累积点, 每 100 个点批量写入一次 (减少 Qdrant upsert 往返)
        batch_points: list[dict[str, Any]] = []
        batch_size = 100
        for f in files:
            if not isinstance(f, dict):
                continue
            file_path = f.get("path", "")
            try:
                adapter = GitMCPAdapter(settings)
                content = await adapter.read_file(repo_path, file_path)
            except Exception as e:  # noqa: BLE001
                errors.append(f"read_failed:{file_path}:{e}")
                continue
            chunks = chunk_file(file_path, content)
            for chunk in chunks:
                chunk_content = chunk.get("content", "")
                if not chunk_content:
                    continue
                batch_points.append(
                    {
                        "content": chunk_content,
                        "metadata": {
                            "user_id": user_id,
                            "repo_id": repo_id,
                            "file_path": file_path,
                            "language": f.get("ext", "").lstrip("."),
                            "chunk_type": chunk.get("chunk_type", ""),
                        },
                    }
                )
                if len(batch_points) >= batch_size:
                    try:
                        await qdrant_mgr.upsert_points(
                            namespace=namespace,
                            points=batch_points,
                            user_id=user_id,
                        )
                        indexed_count += len(batch_points)
                    except Exception as e:  # noqa: BLE001
                        errors.append(f"index_failed:{file_path}:{e}")
                    batch_points.clear()
        # 写入剩余点
        if batch_points:
            try:
                await qdrant_mgr.upsert_points(
                    namespace=namespace,
                    points=batch_points,
                    user_id=user_id,
                )
                indexed_count += len(batch_points)
            except Exception as e:  # noqa: BLE001
                errors.append(f"index_failed:final_batch:{e}")

        span.update(
            output={
                "indexed_count": indexed_count,
                "error_count": len(errors),
            },
            metadata={"namespace": namespace, "success": True},
        )
        return {
            "namespace": namespace,
            "indexed_count": indexed_count,
            "errors": errors,
        }


__all__ = [
    "build_file_index",
    "chunk_file",
    "clone_repo",
    "index_repo_to_qdrant",
    "list_files",
    "read_files",
    "select_key_files",
]
