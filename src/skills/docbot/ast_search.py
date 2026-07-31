"""v8-P0-C: AST 结构感知搜索 API (借鉴 AutoCodeRover + SWE-agent).

提供结构感知搜索函数, 枚举所有 Controller/路由方法/枚举定义,
解决"接口发现不完整"和"errorCode 幻觉"问题.

借鉴:
- AutoCodeRover: AST 搜索 API (结构感知, 精确定位符号, 而非全文 grep)
- SWE-agent: search_dir 风格 (通用扫描所有代码文件, 不限定特定目录)

设计约束 (遵循 AGENTS.md):
- Python >=3.11, 用绝对导入, type hints 严格
- 失败降级, 不阻断主流程, 日志使用 logger.warning / logger.info
- 不硬编码任何项目特定内容 (路径 / 类名 / 枚举名 / 字段名)
- 通用扫描所有代码文件, 不限定特定目录 (如不预设 Controllers/ 路径)
- 复用 repo_map._get_parser_cached / _EXT_TO_LANG, 不重定义

支持语言:
- HTTP 端点: C# / Python / Java / TypeScript / JavaScript / Go
- 枚举定义: C# / Python / Java

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from src.skills.docbot.repo_map import _EXT_TO_LANG, _get_parser_cached

logger = logging.getLogger(__name__)

# v8-P0-C: 需跳过的目录 (构建产物 / 依赖 / VCS / 缓存等)
# 设计理由: 借鉴 SWE-agent search_dir 的过滤策略, 避免扫描无关目录
_SKIP_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        ".git",
        "dist",
        "build",
        "__pycache__",
        "bin",
        "obj",
        ".venv",
        "venv",
        ".next",
        "target",
        ".idea",
        ".vscode",
    }
)

# v8-P0-C: 待扫描的代码扩展名 (HTTP 端点 + 枚举定义搜索范围)
# 设计理由: 覆盖主流后端语言, 不预设特定项目结构
_CODE_EXTENSIONS: frozenset[str] = frozenset({".cs", ".py", ".java", ".ts", ".js", ".go"})


# ---------------------------------------------------------------------------
# 辅助函数 (私有, 不对外暴露)
# ---------------------------------------------------------------------------


def _should_skip(path: Path) -> bool:
    """判断路径是否应跳过 (构建产物 / 依赖 / VCS 目录).

    设计理由: 与 repo_loader.build_file_index 的跳过逻辑保持一致,
    避免扫描 bin/obj/node_modules 等非业务目录产生噪声.
    """
    return any(part in _SKIP_DIRS for part in path.parts)


def _to_rel_path(file_path: Path, repo: Path) -> str:
    """计算相对路径, 统一用 / 分隔 (跨平台兼容 Windows 反斜杠).

    设计理由: prompt 注入文本需统一路径分隔符, 避免 LLM 因路径格式差异误解.
    """
    try:
        return str(file_path.relative_to(repo)).replace("\\", "/")
    except ValueError:
        # file_path 不在 repo 下时, 退化为绝对路径
        return str(file_path).replace("\\", "/")


def _line_of(content: str, offset: int) -> int:
    """根据字符偏移计算行号 (1-based).

    设计理由: 正则 match 的 start() 是字符偏移, 需转换为行号供 prompt 引用.
    """
    return content.count("\n", 0, offset) + 1


def _iter_code_files(
    repo_path: str, file_index: dict | None = None
) -> Iterator[tuple[Path, str, str, str]]:
    """迭代代码文件, 返回 (abs_path, rel_path, ext, lang) 元组.

    设计理由 (借鉴 SWE-agent search_dir):
    - 若提供 file_index (repo_loader.build_file_index 返回), 复用其文件列表, 避免重复枚举
    - 若未提供 file_index, 直接 rglob 仓库路径, 通用扫描所有代码文件
    - 两种模式均跳过 _SKIP_DIRS 中的目录

    Args:
        repo_path: 仓库本地路径
        file_index: 文件索引 (可选, 含 "files" 列表, 每项有 path/ext 字段)

    Yields:
        (abs_path, rel_path, ext, lang) 元组
    """
    repo = Path(repo_path)

    if file_index is not None and isinstance(file_index, dict):
        # 复用 file_index 中的文件列表 (避免重复 rglob)
        files = file_index.get("files", [])
        for f in files:
            if not isinstance(f, dict):
                continue
            ext = (f.get("ext") or "").lower()
            if ext not in _CODE_EXTENSIONS:
                continue
            rel = f.get("path", "")
            if not rel:
                continue
            abs_path = repo / rel
            if _should_skip(abs_path):
                continue
            lang = _EXT_TO_LANG.get(ext, "")
            if not lang:
                continue
            yield abs_path, rel, ext, lang
    else:
        # 降级: 直接 rglob 仓库路径 (通用扫描, 不限定特定目录)
        for ext in _CODE_EXTENSIONS:
            for file_path in repo.rglob(f"*{ext}"):
                if _should_skip(file_path):
                    continue
                rel = _to_rel_path(file_path, repo)
                lang = _EXT_TO_LANG.get(ext, "")
                if not lang:
                    continue
                yield file_path, rel, ext, lang


# ---------------------------------------------------------------------------
# 公共 API: HTTP 端点搜索
# ---------------------------------------------------------------------------


def search_http_endpoints(repo_path: str, file_index: dict | None = None) -> list[dict]:
    """v8-P0-C: 搜索所有 HTTP 端点 (Controller Action / 路由方法).

    通用扫描所有代码文件 (.cs/.py/.java/.ts/.js/.go), 枚举 HTTP 端点,
    解决"接口发现不完整"问题 (确保文档覆盖每一个真实端点).

    支持框架:
    - C#: [HttpGet]/[HttpPost]/[Route] + [ApiController] (ASP.NET Core)
    - Python: @app.get/@router.post (FastAPI) / path("", views.xxx) (Django)
    - Java: @GetMapping/@PostMapping/@RequestMapping (Spring)
    - TypeScript/JavaScript: app.get/router.post (Express/Koa) / @Get/@Post (NestJS)
    - Go: r.GET/r.POST (gin) / http.HandleFunc (net/http)

    设计理由 (借鉴 AutoCodeRover AST 搜索 API):
    - 结构感知: 解析注解 / 装饰器 / 路由注册语句, 而非全文 grep 关键词
    - 通用扫描: 不预设 Controllers/ 路径, 避免遗漏非标准目录结构的端点
    - 失败降级: 单文件解析失败不阻断整体扫描

    Args:
        repo_path: 仓库本地路径
        file_index: 文件索引 (可选, 含 "files" 列表; 提供时复用, 避免重复枚举)

    Returns:
        端点列表, 每项格式:
        {
            "file_path": "相对路径",
            "lang": "csharp|python|java|typescript|javascript|go",
            "class_name": "类名 (无类时为空字符串)",
            "method_name": "方法名",
            "http_method": "GET|POST|PUT|DELETE|PATCH",
            "route": "/api/...",
            "line": 42,
            "summary": "方法签名行"
        }
    """
    endpoints: list[dict] = []

    for abs_path, rel_path, ext, lang in _iter_code_files(repo_path, file_index):
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            logger.debug("v8-P0-C: 读取文件失败 (跳过) %s: %s", rel_path, e)
            continue

        try:
            if ext == ".cs":
                endpoints.extend(_search_csharp_endpoints(content, rel_path, lang))
            elif ext == ".py":
                endpoints.extend(_search_python_endpoints(content, rel_path, lang))
            elif ext == ".java":
                endpoints.extend(_search_java_endpoints(content, rel_path, lang))
            elif ext in (".ts", ".js"):
                # TypeScript 和 JavaScript 共用同一解析器 (Express/Koa/Nest 模式一致)
                endpoints.extend(_search_typescript_endpoints(content, rel_path, lang))
            elif ext == ".go":
                endpoints.extend(_search_go_endpoints(content, rel_path, lang))
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P0-C: 解析端点失败 (跳过, 不阻断) %s: %s", rel_path, e)

    # v12-P0-2: 端点去噪 — 过滤 Admin/Django 假阳性 + 非 /api/ 垃圾路径
    before = len(endpoints)
    endpoints = filter_api_doc_endpoints(endpoints)
    logger.info(
        "v8-P0-C: 搜索到 %d 个 HTTP 端点 (过滤后 %d, repo=%s)",
        before,
        len(endpoints),
        repo_path,
    )
    return endpoints


def filter_api_doc_endpoints(endpoints: list[dict]) -> list[dict]:
    """v12-P0-2: 过滤适合写入 API/需求文档的端点.

    规则 (借鉴 RepoAgent 仅保留目标对象 + Aider 签名白名单):
    1. 优先保留 *Controller.cs 且 route 以 /api/ 开头的端点
    2. 丢弃 Admin/ 下 Django 路由 (login/, admin/, <path:...> 等)
    3. 丢弃明显拼接错误的短路径 (无 /api/ 前缀且无 class_name)
    4. 按 (http_method, route.lower()) 去重
    """
    if not endpoints:
        return []

    filtered: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for ep in endpoints:
        if not isinstance(ep, dict):
            continue
        route = str(ep.get("route") or "").strip()
        file_path = str(ep.get("file_path") or "").replace("\\", "/")
        class_name = str(ep.get("class_name") or "")
        http_method = str(ep.get("http_method") or "").upper()

        # 丢弃 Admin 子项目 Django 路由
        fp_lower = file_path.lower()
        if "/admin/" in f"/{fp_lower}" or fp_lower.startswith("admin/"):
            continue
        if route.startswith(("admin/", "login/", "logout/", "password_reset/", "client/")):
            continue
        if "<path:" in route or "<int:" in route:
            continue

        # API 文档核心: 保留 /api/ 路由; 若有 Controller 类则放宽
        route_l = route.lower()
        is_api_route = route_l.startswith("/api/") or route_l.startswith("api/")
        is_controller = bool(class_name) and class_name.endswith("Controller")
        if not is_api_route and not is_controller:
            continue
        if not is_api_route and is_controller:
            # Controller 但路由未拼出 /api/ → 丢弃 (通常是 class_route 丢失的残片)
            continue

        # 规范化: 确保以 / 开头
        if route and not route.startswith("/"):
            route = "/" + route
            ep = {**ep, "route": route}
            route_l = route.lower()

        key = (http_method, route_l)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(ep)

    return filtered


def render_api_inventory_markdown(endpoints: list[dict]) -> str:
    """v12: 将端点列表渲染为确定性 API 清单 Markdown 表 (LLM 不可修改).

    输出格式对齐 Trae 参考文档: | 标识 | 方法 | 路径 | 描述 | 鉴权 |
    """
    if not endpoints:
        return "(未扫描到 HTTP 端点)"

    lines: list[str] = [
        "| 标识 | 方法 | 路径 | 描述 | 鉴权 |",
        "|------|------|------|------|------|",
    ]
    for i, ep in enumerate(endpoints, 1):
        method = str(ep.get("http_method") or "").upper()
        route = str(ep.get("route") or "")
        action = str(ep.get("method_name") or ep.get("action") or "")
        ctrl = str(ep.get("class_name") or ep.get("controller") or "")
        desc = f"{ctrl}.{action}" if ctrl and action else (action or ctrl or "-")
        lines.append(f"| API-{i:03d} | {method} | `{route}` | {desc} | Bearer |")
    return "\n".join(lines)


def render_feature_list_from_endpoints(endpoints: list[dict]) -> str:
    """v12: 从端点按 Controller 分组生成需求文档功能列表 (FR 骨架).

    借鉴 RepoAgent 按对象分组 + Trae PRD 功能表格式.
    """
    if not endpoints:
        return "(未扫描到功能端点)"

    by_ctrl: dict[str, list[dict]] = {}
    for ep in endpoints:
        if not isinstance(ep, dict):
            continue
        ctrl = str(ep.get("class_name") or ep.get("controller") or "Unknown")
        by_ctrl.setdefault(ctrl, []).append(ep)

    lines: list[str] = [
        "| 编号 | 模块 | 功能名 | 优先级 | 关联接口 |",
        "|------|------|--------|--------|----------|",
    ]
    fr_idx = 1
    for ctrl, eps in sorted(by_ctrl.items(), key=lambda x: x[0]):
        module = ctrl.replace("Controller", "") if ctrl.endswith("Controller") else ctrl
        for ep in eps:
            method = str(ep.get("http_method") or "").upper()
            route = str(ep.get("route") or "")
            action = str(ep.get("method_name") or ep.get("action") or "")
            lines.append(
                f"| FR-{fr_idx:03d} | {module} | {action} | Must | "
                f"`{method} {route}` |"
            )
            fr_idx += 1
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 各语言 HTTP 端点搜索 (私有)
# ---------------------------------------------------------------------------


def _build_csharp_route(class_route: str, action_route: str, class_name: str) -> str:
    """构建 C# 完整路由 (类级 [Route] + 方法级 [HttpGet("path")] 拼接).

    设计理由: ASP.NET Core 路由拼接规则:
    - [Route("api/[controller]")] + [HttpGet("{id}")] => /api/User/{id}
    - [HttpGet("/absolute")] => /absolute (以 / 开头时为绝对路径, 不拼接)
    - [Route("api/[controller]")] 无方法路由 => /api/User

    Args:
        class_route: 类级 [Route] 路由模板 (如 "api/[controller]")
        action_route: 方法级 [HttpGet] 路由模板 (如 "{id}")
        class_name: 类名 (用于替换 [controller] 占位符)

    Returns:
        完整路由路径 (如 "/api/User/{id}"), 无路由时返回空字符串
    """
    # 替换 [controller] 占位符: 取类名去掉 Controller 后缀并小写
    # (ASP.NET Core 默认路由约定多为小写控制器段)
    base = class_route
    if "[controller]" in base.lower() and class_name:
        controller_name = class_name
        if controller_name.endswith("Controller"):
            controller_name = controller_name[: -len("Controller")]
        # 大小写不敏感替换, 输出统一小写
        base = re.sub(
            r"\[controller\]",
            controller_name.lower(),
            base,
            flags=re.IGNORECASE,
        )

    # 以 / 开头的 action_route 为绝对路径, 直接返回
    if action_route.startswith("/"):
        return action_route

    if base and action_route:
        return f"/{base.strip('/')}/{action_route.strip('/')}"
    if base:
        return f"/{base.strip('/')}"
    if action_route:
        return f"/{action_route.strip('/')}"
    return ""


def _search_csharp_endpoints(content: str, rel_path: str, lang: str) -> list[dict]:
    """搜索 C# Controller 端点 (ASP.NET Core [Http*] 注解 + 方法签名).

    设计理由 (借鉴 AutoCodeRover AST 搜索):
    - 匹配 [HttpGet]/[HttpPost]/[HttpPut]/[HttpDelete]/[HttpPatch] 注解
    - 拼接类级 [Route("api/[controller]")] + 方法级路由
    - 仅识别 public 方法 (跳过 private/protected, Controller Action 必须为 public)
    - 正则匹配而非 AST: C# 注解在 AST 中结构复杂, 正则更直观且兼容性好

    Args:
        content: 文件文本内容
        rel_path: 相对路径 (用于输出)
        lang: 语言标识 (来自 _EXT_TO_LANG)

    Returns:
        端点列表
    """
    endpoints: list[dict] = []
    lines = content.split("\n")
    current_class = ""
    class_route = ""
    # pending_route: [Route] 出现在 class 定义前一行时的暂存 (ASP.NET Core 常见写法)
    pending_route = ""

    for i, line in enumerate(lines, 1):
        # [Route("api/[controller]")] 类级路由
        # v12-P0-1: 方法级 [Route("update")] 绝不可覆盖 class_route,
        # 否则后续端点会拼成 /update/login、/login/logout 等错误路径.
        # 类级 Route 仅出现在 class 定义之前 (pending) 或与 class 同一行.
        route_match = re.search(r'\[Route\(\s*"([^"]+)"\s*\)\]', line)
        if route_match:
            route_val = route_match.group(1)
            # 同行同时有 class → 类级路由
            if re.search(r"\bclass\s+\w+", line):
                pending_route = route_val
            elif not current_class:
                # class 尚未出现: 暂存为类级路由
                pending_route = route_val
            # else: 已进入类体后的 [Route] 一律视为方法级, 由下方 Http* 扫描消费

        # 类定义 (跟踪当前类名)
        cls_match = re.search(r"\bclass\s+(\w+)", line)
        if cls_match:
            current_class = cls_match.group(1)
            # 应用暂存的 [Route] (class 定义前一行的情况), 否则重置
            class_route = pending_route
            pending_route = ""

        # HTTP 谓词注解: [HttpGet] / [HttpGet("path")] / [HttpPost("path", Name = "...")]
        # v12: 亦识别 [HttpGet(Name = "sms")] — Name 在部分文档约定中映射为子路径
        http_match = re.search(
            r'\[(Http(?:Get|Post|Put|Delete|Patch))(?:\(\s*"([^"]*)"\s*(?:,[^]]*)?\))?\]',
            line,
            re.IGNORECASE,
        )
        name_route_match = None
        if not http_match:
            name_route_match = re.search(
                r'\[(Http(?:Get|Post|Put|Delete|Patch))\(\s*Name\s*=\s*"([^"]+)"\s*\)\]',
                line,
                re.IGNORECASE,
            )
        if http_match or name_route_match:
            if http_match:
                http_method = http_match.group(1).replace("Http", "").upper()
                action_route = http_match.group(2) or ""
            else:
                http_method = name_route_match.group(1).replace("Http", "").upper()
                action_route = name_route_match.group(2) or ""

            # v11-P0-2: 当 [HttpPost] 无参数时, 向下扫描注解行,
            # 提取独立的 [Route("path")] (ASP.NET Core 模式 A: [HttpPost] 换行 [Route("update")]).
            # 遇到 public 方法签名则停止扫描.
            if not action_route:
                # lines 是 0-based, i 来自 enumerate(lines, 1) 是 1-based, 故 lines[i] 是下一行
                for k in range(i, min(i + 5, len(lines))):
                    # 检测独立的 [Route("path")] 特性
                    route_attr_match = re.search(
                        r'\[Route\(\s*"([^"]+)"\s*\)\]', lines[k]
                    )
                    if route_attr_match:
                        action_route = route_attr_match.group(1)
                        break
                    # 遇到 public 方法签名则停止扫描 (避免误用下一个方法的 [Route])
                    if re.search(r'\bpublic\s+', lines[k]):
                        break

            # 向下找 public 方法签名 (跳过注解行, 最多看 10 行)
            for j in range(i, min(i + 10, len(lines))):
                # 仅匹配 public 方法 (Controller Action 必须 public, 跳过 private/protected)
                method_match = re.search(
                    r"\bpublic\s+(?:async\s+)?(?:\w+(?:<[^>]+>)?|void)\s+(\w+)\s*\(",
                    lines[j],
                )
                if method_match:
                    method_name = method_match.group(1)
                    # 跳过构造函数 (方法名与类名相同)
                    if method_name == current_class:
                        continue
                    full_route = _build_csharp_route(class_route, action_route, current_class)
                    endpoints.append(
                        {
                            "file_path": rel_path,
                            "lang": lang,
                            "class_name": current_class,
                            "method_name": method_name,
                            "http_method": http_method,
                            "route": full_route,
                            "line": i,
                            "summary": lines[j].strip(),
                        }
                    )
                    break
    return endpoints


def _search_python_endpoints(content: str, rel_path: str, lang: str) -> list[dict]:
    """搜索 Python HTTP 端点 (FastAPI 装饰器 + Django URL 路由).

    设计理由:
    - FastAPI: @app.get("/path") / @router.post("/path") / @app.api_route("/path", methods=["GET"])
    - Django: path("...", views.xxx) / re_path("...", views.xxx)
    - 识别 async def / def, 提取函数签名
    - 正则匹配: Python 装饰器在 AST 中为 decorated_definition, 但装饰器参数提取正则更直接

    Args:
        content: 文件文本内容
        rel_path: 相对路径 (用于输出)
        lang: 语言标识

    Returns:
        端点列表
    """
    endpoints: list[dict] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # FastAPI: @app.get("/path") / @router.post("/path") / @app.api_route("/path", methods=["GET"])
        fastapi_match = re.search(
            r'@\w+\.(get|post|put|delete|patch|api_route)\(\s*["\']([^"\']+)["\']',
            line,
            re.IGNORECASE,
        )
        if fastapi_match:
            verb = fastapi_match.group(1).lower()
            if verb == "api_route":
                # @app.api_route("/path", methods=["GET"]) -> 需提取 methods 参数
                methods_match = re.search(r'methods\s*=\s*\[["\'](\w+)["\']', line)
                http_method = methods_match.group(1).upper() if methods_match else "GET"
            else:
                http_method = verb.upper()
            route = fastapi_match.group(2)

            # 向下找 def / async def (跳过装饰器行, 最多看 5 行)
            for j in range(i, min(i + 5, len(lines))):
                def_match = re.search(
                    r"\b(?:async\s+)?def\s+(\w+)\s*\(", lines[j]
                )
                if def_match:
                    endpoints.append(
                        {
                            "file_path": rel_path,
                            "lang": lang,
                            "class_name": "",
                            "method_name": def_match.group(1),
                            "http_method": http_method,
                            "route": route,
                            "line": i,
                            "summary": lines[j].strip(),
                        }
                    )
                    break

        # Django: path("...", views.xxx) / re_path("...", views.xxx)
        django_match = re.search(
            r'(?:re_)?path\(\s*["\']([^"\']+)["\'].*?views\.(\w+)', line
        )
        if django_match:
            endpoints.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "class_name": "",
                    "method_name": django_match.group(2),
                    "http_method": "GET",  # Django 默认 GET, 具体谓词在 view 内定义
                    "route": django_match.group(1),
                    "line": i,
                    "summary": line.strip(),
                }
            )
    return endpoints


def _search_java_endpoints(content: str, rel_path: str, lang: str) -> list[dict]:
    """搜索 Java Spring HTTP 端点 (@GetMapping / @PostMapping / @RequestMapping).

    设计理由:
    - @GetMapping("/path") / @PostMapping / @PutMapping / @DeleteMapping / @PatchMapping
    - @RequestMapping(value = "/path", method = RequestMethod.GET) (类级或方法级)
    - 仅识别 public 方法 (Spring Controller 方法必须 public)
    - 正则匹配: Java 注解在 AST 中为 annotation node, 但参数提取正则更简单

    Args:
        content: 文件文本内容
        rel_path: 相对路径 (用于输出)
        lang: 语言标识

    Returns:
        端点列表
    """
    endpoints: list[dict] = []
    lines = content.split("\n")
    current_class = ""
    class_request_mapping = ""
    # pending_mapping: @RequestMapping 出现在 class 定义前一行时的暂存 (Spring 常见写法)
    pending_mapping = ""
    # 检测文件是否含 @RestController / @Controller (Spring Controller 标志)
    is_spring_controller = "@RestController" in content or "@Controller" in content

    for i, line in enumerate(lines, 1):
        # 类级 @RequestMapping("/api") (可能在 class 定义前一行或同一行)
        class_mapping_match = re.search(
            r'@RequestMapping\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', line
        )
        if class_mapping_match and is_spring_controller:
            if current_class:
                # @RequestMapping 在 class 定义之后
                class_request_mapping = class_mapping_match.group(1)
            else:
                # @RequestMapping 在 class 定义之前, 暂存等待 class 匹配
                pending_mapping = class_mapping_match.group(1)

        # 类定义 (跟踪当前类名)
        cls_match = re.search(r"\bclass\s+(\w+)", line)
        if cls_match:
            current_class = cls_match.group(1)
            # 应用暂存的 @RequestMapping, 否则重置
            class_request_mapping = pending_mapping
            pending_mapping = ""

        # 方法级 @GetMapping / @PostMapping / @PutMapping / @DeleteMapping / @PatchMapping
        http_match = re.search(
            r'@(?:Get|Post|Put|Delete|Patch)Mapping(?:\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']\s*(?:,[^]]*)?\))?',
            line,
        )
        # 方法级 @RequestMapping(value = "/path", method = ...)
        # 排除类级 @RequestMapping (已被 class_mapping_match 捕获, 避免重复匹配)
        req_mapping_match = None
        if not class_mapping_match:
            req_mapping_match = re.search(
                r'@RequestMapping\(\s*(?:value\s*=\s*)?["\']([^"\']*)["\']',
                line,
            )

        if http_match or req_mapping_match:
            http_method = ""
            action_route = ""

            if http_match:
                # 从注解名提取 HTTP 谓词: @GetMapping -> GET
                http_method = (
                    http_match.group(0)
                    .split("Mapping")[0]
                    .replace("@", "")
                    .upper()
                )
                action_route = http_match.group(1) or ""
            elif req_mapping_match:
                # @RequestMapping 需从 method 参数提取谓词, 默认 GET
                method_param = re.search(
                    r"method\s*=\s*RequestMethod\.(\w+)", line
                )
                http_method = (
                    method_param.group(1).upper() if method_param else "GET"
                )
                action_route = req_mapping_match.group(1) or ""

            # 向下找 public 方法签名 (跳过注解行, 最多看 10 行)
            for j in range(i, min(i + 10, len(lines))):
                method_match = re.search(
                    r"\bpublic\s+(?:[\w<>\[\],\s]+?)\s+(\w+)\s*\(", lines[j]
                )
                if method_match:
                    method_name = method_match.group(1)
                    # 拼接类级 + 方法级路由
                    if class_request_mapping and action_route:
                        full_route = f"/{class_request_mapping.strip('/')}/{action_route.strip('/')}"
                    elif class_request_mapping:
                        full_route = f"/{class_request_mapping.strip('/')}"
                    else:
                        full_route = f"/{action_route.strip('/')}" if action_route else ""
                    endpoints.append(
                        {
                            "file_path": rel_path,
                            "lang": lang,
                            "class_name": current_class,
                            "method_name": method_name,
                            "http_method": http_method,
                            "route": full_route,
                            "line": i,
                            "summary": lines[j].strip(),
                        }
                    )
                    break
    return endpoints


def _search_typescript_endpoints(
    content: str, rel_path: str, lang: str
) -> list[dict]:
    """搜索 TypeScript/JavaScript HTTP 端点 (Express/Koa/NestJS).

    设计理由:
    - Express/Koa/Fastify: app.get("/path", handler) / router.post("/path", handler)
      (TypeScript 和 JavaScript 模式一致, 共用此函数)
    - NestJS: @Controller("prefix") + @Get("path") / @Post("path")
      (仅 TypeScript, 装饰器风格)
    - 路由路径要求以 / 开头, 减少误匹配 (如 obj.get("key") 不匹配)

    Args:
        content: 文件文本内容
        rel_path: 相对路径 (用于输出)
        lang: 语言标识 (typescript 或 javascript)

    Returns:
        端点列表
    """
    endpoints: list[dict] = []
    lines = content.split("\n")
    current_class = ""
    controller_route = ""
    # pending_controller: @Controller 出现在 class 定义前一行时的暂存 (NestJS 常见写法)
    pending_controller = ""

    for i, line in enumerate(lines, 1):
        # @Controller("prefix") 类级路由 (可能在 class 定义前一行或同一行)
        controller_match = re.search(
            r'@Controller\(\s*["\']([^"\']*)["\']\s*\)', line
        )
        if controller_match:
            if current_class:
                controller_route = controller_match.group(1)
            else:
                # @Controller 在 class 定义之前, 暂存等待 class 匹配
                pending_controller = controller_match.group(1)

        # NestJS 类定义
        cls_match = re.search(r"\bclass\s+(\w+)", line)
        if cls_match:
            current_class = cls_match.group(1)
            # 应用暂存的 @Controller 路由, 否则重置
            controller_route = pending_controller
            pending_controller = ""

        # NestJS 方法级: @Get("path") / @Post("path") / @Put / @Delete / @Patch
        nest_match = re.search(
            r'@(Get|Post|Put|Delete|Patch)\(\s*["\']?([^"\')]*)["\']?\s*\)',
            line,
        )
        if nest_match:
            http_method = nest_match.group(1).upper()
            action_route = nest_match.group(2) or ""

            # 向下找方法签名 (最多看 10 行)
            for j in range(i, min(i + 10, len(lines))):
                # async methodName(...) / methodName(...)
                method_match = re.search(
                    r"(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*\S+)?\s*\{",
                    lines[j],
                )
                if method_match:
                    method_name = method_match.group(1)
                    # 拼接 Controller 路由 + 方法路由
                    if controller_route and action_route:
                        full_route = f"/{controller_route.strip('/')}/{action_route.strip('/')}"
                    elif controller_route:
                        full_route = f"/{controller_route.strip('/')}"
                    else:
                        full_route = f"/{action_route.strip('/')}" if action_route else ""
                    endpoints.append(
                        {
                            "file_path": rel_path,
                            "lang": lang,
                            "class_name": current_class,
                            "method_name": method_name,
                            "http_method": http_method,
                            "route": full_route,
                            "line": i,
                            "summary": lines[j].strip(),
                        }
                    )
                    break

        # Express/Koa/Fastify: app.get("/path", ...) / router.post("/path", ...)
        # 路径要求以 / 开头, 减少误匹配
        express_match = re.search(
            r'\b\w+\.(get|post|put|delete|patch)\s*\(\s*["\'`](/[^"\'`]*)["\'`]',
            line,
        )
        if express_match:
            http_method = express_match.group(1).upper()
            route = express_match.group(2)
            # 提取 handler 函数名 (第二个参数, 若为标识符)
            handler_match = re.search(
                r',\s*(\w+)\s*[,)]', line
            )
            method_name = handler_match.group(1) if handler_match else ""
            endpoints.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "class_name": "",
                    "method_name": method_name,
                    "http_method": http_method,
                    "route": route,
                    "line": i,
                    "summary": line.strip(),
                }
            )
    return endpoints


def _search_go_endpoints(content: str, rel_path: str, lang: str) -> list[dict]:
    """搜索 Go HTTP 端点 (gin / echo / chi / net/http).

    设计理由:
    - gin/echo: r.GET("/path", handler) / r.POST("/path", handler) (大写谓词)
    - chi: r.Get("/path", handler) / r.Post("/path", handler) (首字母大写谓词)
    - net/http: http.HandleFunc("/path", handler) / mux.HandleFunc("/path", handler)
    - 提取 handler 函数名 (第二个参数, 若为标识符而非匿名函数)

    Args:
        content: 文件文本内容
        rel_path: 相对路径 (用于输出)
        lang: 语言标识

    Returns:
        端点列表
    """
    endpoints: list[dict] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # gin/echo: r.GET("/path", handler) / r.POST("/path", handler)
        gin_match = re.search(
            r'\b\w+\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*["\']([^"\']+)["\']',
            line,
        )
        if gin_match:
            http_method = gin_match.group(1).upper()
            route = gin_match.group(2)
            # 提取 handler 函数名
            handler_match = re.search(r',\s*(\w+)\s*[,)]', line)
            method_name = handler_match.group(1) if handler_match else ""
            endpoints.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "class_name": "",
                    "method_name": method_name,
                    "http_method": http_method,
                    "route": route,
                    "line": i,
                    "summary": line.strip(),
                }
            )
            continue

        # chi: r.Get("/path", handler) / r.Post("/path", handler)
        chi_match = re.search(
            r'\b\w+\.(Get|Post|Put|Delete|Patch)\s*\(\s*["\']([^"\']+)["\']',
            line,
        )
        if chi_match:
            http_method = chi_match.group(1).upper()
            route = chi_match.group(2)
            handler_match = re.search(r',\s*(\w+)\s*[,)]', line)
            method_name = handler_match.group(1) if handler_match else ""
            endpoints.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "class_name": "",
                    "method_name": method_name,
                    "http_method": http_method,
                    "route": route,
                    "line": i,
                    "summary": line.strip(),
                }
            )
            continue

        # net/http: http.HandleFunc("/path", handler) / mux.HandleFunc("/path", handler)
        http_match = re.search(
            r'\b\w+\.HandleFunc\s*\(\s*["\']([^"\']+)["\']',
            line,
        )
        if http_match:
            route = http_match.group(1)
            handler_match = re.search(r',\s*(\w+)\s*[,)]', line)
            method_name = handler_match.group(1) if handler_match else ""
            # net/http 不区分谓词, 默认 GET (具体谓词在 handler 内通过 r.Method 判断)
            endpoints.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "class_name": "",
                    "method_name": method_name,
                    "http_method": "GET",
                    "route": route,
                    "line": i,
                    "summary": line.strip(),
                }
            )
    return endpoints


# ---------------------------------------------------------------------------
# 公共 API: 枚举定义搜索
# ---------------------------------------------------------------------------


def search_enum_definitions(
    repo_path: str, file_index: dict | None = None
) -> list[dict]:
    """v8-P0-C: 搜索所有枚举定义 (errorCode 常量).

    通用扫描所有代码文件, 提取枚举定义及其常量,
    解决"errorCode 幻觉"问题 (确保文档引用真实存在的错误码常量和数值).

    支持语言:
    - C#: public enum Xxx { A = 1, B = 2 }
    - Python: class Xxx(Enum): A = 1 / class Xxx(IntEnum): A = 1
    - Java: public enum Xxx { A, B } / public enum Xxx { A(1), B(2) }

    设计理由 (借鉴 AutoCodeRover AST 搜索 API):
    - Python 优先用 tree-sitter AST 精确定位 class_definition + Enum 基类
    - C#/Java 用正则匹配 (enum 语法结构简单, 正则足够可靠)
    - AST 不可用时降级为正则 (失败降级, 不阻断主流程)

    Args:
        repo_path: 仓库本地路径
        file_index: 文件索引 (可选)

    Returns:
        枚举列表, 每项格式:
        {
            "file_path": "相对路径",
            "lang": "csharp|python|java",
            "enum_name": "枚举名",
            "constants": [{"name": "常量名", "value": "值"}],
            "line": 10
        }
    """
    enums: list[dict] = []

    for abs_path, rel_path, ext, lang in _iter_code_files(repo_path, file_index):
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            logger.debug("v8-P0-C: 读取文件失败 (跳过) %s: %s", rel_path, e)
            continue

        try:
            if ext == ".cs":
                enums.extend(_search_csharp_enums(content, rel_path, lang))
            elif ext == ".py":
                enums.extend(_search_python_enums(content, rel_path, lang))
            elif ext == ".java":
                enums.extend(_search_java_enums(content, rel_path, lang))
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P0-C: 解析枚举失败 (跳过, 不阻断) %s: %s", rel_path, e)

    logger.info("v8-P0-C: 搜索到 %d 个枚举定义 (repo=%s)", len(enums), repo_path)
    return enums


# ---------------------------------------------------------------------------
# 各语言枚举定义搜索 (私有)
# ---------------------------------------------------------------------------


def _search_csharp_enums(content: str, rel_path: str, lang: str) -> list[dict]:
    """搜索 C# enum 定义: public enum Xxx { A = 1, B = 2 }.

    设计理由:
    - C# enum 语法: [access_modifier] enum Name [: base_type] { A = 1, B = 2, ... }
    - 正则匹配 enum ... { ... } 块, 解析常量名 = 值
    - 跳过注解行 ([Description("...")]) 和注释行
    """
    enums: list[dict] = []
    # 匹配 enum Name { ... } (含可选基类型: enum Name : int { ... })
    pattern = re.compile(
        r"enum\s+(\w+)\s*(?::\s*\w+\s*)?\{([^}]+)\}",
        re.MULTILINE | re.DOTALL,
    )
    for m in pattern.finditer(content):
        enum_name = m.group(1)
        body = m.group(2)
        constants: list[dict] = []
        for line in body.split("\n"):
            line = line.strip().rstrip(",").strip()
            if not line or line.startswith("//") or line.startswith("["):
                continue
            # 移除行内注解: [Description("xxx")]
            line = re.sub(r"\[[^\]]+\]", "", line).strip()
            # 匹配: Name = value 或 Name (无值)
            const_match = re.match(r"(\w+)\s*(?:=\s*([^,/\s]+))?", line)
            if const_match:
                name = const_match.group(1)
                value = const_match.group(2) or ""
                constants.append({"name": name, "value": value})
        if constants:
            line_num = _line_of(content, m.start())
            enums.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "enum_name": enum_name,
                    "constants": constants,
                    "line": line_num,
                }
            )
    return enums


def _search_python_enums(content: str, rel_path: str, lang: str) -> list[dict]:
    """搜索 Python enum 定义: class Xxx(Enum): A = 1.

    设计理由 (借鉴 AutoCodeRover AST 搜索 API):
    - 优先用 tree-sitter AST 精确定位 class_definition 节点, 检查基类是否为 Enum/IntEnum
    - AST 不可用时降级为正则 (失败降级, 不阻断主流程)
    - AST 优势: 精确识别 class 定义, 不受注释/字符串中的伪 class 干扰
    """
    # 优先: tree-sitter AST 解析 (精确)
    parser = _get_parser_cached("python")
    if parser is not None:
        ast_enums = _search_python_enums_via_ast(content, rel_path, lang, parser)
        if ast_enums:
            return ast_enums
        logger.debug("v8-P0-C: Python enum AST 无结果, 降级正则 (rel_path=%s)", rel_path)

    # 降级: 正则匹配
    return _search_python_enums_via_regex(content, rel_path, lang)


def _search_python_enums_via_ast(
    content: str, rel_path: str, lang: str, parser: Any
) -> list[dict]:
    """通过 tree-sitter AST 搜索 Python enum 定义 (精确模式).

    设计理由:
    - 遍历 AST 找到 class_definition 节点
    - 检查 superclasses 是否含 Enum / IntEnum
    - 遍历 class body 中的 assignment 节点提取常量
    - 相比正则, AST 不会误匹配注释/字符串中的 "class Xxx(Enum):"
    """
    enums: list[dict] = []
    try:
        source_bytes = content.encode("utf-8", errors="replace")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        def _walk(node: Any) -> None:
            """递归遍历 AST, 查找 enum class 定义."""
            if node.type == "class_definition":
                # 提取类名
                name_node = node.child_by_field_name("name")
                if name_node is not None:
                    class_name = source_bytes[
                        name_node.start_byte : name_node.end_byte
                    ].decode("utf-8", errors="replace")
                    # 提取基类文本, 检查是否为 Enum / IntEnum
                    superclasses_node = node.child_by_field_name("superclasses")
                    base_text = ""
                    if superclasses_node is not None:
                        base_text = source_bytes[
                            superclasses_node.start_byte : superclasses_node.end_byte
                        ].decode("utf-8", errors="replace")
                    if re.search(r"\b(?:Int)?Enum\b", base_text):
                        # 遍历 class body 提取常量
                        constants = _extract_python_enum_constants(
                            node, source_bytes
                        )
                        if constants:
                            line_num = node.start_point[0] + 1
                            enums.append(
                                {
                                    "file_path": rel_path,
                                    "lang": lang,
                                    "enum_name": class_name,
                                    "constants": constants,
                                    "line": line_num,
                                }
                            )
            # 递归子节点
            for child in node.children:
                _walk(child)

        _walk(root)
    except Exception as e:  # noqa: BLE001
        logger.debug("v8-P0-C: Python enum AST 解析失败 (降级正则): %s", e)
    return enums


def _extract_python_enum_constants(
    class_node: Any, source_bytes: bytes
) -> list[dict]:
    """从 Python class_definition AST 节点提取 enum 常量.

    设计理由: 遍历 class body 中的 assignment 节点 (NAME = value),
    提取常量名和值. 跳过方法定义 / 文档字符串等非赋值节点.
    """
    constants: list[dict] = []
    body_node = class_node.child_by_field_name("body")
    if body_node is None:
        return constants

    for child in body_node.children:
        # assignment: NAME = value
        if child.type == "assignment":
            left = child.child_by_field_name("left")
            right = child.child_by_field_name("right")
            if left is not None and left.type == "identifier":
                name = source_bytes[left.start_byte : left.end_byte].decode(
                    "utf-8", errors="replace"
                )
                value = ""
                if right is not None:
                    value = source_bytes[
                        right.start_byte : right.end_byte
                    ].decode("utf-8", errors="replace")
                # 跳过 dunder 属性 (__members__ 等) 和私有属性
                if not name.startswith("_"):
                    constants.append({"name": name, "value": value})
        # decorated_definition: 装饰的赋值 (穿透到内部)
        elif child.type == "decorated_definition":
            for inner in child.children:
                if inner.type == "assignment":
                    left = inner.child_by_field_name("left")
                    right = inner.child_by_field_name("right")
                    if left is not None and left.type == "identifier":
                        name = source_bytes[
                            left.start_byte : left.end_byte
                        ].decode("utf-8", errors="replace")
                        value = ""
                        if right is not None:
                            value = source_bytes[
                                right.start_byte : right.end_byte
                            ].decode("utf-8", errors="replace")
                        if not name.startswith("_"):
                            constants.append({"name": name, "value": value})
    return constants


def _search_python_enums_via_regex(
    content: str, rel_path: str, lang: str
) -> list[dict]:
    """通过正则搜索 Python enum 定义 (降级模式).

    设计理由: tree-sitter 不可用时降级. 匹配 class Xxx(Enum): / class Xxx(IntEnum):
    后续行缩进块为常量定义.
    """
    enums: list[dict] = []
    pattern = re.compile(
        r"class\s+(\w+)\s*\(\s*(?:Int)?Enum\s*\):\s*\n((?:[ \t]+[^\n]+\n)+)",
        re.MULTILINE,
    )
    for m in pattern.finditer(content):
        enum_name = m.group(1)
        body = m.group(2)
        constants: list[dict] = []
        for line in body.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith('"""'):
                continue
            const_match = re.match(r"(\w+)\s*=\s*([^#\s]+)", line)
            if const_match:
                name = const_match.group(1)
                if name.startswith("_"):
                    continue
                value = const_match.group(2)
                constants.append({"name": name, "value": value})
        if constants:
            line_num = _line_of(content, m.start())
            enums.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "enum_name": enum_name,
                    "constants": constants,
                    "line": line_num,
                }
            )
    return enums


def _search_java_enums(content: str, rel_path: str, lang: str) -> list[dict]:
    """搜索 Java enum 定义: public enum Xxx { A, B } / public enum Xxx { A(1), B(2) }.

    设计理由:
    - Java enum 语法: [access_modifier] enum Name { A, B(1), C(2); ... }
    - 常量段以 ; 结尾 (之后是构造函数/方法), 仅解析 ; 之前部分
    - 正则匹配 enum ... { ... } 块
    """
    enums: list[dict] = []
    pattern = re.compile(
        r"enum\s+(\w+)\s*\{([^}]+)\}",
        re.MULTILINE | re.DOTALL,
    )
    for m in pattern.finditer(content):
        enum_name = m.group(1)
        body = m.group(2)
        # Java enum 常量段以 ; 结尾, 之后是构造函数/字段/方法
        # 仅解析 ; 之前部分 (常量列表)
        if ";" in body:
            body = body.split(";", 1)[0]
        constants: list[dict] = []
        for line in body.split("\n"):
            line = line.strip().rstrip(",").strip()
            if not line or line.startswith("//"):
                continue
            # 匹配: NAME(value) 或 NAME
            const_match = re.match(r"(\w+)\s*(?:\(([^)]*)\))?", line)
            if const_match:
                name = const_match.group(1)
                value = const_match.group(2) or ""
                constants.append({"name": name, "value": value})
        if constants:
            line_num = _line_of(content, m.start())
            enums.append(
                {
                    "file_path": rel_path,
                    "lang": lang,
                    "enum_name": enum_name,
                    "constants": constants,
                    "line": line_num,
                }
            )
    return enums


# ---------------------------------------------------------------------------
# 格式化函数 (供 prompt 注入)
# ---------------------------------------------------------------------------


def format_endpoints_for_prompt(endpoints: list[dict]) -> str:
    """格式化 HTTP 端点列表为 prompt 注入文本, 按模块 (文件) 分组.

    设计理由:
    - 按文件分组展示, 便于 LLM 按模块理解端点分布
    - 强调"必须覆盖每一个端点", 防止接口遗漏
    - 不包含任何项目特定名称, 通用适用

    Args:
        endpoints: search_http_endpoints 返回的端点列表

    Returns:
        格式化文本, 可直接注入 LLM prompt;
        无端点时返回降级提示文本
    """
    if not endpoints:
        return "(未扫描到 HTTP 端点)"

    # 按文件分组 (模块化展示)
    by_file: dict[str, list[dict]] = {}
    for ep in endpoints:
        file_path = ep.get("file_path", "")
        by_file.setdefault(file_path, []).append(ep)

    lines: list[str] = [
        "# HTTP 端点清单 (AST 结构感知扫描, 文档必须覆盖每一个端点)",
        f"# 共 {len(endpoints)} 个端点, 分布在 {len(by_file)} 个文件中",
        "",
    ]

    for file_path, eps in by_file.items():
        lines.append(f"## {file_path}")
        for ep in eps:
            class_name = ep.get("class_name", "")
            method_name = ep.get("method_name", "")
            http_method = ep.get("http_method", "")
            route = ep.get("route", "")
            line_num = ep.get("line", 0)
            # 类名.方法名 (无类名时仅方法名)
            qualified = f"{class_name}.{method_name}" if class_name else method_name
            lines.append(
                f"- {http_method} {route} -> {qualified} [line:{line_num}]"
            )
        lines.append("")  # 文件间空行分隔

    return "\n".join(lines).rstrip()


def format_enums_for_prompt(enums: list[dict]) -> str:
    """格式化枚举定义为 prompt 注入文本, 展示枚举名 + 常量名=值.

    设计理由:
    - 强调"错误码必须引用以下真实值", 防止 errorCode 幻觉
    - 展示常量名和数值, 便于 LLM 精确引用
    - 不包含任何项目特定名称, 通用适用

    Args:
        enums: search_enum_definitions 返回的枚举列表

    Returns:
        格式化文本, 可直接注入 LLM prompt;
        无枚举时返回降级提示文本
    """
    if not enums:
        return "(未扫描到枚举定义)"

    lines: list[str] = [
        "# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)",
        f"# 共 {len(enums)} 个枚举定义",
        "",
    ]

    for enum in enums:
        enum_name = enum.get("enum_name", "")
        file_path = enum.get("file_path", "")
        line_num = enum.get("line", 0)
        lines.append(f"## {enum_name} [{file_path}:{line_num}]")
        for const in enum.get("constants", []):
            name = const.get("name", "")
            value = const.get("value", "")
            if value:
                lines.append(f"- {name} = {value}")
            else:
                lines.append(f"- {name}")
        lines.append("")  # 枚举间空行分隔

    return "\n".join(lines).rstrip()


def search_domain_symbols(repo_path: str, max_files: int = 800) -> dict[str, list[str]]:
    """v14: 通用扫描领域符号 (类名 / 表名 / Handler), 供终审事实附录注入.

    不硬编码任何产品名; 仅用通用语言结构模式:
    - C#/Java: class Xxx
    - C#: [Table("name")] / [Table(Name = "name")]
    - 路径字面量中的 /api/... 片段另见 search_literal_api_routes
    """
    root = Path(repo_path)
    class_names: set[str] = set()
    table_names: set[str] = set()
    if not root.is_dir():
        return {"class_names": [], "table_names": []}

    class_re = re.compile(
        r"\b(?:public|internal|protected|private)?\s*(?:static\s+|abstract\s+|sealed\s+|partial\s+)*"
        r"class\s+([A-Z][A-Za-z0-9_]{2,})"
    )
    # EF Core / SqlSugar / 通用 Table 标注
    table_re = re.compile(
        r'\[(?:Table|SugarTable)\s*\(\s*(?:Name\s*=\s*)?["\']([A-Za-z0-9_]+)["\']',
        re.IGNORECASE,
    )
    table_re2 = re.compile(
        r'\.ToTable\s*\(\s*["\']([A-Za-z0-9_]+)["\']',
        re.IGNORECASE,
    )
    # 属性 / 列名 (含 ColumnName)
    prop_re = re.compile(
        r"\b(?:public|internal|protected)\s+(?:static\s+|virtual\s+|override\s+|required\s+|const\s+)*"
        r"(?:string\??|int\??|long\??|bool\??|decimal\??|double\??|float\??|DateTime\??|Guid\??|"
        r"object|[A-Z][A-Za-z0-9_<>,\s\?]+?)\s+"
        r"([A-Z][A-Za-z0-9_]{2,})\s*[{;=]"
    )
    # public const int Foo = 1;
    const_re = re.compile(
        r"\b(?:public|internal)\s+const\s+\w+\s+([A-Z][A-Za-z0-9_]{2,})\s*="
    )
    col_re = re.compile(
        r'\[SugarColumn\s*\([^\]]*ColumnName\s*=\s*["\']([A-Za-z0-9_]+)["\']',
        re.IGNORECASE,
    )
    scanned = 0
    prop_names: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        # 跳过测试目录名
        if any(part.lower() in {"unittest", "tests", "test"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".cs", ".java", ".kt"}:
            continue
        scanned += 1
        if scanned > max_files:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for m in class_re.finditer(text):
            name = m.group(1)
            if name.endswith(("Tests", "Test", "Specs")):
                continue
            class_names.add(name)
        for m in table_re.finditer(text):
            table_names.add(m.group(1))
        for m in table_re2.finditer(text):
            table_names.add(m.group(1))
        for m in col_re.finditer(text):
            table_names.add(m.group(1))  # 列名也作为事实 token
        for m in prop_re.finditer(text):
            pname = m.group(1)
            if not pname.endswith(("Tests", "Test")):
                prop_names.add(pname)
        for m in const_re.finditer(text):
            prop_names.add(m.group(1))

    return {
        "class_names": sorted(class_names, key=lambda x: (-len(x), x))[:300],
        "table_names": sorted(table_names, key=lambda x: (-len(x), x))[:300],
        "property_names": sorted(prop_names, key=lambda x: (-len(x), x))[:300],
    }


def search_literal_api_routes(repo_path: str, max_files: int = 300) -> list[str]:
    """v14: 从源码字符串字面量提取 /api/... 路由 (含反向代理配置)."""
    root = Path(repo_path)
    routes: set[str] = set()
    if not root.is_dir():
        return []
    route_re = re.compile(r'["\`](/api/[a-zA-Z0-9_/\-{}]+)["\`]')
    scanned = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {
            ".cs", ".java", ".ts", ".js", ".json", ".yml", ".yaml", ".xml", ".py",
        }:
            continue
        scanned += 1
        if scanned > max_files:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for m in route_re.finditer(text):
            r = m.group(1).rstrip("/")
            if r.lower() != "/api/xxx":
                routes.add(r)
    return sorted(routes)


__all__ = [
    "search_http_endpoints",
    "search_enum_definitions",
    "search_domain_symbols",
    "search_literal_api_routes",
    "format_endpoints_for_prompt",
    "format_enums_for_prompt",
    "filter_api_doc_endpoints",
    "render_api_inventory_markdown",
    "render_feature_list_from_endpoints",
]
