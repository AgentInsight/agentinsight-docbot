"""AST 符号白名单校验器 (O4-P0-B).

借鉴 Aider Repo Map: 从 tree-sitter AST 抽取所有符号 (类/函数/方法),
作为 LLM 输出的白名单校验依据. 文档中提到的类名/函数名必须命中白名单.

设计约束:
- 从 code_learning 的 repo_map + code_graph 构建符号集合
- 仅校验标识符 (PascalCase / camelCase / snake_case), 不校验路径 (路径由 citation_extractor 校验)
- 排除常见英文单词, 避免误报
- 失败降级: 构建失败时 allow_unknown=True, 不阻断主流程

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# 标识符提取正则 (匹配 PascalCase / camelCase / snake_case)
# PascalCase: 至少两个大写开头的小写段 (如 UserController, ApiController)
# camelCase: 首字母小写, 后跟大写 (如 getUserInfo)
# snake_case: 全小写带下划线 (如 get_user_info)
# UPPER_SNAKE: 全大写带下划线 (如 MAX_RETRY_COUNT)
_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:(?:[A-Z][a-z0-9]+){2,}|[a-z]+_[a-z_]+|[A-Z][a-zA-Z0-9]*[A-Z][a-z0-9]*|[A-Z_]{3,})\b"
)

# 排除的常见英文单词 / 技术术语 (大写形式, 避免误报)
# v9: 移除硬编码的 AgentInsightService 等项目特定名称 (用户补充要求 #2: 不硬编码特定项目)
# 项目名/品牌名应从 project_metadata 动态提取, 在 build_from_code_learning 中加入排除集
_COMMON_WORDS: frozenset[str] = frozenset({
    "TODO", "FIXME", "NOTE", "HTTP", "HTTPS", "URL", "JSON", "XML",
    "SQL", "API", "SDK", "UI", "UX", "CSS", "HTML", "JS", "TS",
    "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS",
    "JWT", "RBAC", "RBAC", "CRUD", "ORM", "DTO", "DAO", "VO",
    "POCO", "EF", "DI", "IoC", "SOLID", "DRY", "KISS", "YAGNI",
    "The", "This", "That", "And", "But", "For", "With", "From",
    "ID", "OK", "KO", "PR", "MR", "CI", "CD", "QA", "PRD",
    "LLM", "RAG", "MCP", "AST", "SVG", "PNG", "JPG", "GIF",
    "UTC", "ISO", "UTF", "CRUD", "AC", "FR", "NFR",
})

# v5-P0-D: 文档编号模式 (如 AC1/FR-001/NFR-002/API-003/DEP-001 等), 不应校验为代码符号
_DOC_ID_PATTERN = re.compile(
    r"^(?:AC|FR|NFR|IR|DR|BR|C|AS|DEP|API|UC|TC|SC|REQ)[-_]?\d+$",
    re.IGNORECASE,
)

# v5-P0-D: 常见技术缩写 (含大小写敏感的加密算法等), 不应校验为代码符号
_COMMON_ABBREVS: frozenset[str] = frozenset({
    "API", "URL", "URI", "HTTP", "HTTPS", "JSON", "XML", "SQL", "HTML", "CSS",
    "JWT", "OAuth", "RBAC", "ABAC", "CRUD", "SDK", "SLA", "SLO", "TLS", "SSL",
    "HMAC", "SHA256", "MD5", "AES", "RSA", "PBKDF2", "BCrypt", "HS256",
    "YARP", "RFC", "ISO", "UTF", "UTC", "GUID", "UUID",
    "HTML", "CSS", "XML", "JSON", "YAML", "TOML",
    "MVC", "MVVM", "CQRS", "ESB", "SOA", "REST", "SOAP", "gRPC", "RESTful",
    "ACID", "BASE", "CAP", "BFF",
    # 常见技术栈词 (非项目符号, 避免误触发幻觉重写)
    "ASP", "NET", "PostgreSQL", "SqlSugar", "Redis", "SSE", "SaaS", "DevOps",
    "AGENTS", "ADMIN", "OWNER", "MEMBER",
})

# v7-P0-B: 常见外部库/框架类名 (不应校验为项目符号)
# 这些是业界主流框架/库的类名, 任何项目都可能引用, 不属于项目自身符号
_EXTERNAL_LIB_SYMBOLS: frozenset[str] = frozenset({
    # .NET 生态
    "MediatR", "IMemoryCache", "MemoryCache", "ISqlSugarClient", "SqlSugarClient",
    "SqlSugarScope", "ITenant", "IFreeSql", "FreeSql",
    "AppFriendlyException", "Oops", "Furion", "App", "IApplicationBuilder",
    "IConfiguration", "IWebHostEnvironment", "IServiceCollection", "ILogger",
    "ILoggerFactory", "IOptions", "IHostedService", "BackgroundService",
    "IController", "ControllerBase", "ApiController", "RouteAttribute",
    "HttpPostAttribute", "HttpGetAttribute", "HttpPutAttribute", "HttpDeleteAttribute",
    "FromBodyAttribute", "FromQueryAttribute", "FromRouteAttribute", "FromFormAttribute",
    "YARP", "TransformBuilder", "TransformContext", "RequestTransform",
    "BasicAuth", "AuthenticationHandler", "JwtBearerHandler", "AuthenticationScheme",
    "ClaimPrincipal", "ClaimsIdentity", "Claim",
    "EFCore", "DbContext", "DbSet", "Migration", "DatabaseFacade", "Dapper", "NHibernate",
    # Python 生态
    "FastAPI", "FastAPIRouter", "APIRouter", "Request", "Response",
    "HTTPException", "Depends", "Query", "Path", "Body", "Header",
    "Pydantic", "BaseModel", "Field", "validator", "root_validator",
    "LangGraph", "StateGraph", "END", "START", "MessageGraph",
    "LangChain", "LLMChain", "Chain", "Runnable", "RunnablePassthrough",
    "OpenAI", "AzureOpenAI", "ChatOpenAI", "OpenAIEmbeddings",
    "Qdrant", "QdrantClient", "ChromaDB", "FAISS", "Redis",
    "Celery", "BullMQ",
    # Java 生态
    "SpringBoot", "RestController", "RequestMapping", "SpringApplication",
    "JpaRepository", "EntityManager", "PersistenceContext",
    # 通用工具/协议
    "OpenAPI", "Swagger", "SwaggerUI", "Redoc",
    "JsonSerializer", "JsonDeserializer", "NewtonsoftJson", "SystemTextJson",
    "AutoMapper", "Mapster", "DTOMapper",
    "Polly", "RetryPolicy", "CircuitBreakerPolicy",
    "Serilog", "NLog", "Log4net",
    # 支付/认证相关 (业界通用协议/SDK, 非项目自身符号)
    "JSAPI", "NativePay", "MiniProgram", "AlipayClient", "AlipayTrade",
    "WeChatPayClient", "WeChatPayRequest", "WeChatPayResponse",
    "OAuth2", "OIDC", "OpenIDConnect",
})

# v7-P0-B: 后缀模式宽松校验 (XxxService/XxxHandler 等通用接口/类名)
# 即使不在白名单, 也不直接判为幻觉 (可能是真实存在但未被 AST 抽取的接口)
_LOOSE_SUFFIXES: tuple[str, ...] = (
    "Handler", "Service", "Controller", "Repository", "Manager",
    "Provider", "Factory", "Builder", "Context", "Client",
    "Orchestrator", "Evaluator", "Validator", "Resolver", "Strategy",
)

# 最小长度阈值 (避免 2 字符以下的短标识符误报)
_MIN_IDENTIFIER_LENGTH = 3


def _is_doc_id_or_abbrev(ident: str) -> bool:
    """v5-P0-D / v7-P0-B: 判断标识符是否为文档编号/缩写/外部库 (不应校验为代码符号).

    Args:
        ident: 待判断的标识符 (如 "AC1", "FR-001", "HMAC", "MediatR")

    Returns:
        True 表示是文档编号/缩写/外部库, 应跳过校验
    """
    if _DOC_ID_PATTERN.match(ident):
        return True
    if ident in _COMMON_ABBREVS or ident.upper() in _COMMON_ABBREVS:
        return True
    # v7-P0-B: 外部库类名白名单
    if ident in _EXTERNAL_LIB_SYMBOLS:
        return True
    return False


class SymbolValidator:
    """AST 符号白名单校验器.

    用法:
        validator = SymbolValidator()
        validator.build_from_code_learning(code_learning)
        result = validator.validate_document(doc_text)
        if not result["valid"]:
            # 触发重写, 将幻觉符号列入禁止清单
            ...
    """

    def __init__(self) -> None:
        self._symbol_set: set[str] = set()
        self._file_paths: set[str] = set()
        self._excluded_terms: set[str] = set()  # v9: 动态排除项 (品牌名/项目名)
        self._built: bool = False

    def build_from_code_learning(self, code_learning: dict[str, Any]) -> None:
        """从 code_learning 结果构建符号白名单.

        Args:
            code_learning: 任务一代码学习产物, 含 file_index / repo_map / code_graph
        """
        if not isinstance(code_learning, dict):
            logger.warning("O4-P0-B: code_learning 非 dict, 跳过符号白名单构建")
            return

        # 1. 文件路径集合 (用于排除路径型标识符)
        file_index = code_learning.get("file_index", {})
        if isinstance(file_index, dict):
            for f in file_index.get("files", []):
                if isinstance(f, dict):
                    path = f.get("path", "")
                    if path:
                        self._file_paths.add(path)
                        # 将路径最后一段的文件名 (去扩展名) 加入符号集 (如 UserController.cs -> UserController)
                        filename = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                        name_without_ext = filename.rsplit(".", 1)[0]
                        if name_without_ext and len(name_without_ext) >= _MIN_IDENTIFIER_LENGTH:
                            self._symbol_set.add(name_without_ext)

        # 2. 从 repo_map 提取符号 (class/def/func 签名行)
        repo_map_text = code_learning.get("repo_map", "")
        if isinstance(repo_map_text, str):
            self._extract_symbols_from_repo_map(repo_map_text)
            # v7-P0-B: 从 import/using 语句提取外部库符号
            self._extract_external_symbols_from_repo_map(repo_map_text)

        # 3. 从 code_graph 提取符号节点
        code_graph = code_learning.get("code_graph", {})
        if isinstance(code_graph, dict):
            for node in code_graph.get("nodes", []):
                if isinstance(node, dict):
                    name = node.get("name", "")
                    if name and len(name) >= _MIN_IDENTIFIER_LENGTH:
                        self._symbol_set.add(name)

        # v9 新增: 从 project_metadata_text 动态提取品牌名/项目名作为排除项
        # 避免硬编码特定项目名 (用户补充要求 #2: 不硬编码特定项目)
        # 品牌名不是代码符号, 不应被校验为幻觉符号
        project_metadata_text = code_learning.get("project_metadata_text", "")
        if isinstance(project_metadata_text, str) and project_metadata_text:
            self._extract_brand_names_from_metadata(project_metadata_text)

        # v9 新增: 从 glossary_text 提取 forced_original_terms 作为排除项
        glossary_text = code_learning.get("glossary_text", "")
        if isinstance(glossary_text, str) and glossary_text:
            self._extract_forced_terms_from_glossary(glossary_text)

        self._built = True
        logger.info(
            "O4-P0-B: 符号白名单构建完成: %d 个符号, %d 个文件路径, %d 个排除项",
            len(self._symbol_set),
            len(self._file_paths),
            len(self._excluded_terms),
        )

    def _extract_brand_names_from_metadata(self, metadata_text: str) -> None:
        """v9: 从 project_metadata_text 提取品牌名/项目名作为排除项.

        品牌名 (如 PascalCase 项目名) 不是代码符号, 不应被校验为幻觉符号.
        从 metadata_text 中提取 PascalCase 标识符作为排除项.

        设计原则: 不硬编码特定项目名, 从实际 metadata 动态提取.
        """
        # 从 "项目名: XxxYyy" 格式提取
        m = re.search(r"项目名[:：]\s*([A-Za-z][A-Za-z0-9_\-]+)", metadata_text)
        if m:
            self._excluded_terms.add(m.group(1))
        # 从 "品牌名清单" 行提取 PascalCase 标识符
        brand_line = re.search(r"品牌名清单[^:：]*[:：]\s*([^\n]+)", metadata_text)
        if brand_line:
            brands = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", brand_line.group(1))
            for brand in brands:
                if len(brand) >= 3:
                    self._excluded_terms.add(brand)

    def _extract_forced_terms_from_glossary(self, glossary_text: str) -> None:
        """v9: 从 glossary_text 提取 forced_original_terms 作为排除项.

        forced_original_terms 中的术语 (如 Agent/Trace/Observation) 是强制保留的英文术语,
        不是代码符号, 不应被校验为幻觉符号.
        """
        # 从 "强制保留原文术语" 段落提取
        forced_section = re.search(
            r"强制保留原文术语[^\n]*\n([^\n#]+)",
            glossary_text,
        )
        if forced_section:
            terms = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", forced_section.group(1))
            for term in terms:
                if len(term) >= 3:
                    self._excluded_terms.add(term)

    def _extract_symbols_from_repo_map(self, repo_map: str) -> None:
        """从 repo_map 文本提取符号 (class/def/func 签名行).

        repo_map 格式:
            src/foo.py:
              class Foo(Bar):
                def method1(self, x: int) -> str
              def func1(x: int) -> int
            API/Controllers/UserController.cs:
              public class UserController : ControllerBase
              public async Task<IActionResult> Login(...)
        """
        for line in repo_map.split("\n"):
            stripped = line.lstrip("│⋮ \t ")
            if not stripped:
                continue

            # Python: class Foo / def foo / async def foo
            if stripped.startswith(("class ", "def ", "async def ")):
                parts = stripped.split("(")[0].split()
                if len(parts) >= 2:
                    symbol = parts[-1].split(":")[0].split("=")[0].strip()
                    if symbol and len(symbol) >= _MIN_IDENTIFIER_LENGTH:
                        self._symbol_set.add(symbol)
                continue

            # C# / Java: public/private/protected/internal 修饰符开头
            if stripped.startswith(("public ", "private ", "protected ", "internal ", "static ")):
                # 移除修饰符链
                tokens = stripped.split()
                # 找到类型后的标识符 (简化: 取 ( 后第一个 token, 或 { 前一个 token)
                # 示例: "public async Task<IActionResult> Login(...)" -> "Login"
                #       "public class UserController : ControllerBase" -> "UserController"
                paren_idx = stripped.find("(")
                brace_idx = stripped.find("{")
                colon_idx = stripped.find(":")
                end_idx = min(
                    x for x in [paren_idx, brace_idx, colon_idx, len(stripped)] if x >= 0
                )
                sig_part = stripped[:end_idx].strip()
                sig_tokens = sig_part.split()
                if len(sig_tokens) >= 2:
                    # 最后一个 token 通常是符号名 (可能是 "Login" 或 "UserController")
                    symbol = sig_tokens[-1].split("<")[0].split(">")[-1].strip("({[:;,")
                    if symbol and len(symbol) >= _MIN_IDENTIFIER_LENGTH:
                        self._symbol_set.add(symbol)

            # namespace 声明
            if stripped.startswith("namespace "):
                parts = stripped.split()
                if len(parts) >= 2:
                    ns = parts[1].split(".")[0].strip("{")
                    if ns and len(ns) >= _MIN_IDENTIFIER_LENGTH:
                        self._symbol_set.add(ns)

    def _extract_external_symbols_from_repo_map(self, repo_map: str) -> None:
        """v7-P0-B: 从 repo_map 的 import/using 语句提取外部库符号.

        项目代码中引用的外部库类名 (如 MediatR / FastAPI / SqlSugarClient)
        虽然 AST 抽取不到定义, 但在 import/using 语句中出现, 应加入白名单.

        示例:
          using MediatR;                       -> MediatR
          using Microsoft.Extensions.Caching;  -> Caching (末段)
          from fastapi import FastAPI          -> FastAPI
          import langgraph                     -> langgraph
        """
        for line in repo_map.split("\n"):
            stripped = line.strip()
            # C# using 语句
            if stripped.startswith("using "):
                # using MediatR; -> MediatR
                # using Microsoft.Extensions.Caching.Memory; -> Memory
                ns = stripped[6:].rstrip(";").strip()
                if ns:
                    last_seg = ns.split(".")[-1]
                    if last_seg and len(last_seg) >= _MIN_IDENTIFIER_LENGTH:
                        self._symbol_set.add(last_seg)
            # Python import 语句
            elif stripped.startswith("import "):
                mod = stripped[7:].split(" as ")[0].split(",")[0].strip()
                if mod:
                    last_seg = mod.split(".")[-1]
                    if last_seg and len(last_seg) >= _MIN_IDENTIFIER_LENGTH:
                        self._symbol_set.add(last_seg)
            # Python from import 语句
            elif stripped.startswith("from "):
                # from fastapi import FastAPI, HTTPException -> FastAPI, HTTPException
                parts = stripped.split(" import ")
                if len(parts) == 2:
                    names = parts[1].split(",")
                    for n in names:
                        n = n.strip().split(" as ")[0].strip()
                        if n and len(n) >= _MIN_IDENTIFIER_LENGTH:
                            self._symbol_set.add(n)

    def validate_document(
        self,
        doc_text: str,
        *,
        allow_unknown: bool = False,
    ) -> dict[str, Any]:
        """校验文档中的标识符是否命中符号白名单.

        Args:
            doc_text: 生成的文档 Markdown 文本
            allow_unknown: True 时不校验 (降级模式)

        Returns:
            {
                "valid": bool,                # 是否通过校验
                "hallucinated_symbols": list, # 不在白名单的标识符 (最多 50 个)
                "total_identifiers": int,     # 文档中提取的标识符总数
                "matched_count": int,         # 命中白名单的标识符数
            }
        """
        if not self._built or allow_unknown:
            return {
                "valid": True,
                "hallucinated_symbols": [],
                "total_identifiers": 0,
                "matched_count": 0,
            }

        # 提取文档中所有候选标识符
        candidates = set(_IDENTIFIER_PATTERN.findall(doc_text))
        # 过滤常见单词
        candidates = {c for c in candidates if c not in _COMMON_WORDS and len(c) >= _MIN_IDENTIFIER_LENGTH}
        # v5-P0-D: 过滤文档编号 (AC1/FR-001 等) 和常见技术缩写 (HMAC/SHA256 等)
        candidates = {c for c in candidates if not _is_doc_id_or_abbrev(c)}

        if not candidates:
            return {
                "valid": True,
                "hallucinated_symbols": [],
                "total_identifiers": 0,
                "matched_count": 0,
            }

        # 命中白名单的标识符
        matched = {c for c in candidates if c in self._symbol_set}
        # 不在白名单的标识符 (可能为幻觉)
        hallucinated = sorted(candidates - matched)

        # 过滤明显为路径组件的标识符 (如 "src", "API", "Controllers" - 这些不是符号)
        hallucinated = [
            s for s in hallucinated
            if not any(s in path for path in self._file_paths)
        ]

        # v7-P0-B: 后缀模式宽松校验
        # XxxService/XxxHandler/XxxController 等通用接口/类名, 即使不在白名单
        # 也不判为幻觉 (可能是真实存在但未被 AST 抽取的接口/依赖注入类)
        hallucinated = [
            s for s in hallucinated
            if not any(s.endswith(suffix) for suffix in _LOOSE_SUFFIXES)
        ]

        # v9 新增: 过滤动态排除项 (品牌名/项目名/强制保留术语)
        # 这些术语不是代码符号, 不应被校验为幻觉符号
        hallucinated = [s for s in hallucinated if s not in self._excluded_terms]

        return {
            "valid": len(hallucinated) == 0,
            "hallucinated_symbols": hallucinated[:50],
            "total_identifiers": len(candidates),
            "matched_count": len(matched),
        }


__all__ = ["SymbolValidator"]
