"""API 签名直填提取器 (O4-P0-C).

借鉴 Aider Repo Map: 函数签名直接从 AST/源码提取, 注入文档模板,
LLM 只补文字说明, 禁止自由描述签名.

针对 .NET 仓库: 提取 Controller 类的公共方法,
解析 HttpVerb 特性/路由/参数/返回值.
针对 Python 仓库 (FastAPI): 提取 @app.route/@router 装饰器签名.

设计约束:
- 仅在 api_doc 报告类型触发
- 签名表直填章节内容, LLM 不可修改
- 失败降级: 提取失败时返回空列表, 不阻断主流程

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SignatureExtractor:
    """从 code_graph 提取 API 接口签名 (支持 .NET Controller + FastAPI)."""

    def extract_api_signatures(
        self,
        code_learning: dict[str, Any],
        repo_path: str,
    ) -> list[dict[str, Any]]:
        """提取所有 API 接口签名 (支持 .NET Controller + FastAPI).

        Args:
            code_learning: 任务一代码学习产物
            repo_path: 仓库本地根路径

        Returns:
            签名字典列表, 每项含:
            - controller: 控制器类名 / 文件名
            - action: 方法名
            - http_method: GET/POST/PUT/DELETE/PATCH
            - route: 路由路径 (不含 controller 前缀, 由调用方拼接)
            - signature: 原始签名行
            - file_path: 文件相对路径
            - line: 行号
            - parameters: 参数列表 [{type, name, source}]
            - return_type: 返回类型
            - framework: "dotnet" / "fastapi"
        """
        if not isinstance(code_learning, dict):
            return []

        code_graph = code_learning.get("code_graph", {})
        if not isinstance(code_graph, dict):
            return []

        nodes = code_graph.get("nodes", [])
        if not isinstance(nodes, list):
            return []

        # 1. .NET Controller 方法提取
        dotnet_sigs = self._extract_dotnet_signatures(nodes, repo_path)

        # 2. FastAPI 路由提取 (Python)
        fastapi_sigs = self._extract_fastapi_signatures(nodes, repo_path)

        all_sigs = dotnet_sigs + fastapi_sigs
        logger.info(
            "O4-P0-C: 提取 %d 个 API 签名 (.NET=%d, FastAPI=%d)",
            len(all_sigs),
            len(dotnet_sigs),
            len(fastapi_sigs),
        )
        return all_sigs

    def _extract_dotnet_signatures(
        self,
        nodes: list[dict],
        repo_path: str,
    ) -> list[dict[str, Any]]:
        """从 .NET Controller 文件提取 Action 方法签名.

        策略:
        1. 从 code_graph nodes 筛选 class 节点且 name 以 "Controller" 结尾
        2. 读取对应源文件
        3. 解析 [HttpGet/HttpPost/...] 特性 + public 方法签名
        """
        signatures: list[dict[str, Any]] = []

        # 筛选 Controller 类节点
        controller_nodes: list[dict] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if (
                node.get("kind") == "class"
                and isinstance(node.get("name"), str)
                and node["name"].endswith("Controller")
            ):
                controller_nodes.append(node)

        if not controller_nodes:
            return []

        repo_root = Path(repo_path) if repo_path else None

        for ctrl in controller_nodes:
            ctrl_name = ctrl.get("name", "")
            ctrl_file = ctrl.get("file_path", "")
            if not ctrl_file or repo_root is None:
                continue

            # 读取 Controller 文件
            full_path = repo_root / ctrl_file
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:  # noqa: BLE001
                logger.debug("读取 Controller 文件失败 (跳过): %s, error=%s", ctrl_file, e)
                continue

            # 解析 [Route("...")] controller 级路由前缀
            route_prefix = self._extract_controller_route_prefix(content)

            # 解析 Action 方法
            actions = self._parse_dotnet_actions(content, ctrl_name, ctrl_file)
            for action in actions:
                # 拼接完整路由: route_prefix + action_route
                action["full_route"] = self._join_route(route_prefix, action.get("route", ""))
                action["framework"] = "dotnet"
                signatures.append(action)

        return signatures

    def _extract_controller_route_prefix(self, content: str) -> str:
        """提取 Controller 类级的 [Route("...")] 前缀."""
        # 匹配 [Route("api/user")] 或 [Route("[controller]")]
        match = re.search(r'\[Route\(\s*"([^"]+)"\s*\)\]', content)
        if match:
            route = match.group(1)
            # 替换 [controller] 占位符为不含 Controller 后缀的类名
            # (此处简化, 由调用方处理; 保留原值)
            return route
        return ""

    def _join_route(self, prefix: str, suffix: str) -> str:
        """拼接路由前缀和后缀."""
        if not prefix:
            return suffix or "/"
        if not suffix:
            return prefix
        # 去重斜杠
        if prefix.endswith("/") and suffix.startswith("/"):
            return prefix + suffix[1:]
        if not prefix.endswith("/") and not suffix.startswith("/"):
            return prefix + "/" + suffix
        return prefix + suffix

    def _parse_dotnet_actions(
        self,
        content: str,
        controller_name: str,
        file_path: str,
    ) -> list[dict[str, Any]]:
        """解析 .NET Controller 的 Action 方法 (HttpVerb 特性 + 方法签名)."""
        signatures: list[dict[str, Any]] = []
        lines = content.split("\n")

        # HttpVerb 特性正则: [HttpGet] / [HttpGet("path")] / [HttpPost("path")]
        http_verb_pattern = re.compile(
            r'\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch)\s*(?:\(\s*"([^"]*)"\s*\))?\]'
        )
        # 方法签名正则: public [async] Task<T> / T MethodName(params)
        method_pattern = re.compile(
            r'public\s+(?:async\s+)?(?:Task<(\w+(?:<[^>]+>)?)>|(\w+(?:<[^>]+>)?))\s+(\w+)\s*\(([^)]*)\)'
        )

        i = 0
        while i < len(lines):
            verb_match = http_verb_pattern.search(lines[i])
            if verb_match:
                http_method = verb_match.group(1).replace("Http", "").upper()
                route_attr = verb_match.group(2) or ""

                # 向下查找方法签名 (最多 5 行)
                for j in range(i + 1, min(i + 5, len(lines))):
                    method_match = method_pattern.search(lines[j])
                    if method_match:
                        return_type = method_match.group(1) or method_match.group(2) or "void"
                        action_name = method_match.group(3)
                        params_str = method_match.group(4)

                        signatures.append({
                            "controller": controller_name,
                            "action": action_name,
                            "http_method": http_method,
                            "route": route_attr,
                            "signature": lines[j].strip().rstrip("{").strip(),
                            "file_path": file_path,
                            "line": j + 1,
                            "parameters": self._parse_dotnet_params(params_str),
                            "return_type": return_type,
                        })
                        # 跳过已匹配的方法行
                        i = j
                        break
            i += 1
        return signatures

    def _parse_dotnet_params(self, params_str: str) -> list[dict[str, str]]:
        """解析 .NET 方法参数列表."""
        if not params_str.strip():
            return []

        params: list[dict[str, str]] = []
        # 简化分割: 按逗号分割 (不处理泛型中的逗号, 对 API 签名足够)
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue
            # 提取 [FromBody]/[FromQuery]/[FromRoute]/[FromHeader] 特性
            from_match = re.match(r'\[(FromBody|FromQuery|FromRoute|FromHeader)\]\s*', param)
            if from_match:
                param = param[from_match.end():]
                source = from_match.group(1)
            else:
                source = "unknown"

            # 默认参数值去除
            param = param.split("=")[0].strip()

            parts = param.split()
            if len(parts) >= 2:
                # 最后一个是参数名, 倒数第二个是类型
                param_name = parts[-1].rstrip("?")
                param_type = parts[-2]
                params.append({
                    "type": param_type,
                    "name": param_name,
                    "source": source,
                })
        return params

    def _extract_fastapi_signatures(
        self,
        nodes: list[dict],
        repo_path: str,
    ) -> list[dict[str, Any]]:
        """从 FastAPI 路由文件提取签名 (@app.route/@router 装饰器)."""
        signatures: list[dict[str, Any]] = []

        # 收集所有 Python 文件路径 (去重)
        file_paths: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            fp = node.get("file_path", "")
            if fp and fp.endswith(".py"):
                file_paths.add(fp)

        if not file_paths:
            return []

        repo_root = Path(repo_path) if repo_path else None
        if repo_root is None:
            return []

        # 路由装饰器正则: @app.get("path") / @router.post("path") / @router.api_route(...)
        route_pattern = re.compile(
            r'@(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']'
        )
        # 函数定义正则: async def name(params) / def name(params)
        func_pattern = re.compile(
            r'(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)'
        )

        for file_path in file_paths:
            full_path = repo_root / file_path
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue

            lines = content.split("\n")
            for i, line in enumerate(lines):
                route_match = route_pattern.search(line)
                if not route_match:
                    continue

                http_method = route_match.group(1).upper()
                route = route_match.group(2)

                # 向下查找函数定义 (最多 3 行)
                for j in range(i + 1, min(i + 3, len(lines))):
                    func_match = func_pattern.search(lines[j])
                    if func_match:
                        action_name = func_match.group(1)
                        params_str = func_match.group(2)
                        signatures.append({
                            "controller": file_path,
                            "action": action_name,
                            "http_method": http_method,
                            "route": route,
                            "full_route": route,
                            "signature": f"def {action_name}({params_str})",
                            "file_path": file_path,
                            "line": j + 1,
                            "parameters": self._parse_fastapi_params(params_str),
                            "return_type": "Any",
                            "framework": "fastapi",
                        })
                        break
        return signatures

    def _parse_fastapi_params(self, params_str: str) -> list[dict[str, str]]:
        """解析 FastAPI 函数参数列表 (简化)."""
        if not params_str.strip():
            return []

        params: list[dict[str, str]] = []
        for param in params_str.split(","):
            param = param.strip()
            if not param or param == "self":
                continue
            # FastAPI 常见: param: type = Body(...) / param: type = Query(...)
            parts = param.split(":")
            if len(parts) >= 2:
                name = parts[0].strip()
                type_part = parts[1].split("=")[0].strip()
                params.append({
                    "type": type_part,
                    "name": name,
                    "source": "body",  # 简化, 实际需解析 Depends/Query/Path/Body
                })
        return params

    def render_api_table(
        self,
        signatures: list[dict[str, Any]],
    ) -> str:
        """渲染 API 签名表 (直接注入文档, LLM 不修改).

        输出格式 (Markdown 表格):
            | API 编号 | 方法 | 路径 | Controller | Action | 签名 | 文件:行号 |
            |---------|------|------|-----------|--------|------|----------|
            | API-001 | GET  | `/api/...` | XxxController | ActionName | `public async Task<...> ActionName(...)` | path/to/Controller.cs:42 |
        """
        if not signatures:
            return "[无 API 接口签名 - 签名提取失败或仓库无 Controller]"

        lines = [
            "| API 编号 | 方法 | 路径 | Controller | Action | 签名 | 文件:行号 |",
            "|---------|------|------|-----------|--------|------|----------|",
        ]
        for i, sig in enumerate(signatures, 1):
            # 转义 | 字符, 避免破坏表格
            signature_safe = sig.get("signature", "").replace("|", "\\|")
            route = sig.get("full_route", sig.get("route", ""))
            lines.append(
                f"| API-{i:03d} | {sig['http_method']} | `{route}` | "
                f"{sig['controller']} | {sig['action']} | "
                f"`{signature_safe}` | "
                f"{sig['file_path']}:{sig['line']} |"
            )
        return "\n".join(lines)


__all__ = ["SignatureExtractor"]
