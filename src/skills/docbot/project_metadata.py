"""v8-P0-A / v8-P0-H 项目元数据与配置规格提取.

职责:
1. v8-P0-A: 从 README.md / AGENTS.md / 构建文件提取项目名/品牌名/域名/技术栈
   (解决 LLM 捏造品牌名的问题, 将真实项目名作为不可变上下文注入所有 prompt)
2. v8-P0-H: 从配置文件提取技术规格键值
   (解决 LLM 捏造技术规格数值的问题, 如过期时间/分页大小, 强制引用真实值)

设计原则:
- 失败降级: 单文件提取失败不影响其他文件, 不阻断主流程 (logger.warning)
- 通用性: 不硬编码任何项目名/字段名, 规则适用于任何代码仓库
- 函数级元数据: 借鉴 Mintlify Writer 的函数级元数据注释, 每个函数说明设计理由
- 项目级规则: 借鉴 Cline .clinerules, 输出文本含强制约束说明, 注入所有 prompt
- 安全合规: 敏感键 (password/secret/token/api_key 等) 过滤, 不入 prompt
  (属 AGENTS.md 第 11 章 PII/密钥硬约束)
- 无外部依赖: 仅用标准库 (json/re/pathlib/logging), 避免引入 yaml/tomli 等依赖

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ========== 常量 ==========

# README 候选文件名 (大小写变体, 按优先级排序)
_README_CANDIDATES: tuple[str, ...] = ("README.md", "README.rst", "readme.md", "README.MD")

# 构建文件 glob 模式 (覆盖主流语言)
# v9-P0-D: 新增 *.sln (.NET 解决方案文件, 项目名最直接来源)
_BUILD_FILE_PATTERNS: tuple[str, ...] = (
    "*.sln",  # v9-P0-D: .NET 解决方案文件 (优先级高于 .csproj)
    "*.csproj",
    "*.fsproj",
    "*.vbproj",
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
)

# 构建文件查找时跳过的目录 (与 repo_loader.py 文件枚举跳过列表对齐)
_SKIP_DIRS: frozenset[str] = frozenset({
    ".git", "node_modules", "__pycache__", "dist", "build", ".venv",
    ".next", "target", "bin", "obj", ".idea", ".vscode", "vendor",
})

# 域名正则: 匹配 xxx.com / xxx.ai / xxx.io / xxx.cn / xxx.org / xxx.net / xxx.dev
# 不捕获协议前缀, 仅捕获裸域名 (含子域)
_DOMAIN_PATTERN = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"(?:com|ai|io|cn|org|net|dev)\b"
)

# 域名提取上限 (避免噪声)
_MAX_DOMAINS = 8

# 技术栈提取上限 (避免 prompt 膨胀)
_MAX_TECH_STACK = 30

# 品牌名清单提取上限
_MAX_BRAND_NAMES = 10

# .NET 配置 glob 模式 (递归扫描)
_DOTNET_CONFIG_GLOBS: tuple[str, ...] = ("appsettings.json", "appsettings.*.json")

# .NET 其他配置文件名 (递归扫描)
_DOTNET_CONFIG_NAMES: tuple[str, ...] = (
    "jwtsettings.json",
    "swaggersettings.json",
    "captchasettings.json",
    "envsettings.json",
)

# Python 配置文件名 (递归扫描)
_PYTHON_CONFIG_NAMES: tuple[str, ...] = ("config.py", "settings.py")

# Java 配置文件 glob 模式 (递归扫描)
_JAVA_CONFIG_GLOBS: tuple[str, ...] = (
    "application.properties",
    "application-*.properties",
    "application.yml",
    "application.yaml",
    "application-*.yml",
    "application-*.yaml",
)

# Go 配置文件 glob 模式 (根目录 + 一级子目录)
_GO_CONFIG_GLOBS: tuple[str, ...] = ("*.yaml", "*.yml", "*.toml")

# KV 赋值正则: 匹配 `KEY = VALUE` / `KEY: VALUE` (VALUE 可选引号, 忽略行尾注释)
_KV_PATTERN = re.compile(
    r'^(\w[\w.\-]*)\s*[:=]\s*["\']?([^"\'\n#]+)["\']?\s*(?:#.*)?$',
    re.MULTILINE,
)

# 敏感键过滤正则 (避免密钥/密码入 prompt, 属第 11 章 PII/密钥硬约束)
# 仅过滤明显密钥/密码模式, 不过滤业务配置键
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key|credential|cert|passphrase)",
    re.IGNORECASE,
)

# 单个配置文件最大尺寸 (避免读超大文件阻塞主流程)
_MAX_CONFIG_FILE_SIZE = 512 * 1024  # 512 KB

# prompt 中单值截断长度 (避免 prompt 膨胀)
_MAX_VALUE_LENGTH_IN_PROMPT = 200


# ========== v8-P0-A: 项目元数据提取 ==========


def extract_project_metadata(repo_path: str, file_index: dict | None = None) -> dict[str, Any]:
    """提取项目元数据 (项目名/品牌名/域名/技术栈).

    设计理由 (借鉴 Mintlify Writer 函数级元数据):
    将"项目名/品牌名"作为不可变元数据, 在所有 prompt 顶部强制注入,
    解决 LLM 在生成文档时将真实项目名翻译或捏造为其他品牌名的问题.

    提取顺序 (优先级从高到低, 后者仅在前者为空时填充):
    1. README.md 首个 `# 标题` (人类可读项目名, 最权威)
    2. AGENTS.md 首个 `# 标题` (项目规范文档, 标题通常为 "项目名 — 描述" 形式)
    3. 构建文件中的项目名字段 (.csproj `<AssemblyName>` / package.json `name` /
       pyproject.toml `name` / go.mod `module` / Cargo.toml `name` / pom.xml `<artifactId>`)

    Args:
        repo_path: 仓库本地路径 (绝对路径)
        file_index: 文件索引 (可选, 当前实现未使用, 保留接口供未来快速定位元数据文件)

    Returns:
        元数据字典, 字段:
        - project_name: str, 项目名 (英文, 不可翻译)
        - project_name_zh: str, 项目中文名 (如有, 否则为空字符串)
        - brand_names: list[str], 品牌名清单 (项目名 + PascalCase 子词, 不可翻译)
        - domains: list[str], 域名清单 (从 README/AGENTS.md 正则提取)
        - tech_stack: list[str], 技术栈 (从构建文件的依赖声明提取)
        - build_files: list[str], 构建文件相对路径列表 (用于 scope 识别)

        任一字段提取失败时返回空值 (空字符串 / 空列表), 不抛异常.
    """
    repo = Path(repo_path)
    metadata: dict[str, Any] = {
        "project_name": "",
        "project_name_zh": "",
        "brand_names": [],
        "domains": [],
        "tech_stack": [],
        "build_files": [],
    }

    if not repo.exists() or not repo.is_dir():
        logger.warning("v8-P0-A: 仓库路径无效或不存在: %s", repo_path)
        return metadata

    domains: list[str] = []
    tech_stack: list[str] = []

    # 1. 从 README.md 提取项目名 + 中文名 + 域名 (最权威来源)
    readme_path = _find_file(repo, list(_README_CANDIDATES))
    if readme_path is not None:
        project_name, project_name_zh, readme_domains = _extract_from_readme(readme_path)
        if not metadata["project_name"] and project_name:
            metadata["project_name"] = project_name
        if not metadata["project_name_zh"] and project_name_zh:
            metadata["project_name_zh"] = project_name_zh
        domains.extend(readme_domains)

    # 2. 从 AGENTS.md 提取项目名 + 域名 (README 未提取到时降级)
    if not metadata["project_name"]:
        agents_md_path = _find_file(repo, ["AGENTS.md"])
        if agents_md_path is not None:
            project_name, agents_domains = _extract_from_agents_md(agents_md_path)
            if project_name:
                metadata["project_name"] = project_name
            domains.extend(agents_domains)

    # 3. 从构建文件提取项目名 + 技术栈 (机器可读来源)
    build_files = _find_build_files(repo)
    metadata["build_files"] = [
        str(p.relative_to(repo)).replace("\\", "/") for p in build_files
    ]
    for bf in build_files:
        name, deps = _extract_from_build_file(bf)
        if not metadata["project_name"] and name:
            metadata["project_name"] = name
        tech_stack.extend(deps)

    # 4. 域名去重 + 截断 (保持插入顺序)
    metadata["domains"] = list(dict.fromkeys(domains))[:_MAX_DOMAINS]

    # 5. 技术栈去重 + 截断 (保持插入顺序)
    metadata["tech_stack"] = list(dict.fromkeys(tech_stack))[:_MAX_TECH_STACK]

    # 6. 品牌名清单: 项目名 + PascalCase 子词 + 全大写缩写
    metadata["brand_names"] = _build_brand_names(metadata["project_name"])

    logger.info(
        "v8-P0-A: 项目元数据提取完成: project_name=%s, brand_names=%d, domains=%d, tech_stack=%d, build_files=%d",
        metadata["project_name"] or "(空)",
        len(metadata["brand_names"]),
        len(metadata["domains"]),
        len(metadata["tech_stack"]),
        len(metadata["build_files"]),
    )
    return metadata


def format_metadata_for_prompt(metadata: dict[str, Any]) -> str:
    """格式化项目元数据为可注入 prompt 的文本.

    设计理由 (借鉴 Cline .clinerules 项目级规则):
    输出文本含强制约束说明 (禁止翻译/禁止捏造), 作为不可变规则块注入所有 prompt 顶部,
    让 LLM 在生成文档时严格遵守真实项目名与品牌名.

    Args:
        metadata: extract_project_metadata() 返回的元数据字典

    Returns:
        可直接注入 prompt 的多行文本. 元数据为空时返回降级提示,
        不抛异常 (不阻断主流程).
    """
    if not metadata or not metadata.get("project_name"):
        return (
            "(项目元数据未提取到, 请从代码仓库 README/构建文件推断项目名, "
            "禁止捏造品牌名)"
        )

    lines: list[str] = ["# 项目元数据 (v8-P0-A 强制约束, 禁止修改/翻译)"]
    lines.append(
        f"- 项目名: {metadata['project_name']} "
        "(必须使用此名称, 禁止翻译为其他语言, 禁止捏造其他品牌名)"
    )
    if metadata.get("project_name_zh"):
        lines.append(f"- 项目中文名: {metadata['project_name_zh']}")
    if metadata.get("brand_names"):
        lines.append(
            f"- 品牌名清单 (禁止翻译, 必须保留原文): {', '.join(metadata['brand_names'])}"
        )
    if metadata.get("domains"):
        lines.append(
            f"- 域名 (必须使用上述真实域名, 禁止捏造): {', '.join(metadata['domains'])}"
        )
    if metadata.get("tech_stack"):
        lines.append(f"- 技术栈: {', '.join(metadata['tech_stack'][:15])}")
    lines.append("")
    lines.append("# 强制规则 (违反将导致文档校验失败):")
    lines.append("1. 必须使用上述项目名, 禁止翻译为其他语言, 禁止捏造其他品牌名")
    lines.append("2. 品牌名清单中的所有词必须保留原文, 禁止翻译或缩写")
    lines.append("3. 域名必须使用上述真实域名, 禁止捏造")
    lines.append("4. 技术栈描述必须与上述真实依赖一致, 禁止捏造未列出的框架")
    return "\n".join(lines)


# ========== v8-P0-A 内部辅助函数 ==========


def _find_file(repo: Path, names: list[str]) -> Path | None:
    """在仓库根目录查找文件 (不递归, 按 names 顺序匹配).

    设计理由: 元数据文件 (README/AGENTS.md) 通常位于根目录,
    不递归避免误匹配子目录同名文件.

    Args:
        repo: 仓库根 Path
        names: 候选文件名列表 (按优先级排序)

    Returns:
        首个匹配的文件 Path, 未找到返回 None.
    """
    for name in names:
        path = repo / name
        if path.exists() and path.is_file():
            return path
    return None


def _find_build_files(repo: Path) -> list[Path]:
    """查找根目录及一级子目录的构建文件 (识别 monorepo 子项目).

    设计理由: 单仓库构建文件位于根目录; monorepo 子项目构建文件位于一级子目录
    (如 `services/foo/package.json`), 仅扫描一级避免深层递归性能损耗.

    Args:
        repo: 仓库根 Path

    Returns:
        构建文件 Path 列表 (根目录优先, 子目录按字母序).
    """
    result: list[Path] = []
    # 根目录构建文件
    for pattern in _BUILD_FILE_PATTERNS:
        result.extend(sorted(repo.glob(pattern)))
    # 一级子目录构建文件 (识别 monorepo)
    for sub in sorted(repo.iterdir()):
        if not sub.is_dir():
            continue
        if sub.name in _SKIP_DIRS or sub.name.startswith("."):
            continue
        for pattern in _BUILD_FILE_PATTERNS:
            result.extend(sorted(sub.glob(pattern)))
    return result


def _extract_from_readme(readme_path: Path) -> tuple[str, str, list[str]]:
    """从 README 提取项目名/中文名/域名.

    设计理由: README 首个 `# 标题` 是人类可读项目名的最权威来源;
    域名 (xxx.com/xxx.ai/...) 出现在 README 中通常为项目官方域名, 必须保留原文;
    标题若含 "项目名 — 中文描述" 形式, 同时提取中文名.

    Args:
        readme_path: README 文件 Path

    Returns:
        (project_name, project_name_zh, domains) 三元组.
        提取失败时对应字段为空字符串 / 空列表, 不抛异常.
    """
    project_name = ""
    project_name_zh = ""
    domains: list[str] = []

    try:
        content = readme_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-A: 读取 README 失败 (%s): %s", readme_path, e)
        return project_name, project_name_zh, domains

    # 提取首个 # 标题
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        # 移除 emoji 与 markdown 修饰符
        title = re.sub(r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF]", "", title).strip()
        title = re.sub(r"[*_`]", "", title).strip()
        if title and len(title) <= 100:
            # 标题可能为 "ProjectName — 中文描述" / "ProjectName - 中文描述" 形式
            # 仅按 "空格+分隔符+空格" 分割, 保留含连字符的项目名 (如 my-project)
            first_token = re.split(r"\s+[-—/]\s+", title, maxsplit=1)[0].strip()
            if first_token:
                project_name = first_token
                # 若标题含中文部分, 作为中文名
                if len(first_token) < len(title):
                    zh_part = title[len(first_token):].lstrip("-—/ ").strip()
                    if zh_part and re.search(r"[\u4e00-\u9fff]", zh_part):
                        project_name_zh = zh_part

    # 提取域名 (xxx.com/xxx.ai/xxx.io/xxx.cn/xxx.org/xxx.net/xxx.dev)
    domains = _DOMAIN_PATTERN.findall(content)

    return project_name, project_name_zh, domains


def _extract_from_agents_md(agents_md_path: Path) -> tuple[str, list[str]]:
    """从 AGENTS.md 提取项目名 (降级来源) + 域名.

    设计理由: 当 README 缺失或无 # 标题时, AGENTS.md 标题
    通常为 "项目名 — LangGraph AI Agent 执行规则" 形式, 首个 token 即为项目名.

    Args:
        agents_md_path: AGENTS.md 文件 Path

    Returns:
        (project_name, domains) 二元组. 提取失败时为空字符串 / 空列表.
    """
    project_name = ""
    domains: list[str] = []

    try:
        content = agents_md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-A: 读取 AGENTS.md 失败 (%s): %s", agents_md_path, e)
        return project_name, domains

    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        title = re.sub(r"[*_`]", "", m.group(1).strip())
        if title and len(title) <= 100:
            first_token = re.split(r"\s+[-—/]\s+", title, maxsplit=1)[0].strip()
            if first_token:
                project_name = first_token

    domains = _DOMAIN_PATTERN.findall(content)
    return project_name, domains


def _extract_from_build_file(build_file: Path) -> tuple[str, list[str]]:
    """从构建文件提取项目名 + 依赖清单 (技术栈).

    设计理由: 构建文件是项目名的"机器可读"权威来源, 当 README/AGENTS.md 缺失时降级使用;
    依赖清单直接反映真实技术栈, 避免凭空捏造框架名.

    支持构建文件:
    - .NET: *.csproj / *.fsproj / *.vbproj
      (`<AssemblyName>` / `<PackageReference Include="...">`)
    - Node: package.json (`name` / `dependencies` + `devDependencies` + `peerDependencies`)
    - Python: pyproject.toml (`name = "..."` / `dependencies = [...]`)
    - Go: go.mod (`module ...` / require 块)
    - Rust: Cargo.toml (`name = "..."` / `[dependencies]` 段)
    - Java: pom.xml (`<artifactId>` / `<dependency>`)

    Args:
        build_file: 构建文件 Path

    Returns:
        (project_name, dependencies) 二元组. 提取失败时为空字符串 / 空列表.
    """
    project_name = ""
    dependencies: list[str] = []

    try:
        if build_file.stat().st_size > _MAX_CONFIG_FILE_SIZE:
            logger.warning("v8-P0-A: 构建文件过大, 跳过: %s", build_file)
            return project_name, dependencies
        content = build_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-A: 读取构建文件失败 (%s): %s", build_file, e)
        return project_name, dependencies

    suffix = build_file.suffix.lower()
    name = build_file.name

    if suffix == ".sln":
        # v9-P0-D 新增: .NET 解决方案文件, 文件名 stem 作为 project_name
        # 例如 AgentInsightService.sln → AgentInsightService
        # .sln 文件名是最直接的项目名来源, 优先级高于 .csproj
        project_name = build_file.stem
        # 从 .sln 内容提取 C# 项目依赖 (SharpDevelop/MSBuild 格式)
        # 项目引用: Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "ProjectName", "Path\To.csproj", ...
        # 仅提取 PackageReference 不在此处处理 (.sln 不含包引用, 由 .csproj 处理)
        # 但可提取解决方案中引用的项目名作为 brand_names 候选
        sln_project_names = re.findall(r'^\s*Project\([^)]*\)\s*=\s*"([^"]+)"', content, re.MULTILINE)
        # sln_project_names 包含项目名, 不加入 dependencies (避免污染技术栈)
        # 但若 project_name 为空, 用首个项目名兜底
        if not project_name and sln_project_names:
            project_name = sln_project_names[0]
    elif suffix in {".csproj", ".fsproj", ".vbproj"}:
        # .NET 项目文件
        # 1. 优先从 <AssemblyName> 提取
        m = re.search(r"<AssemblyName>([^<]+)</AssemblyName>", content)
        if m:
            project_name = m.group(1).strip()
        # v9-P0-D 新增: 2. 兜底用 .csproj 文件名 stem (AssemblyName 缺失时)
        # 例如 AgentInsightService.csproj → AgentInsightService
        if not project_name:
            project_name = build_file.stem
        # <PackageReference Include="xxx" Version="..." />
        pkgs = re.findall(r'<PackageReference\s+Include="([^"]+)"', content)
        dependencies.extend(pkgs)
    elif name == "package.json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("v8-P0-A: package.json 解析失败 (%s): %s", build_file, e)
            return project_name, dependencies
        if isinstance(data, dict):
            project_name = str(data.get("name", "") or "")
            for dep_key in ("dependencies", "devDependencies", "peerDependencies"):
                deps = data.get(dep_key, {})
                if isinstance(deps, dict):
                    dependencies.extend(list(deps.keys()))
    elif name == "pyproject.toml":
        # PEP 621: name = "xxx" (在 [project] 段)
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            project_name = m.group(1).strip()
        # dependencies = ["xxx", "xxx>=1.0", ...]
        deps_match = re.search(
            r"dependencies\s*=\s*\[([^\]]*)\]",
            content,
            re.MULTILINE | re.DOTALL,
        )
        if deps_match:
            deps = re.findall(r'"([^"]+)"', deps_match.group(1))
            # 依赖项可能含版本约束 (如 "fastapi>=0.115"), 仅保留包名部分
            for dep in deps:
                pkg = re.split(r"[><=!~;\[]", dep, maxsplit=1)[0].strip()
                if pkg:
                    dependencies.append(pkg)
    elif name == "go.mod":
        # module github.com/user/repo
        m = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
        if m:
            module_path = m.group(1).strip()
            project_name = module_path.rsplit("/", 1)[-1]
        # require 块: github.com/xxx/yyy v1.2.3
        deps = re.findall(r"^\s*(\S+)\s+v[\d.]+\s*$", content, re.MULTILINE)
        dependencies.extend(deps)
    elif name == "Cargo.toml":
        # name = "xxx" (在 [package] 段)
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            project_name = m.group(1).strip()
        # [dependencies] 段下的 `xxx = "version"` / `xxx = { version = "..." }`
        deps = re.findall(
            r'^\s*([a-zA-Z0-9_-]+)\s*=\s*(?:"[^"]+"|\{[^}]*\})',
            content,
            re.MULTILINE,
        )
        # 过滤 [package] 段元字段 (name/version/edition/authors 等)
        meta_keys = {
            "name", "version", "edition", "authors", "description",
            "license", "repository", "homepage", "documentation",
            "keywords", "categories", "readme",
        }
        dependencies.extend(d for d in deps if d not in meta_keys)
    elif name == "pom.xml":
        # <artifactId>xxx</artifactId> (首个通常为项目自身)
        m = re.search(r"<artifactId>([^<]+)</artifactId>", content)
        if m:
            project_name = m.group(1).strip()
        # <dependency><artifactId>xxx</artifactId> ...
        deps = re.findall(r"<artifactId>([^<]+)</artifactId>", content)
        # 第一个通常是项目自身, 跳过
        if deps:
            dependencies.extend(deps[1:])

    return project_name, dependencies


def _build_brand_names(project_name: str) -> list[str]:
    """构建品牌名清单 (项目名 + PascalCase 子词 + 全大写缩写).

    设计理由: LLM 可能将 PascalCase 项目名拆开翻译 (如将复合项目名翻译为中文短语),
    将所有 PascalCase 子词与全大写缩写列入品牌名清单, 强制 LLM 保留原文.

    规则:
    1. 项目名本身加入清单
    2. 从项目名提取 PascalCase 相邻子词对 (滑动窗口, 长度 2 个 [A-Z][a-z]+ 段)
    3. 从项目名提取全大写缩写 (长度 >= 2, 如 SDK/API)
    4. 去重, 保持插入顺序

    Args:
        project_name: 项目名 (可能为空)

    Returns:
        品牌名清单 (最多 _MAX_BRAND_NAMES 项). 项目名为空时返回空列表.
    """
    if not project_name:
        return []

    brand_names: list[str] = [project_name]

    # 提取 PascalCase 相邻子词对 (滑动窗口)
    # 通用示例: 复合 PascalCase 名 -> 相邻两段组合
    words = re.findall(r"[A-Z][a-z]+", project_name)
    if len(words) >= 2:
        for i in range(len(words) - 1):
            sub = words[i] + words[i + 1]
            if sub != project_name and sub not in brand_names:
                brand_names.append(sub)

    # 提取全大写缩写 (如 SDK / API / AI, 长度 >= 2 避免单字母误匹配)
    acronyms = re.findall(r"\b[A-Z]{2,}\b", project_name)
    for acr in acronyms:
        if acr not in brand_names:
            brand_names.append(acr)

    return brand_names[:_MAX_BRAND_NAMES]


# ========== v8-P0-H: 配置文件技术规格提取 ==========


def extract_config_specs(repo_path: str) -> dict[str, Any]:
    """v8-P0-H: 从配置文件提取技术规格 (扁平键值字典).

    设计理由 (解决技术规格错误):
    LLM 在生成文档时常捏造技术规格数值 (如将配置文件中的真实过期时间写成其他值),
    本函数从配置文件提取真实键值, 注入 prompt 强制 LLM 引用真实值.

    扫描范围 (按语言生态, 通用规则适用于任何代码仓库):
    - .NET: appsettings.json / appsettings.*.json / jwtsettings.json /
            swaggersettings.json / captchasettings.json / envsettings.json
            (递归扫描, 跳过 bin/obj 目录, JSON 递归 flatten 为 `Section.Key` 路径)
    - Python: .env / config.py / settings.py (提取 `KEY = VALUE` 常量赋值)
    - Node: .env / *.env / config/*.json (env 提取 KV, JSON flatten)
    - Go: *.yaml / *.yml / *.toml (顶层 KV 提取, 无依赖降级)
    - Java: application.properties / application.yml / application-*.properties / application-*.yml

    Args:
        repo_path: 仓库本地路径 (绝对路径)

    Returns:
        扁平字典 {键路径: 值}. JSON 键路径为 `parent.child` 形式;
        .env/properties 键路径即原始键名.
        敏感键 (password/secret/token/api_key/private_key/credential 等) 已过滤,
        避免密钥入 prompt (属 AGENTS.md 第 11 章 PII/密钥硬约束).
        提取失败时返回空字典, 不抛异常.
    """
    repo = Path(repo_path)
    specs: dict[str, Any] = {}

    if not repo.exists() or not repo.is_dir():
        logger.warning("v8-P0-H: 仓库路径无效或不存在: %s", repo_path)
        return specs

    # 1. .NET 配置文件 (JSON, 递归 flatten)
    _collect_dotnet_configs(repo, specs)

    # 2. Python 配置文件 (.env / config.py / settings.py, KV 提取)
    _collect_python_configs(repo, specs)

    # 3. Node 配置文件 (config/*.json; *.env 已在 Python 收集中扫描, 跨语言通用)
    _collect_node_configs(repo, specs)

    # 4. Go 配置文件 (*.yaml / *.yml / *.toml, 顶层 KV 提取)
    _collect_go_configs(repo, specs)

    # 5. Java 配置文件 (application.properties / application.yml)
    _collect_java_configs(repo, specs)

    # 过滤敏感键 (密钥/密码不入 prompt, 属第 11 章硬约束)
    specs = {
        k: v for k, v in specs.items()
        if not _SENSITIVE_KEY_PATTERN.search(k)
    }

    logger.info("v8-P0-H: 配置规格提取完成: %d 项", len(specs))
    return specs


def format_config_specs_for_prompt(specs: dict[str, Any]) -> str:
    """格式化配置规格为可注入 prompt 的文本.

    设计理由: 与 format_metadata_for_prompt 配对, 作为 v8-P0-H 强制约束块注入 prompt,
    让 LLM 在描述技术规格时引用真实数值, 禁止捏造.

    Args:
        specs: extract_config_specs() 返回的扁平字典

    Returns:
        可直接注入 prompt 的多行文本. specs 为空时返回降级提示.
    """
    if not specs:
        return (
            "(未提取到配置文件规格, 请从代码仓库配置文件推断真实数值, "
            "禁止捏造技术规格)"
        )

    lines = ["# 配置文件技术规格 (v8-P0-H, 必须引用以下真实值)"]
    for k, v in sorted(specs.items()):
        # 截断过长值 (避免 prompt 膨胀)
        value_str = str(v)
        if len(value_str) > _MAX_VALUE_LENGTH_IN_PROMPT:
            value_str = value_str[:_MAX_VALUE_LENGTH_IN_PROMPT] + "..."
        lines.append(f"- {k} = {value_str}")
    lines.append("")
    lines.append("# 强制规则 (违反将导致文档校验失败):")
    lines.append("1. 技术规格数值必须引用上述真实值, 禁止捏造")
    lines.append("2. 若上述未列出某规格, 请从代码仓库配置文件推断, 禁止凭空填写")
    return "\n".join(lines)


# ========== v8-P0-H 内部辅助函数 ==========


def _flatten_json(data: Any, prefix: str, result: dict[str, Any]) -> None:
    """递归展平 JSON 为 {键路径: 值} 字典.

    设计理由: appsettings.json 等配置文件通常为嵌套 JSON,
    展平为 `parent.child.grandchild` 形式的键路径, 便于 LLM 引用具体配置项.

    Args:
        data: JSON 解析后的对象 (dict / list / scalar)
        prefix: 当前键路径前缀 (根为空字符串)
        result: 展平结果字典 (in-place 修改)
    """
    if isinstance(data, dict):
        for k, v in data.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)
            _flatten_json(v, new_prefix, result)
    elif isinstance(data, list):
        # 列表整体保留 (如允许的 IP 列表), 不展开索引
        # 避免键路径过深 (如 a.b.0.c.1.d) 导致 prompt 噪声
        if prefix:
            result[prefix] = data
    else:
        # 标量 (str/int/float/bool/None)
        if prefix:
            result[prefix] = data


def _safe_read_file(path: Path) -> str | None:
    """安全读取文件 (大小检查 + 异常降级).

    设计理由: 配置文件可能因权限/编码/体积异常导致读取失败,
    统一在此处降级返回 None, 不阻断主流程.

    Args:
        path: 文件 Path

    Returns:
        文件内容字符串, 失败返回 None.
    """
    try:
        if not path.exists() or not path.is_file():
            return None
        if path.stat().st_size > _MAX_CONFIG_FILE_SIZE:
            logger.warning("v8-P0-H: 配置文件过大, 跳过: %s", path)
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-H: 读取文件失败 (%s): %s", path, e)
        return None


def _is_in_skip_dir(path: Path, repo: Path) -> bool:
    """判断路径是否位于跳过目录 (bin/obj/node_modules 等) 内.

    设计理由: .NET 编译产物目录 (bin/obj) 可能含 appsettings.json 副本,
    node_modules 含大量依赖的配置文件, 必须跳过避免噪声与重复.

    Args:
        path: 待检查文件 Path
        repo: 仓库根 Path

    Returns:
        True 表示路径位于跳过目录内, 应跳过.
    """
    try:
        rel = path.relative_to(repo)
    except ValueError:
        return True
    return any(part in _SKIP_DIRS for part in rel.parts)


def _parse_kv_content(content: str) -> dict[str, str]:
    """从 KEY = VALUE / KEY: VALUE 模式文本提取键值对.

    设计理由: .env / config.py / application.properties 等使用 `KEY = VALUE` 赋值语法,
    YAML/TOML 顶层用 `KEY: VALUE` / `KEY = VALUE`, 统一用正则提取,
    忽略注释行 (# 开头) 与空行.

    Args:
        content: 文件内容字符串

    Returns:
        {KEY: VALUE} 字典. VALUE 去除首尾引号与空白.
    """
    result: dict[str, str] = {}
    for m in _KV_PATTERN.finditer(content):
        key = m.group(1)
        value = m.group(2).strip()
        if key and value:
            result[key] = value
    return result


def _collect_dotnet_configs(repo: Path, specs: dict[str, Any]) -> None:
    """收集 .NET 配置文件 (appsettings.json 等, JSON 递归 flatten).

    设计理由: .NET 配置为 JSON 格式, 递归 flatten 后键路径形如
    `Section.Key` / `Section.Subsection.Key`, 便于 LLM 引用具体配置项.
    跳过 bin/obj 目录避免编译产物副本噪声.

    Args:
        repo: 仓库根 Path
        specs: 累积结果的扁平字典 (in-place 修改)
    """
    seen: set[Path] = set()

    # appsettings.json + appsettings.*.json (递归扫描)
    for pattern in _DOTNET_CONFIG_GLOBS:
        for cfg_path in repo.rglob(pattern):
            if cfg_path in seen or _is_in_skip_dir(cfg_path, repo):
                continue
            seen.add(cfg_path)
            content = _safe_read_file(cfg_path)
            if content is None:
                continue
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning("v8-P0-H: JSON 解析失败 (%s): %s", cfg_path, e)
                continue
            if isinstance(data, dict):
                _flatten_json(data, prefix="", result=specs)

    # 其他 .NET 配置文件 (jwtsettings.json / captchasettings.json 等)
    for name in _DOTNET_CONFIG_NAMES:
        for cfg_path in repo.rglob(name):
            if cfg_path in seen or _is_in_skip_dir(cfg_path, repo):
                continue
            seen.add(cfg_path)
            content = _safe_read_file(cfg_path)
            if content is None:
                continue
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                _flatten_json(data, prefix="", result=specs)


def _collect_python_configs(repo: Path, specs: dict[str, Any]) -> None:
    """收集 Python 配置文件 (.env / *.env / config.py / settings.py).

    设计理由: Python 项目常用 .env / config.py / settings.py 定义常量,
    提取 `KEY = VALUE` 赋值, 键路径即变量名. *.env 扫描跨语言通用
    (Node 项目也用 .env), 在此处统一处理避免其他收集器重复扫描.

    Args:
        repo: 仓库根 Path
        specs: 累积结果的扁平字典 (in-place 修改)
    """
    # 根目录 .env
    env_path = repo / ".env"
    if env_path.exists() and env_path.is_file():
        content = _safe_read_file(env_path)
        if content:
            specs.update(_parse_kv_content(content))

    # 递归 *.env (排除 .env.template / .env.example 等模板文件)
    # 模板文件含示例值, 不应混入真实规格
    for cfg_path in repo.rglob("*.env"):
        if _is_in_skip_dir(cfg_path, repo):
            continue
        if cfg_path.name.endswith((".template", ".example", ".sample")):
            continue
        if cfg_path == env_path:
            continue
        content = _safe_read_file(cfg_path)
        if content:
            specs.update(_parse_kv_content(content))

    # config.py / settings.py (递归)
    for name in _PYTHON_CONFIG_NAMES:
        for cfg_path in repo.rglob(name):
            if _is_in_skip_dir(cfg_path, repo):
                continue
            content = _safe_read_file(cfg_path)
            if content:
                specs.update(_parse_kv_content(content))


def _collect_node_configs(repo: Path, specs: dict[str, Any]) -> None:
    """收集 Node 配置文件 (config/*.json).

    设计理由: Node 项目常用 config/*.json 定义分层配置, JSON 递归 flatten.
    *.env 已在 _collect_python_configs 中统一扫描 (跨语言通用), 此处不重复.

    Args:
        repo: 仓库根 Path
        specs: 累积结果的扁平字典 (in-place 修改)
    """
    # config/*.json (一级子目录 config 下的 JSON)
    config_dir = repo / "config"
    if config_dir.exists() and config_dir.is_dir():
        for cfg_path in config_dir.glob("*.json"):
            if _is_in_skip_dir(cfg_path, repo):
                continue
            content = _safe_read_file(cfg_path)
            if content is None:
                continue
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                _flatten_json(data, prefix="", result=specs)


def _collect_go_configs(repo: Path, specs: dict[str, Any]) -> None:
    """收集 Go 配置文件 (*.yaml / *.yml / *.toml, 顶层 KV 提取).

    设计理由: Go 项目常用 YAML / TOML 定义配置, 顶层 KV 直接提取,
    嵌套结构降级为空 (避免引入 yaml/tomli 依赖, 保持轻量).
    仅扫描根目录与一级子目录避免深层递归性能损耗.

    Args:
        repo: 仓库根 Path
        specs: 累积结果的扁平字典 (in-place 修改)
    """
    # 仅扫描根目录与一级子目录 (避免深层递归)
    candidates: list[Path] = []
    for pattern in _GO_CONFIG_GLOBS:
        candidates.extend(repo.glob(pattern))
        for sub in repo.iterdir():
            if not sub.is_dir() or sub.name in _SKIP_DIRS or sub.name.startswith("."):
                continue
            candidates.extend(sub.glob(pattern))

    for cfg_path in candidates:
        if _is_in_skip_dir(cfg_path, repo):
            continue
        content = _safe_read_file(cfg_path)
        if content is None:
            continue
        # YAML/TOML 顶层 KV 提取 (无依赖降级方案)
        kv = _parse_yaml_toml_top_level(content)
        specs.update(kv)


def _collect_java_configs(repo: Path, specs: dict[str, Any]) -> None:
    """收集 Java 配置文件 (application.properties / application.yml).

    设计理由: Spring Boot 项目用 application.properties / application.yml 定义配置,
    properties 文件为 `key=value` 格式 (键本身含 `.` 分层, 如 `server.port`),
    yml 为 YAML 格式, 统一提取顶层 KV.

    Args:
        repo: 仓库根 Path
        specs: 累积结果的扁平字典 (in-place 修改)
    """
    for pattern in _JAVA_CONFIG_GLOBS:
        for cfg_path in repo.rglob(pattern):
            if _is_in_skip_dir(cfg_path, repo):
                continue
            content = _safe_read_file(cfg_path)
            if content is None:
                continue
            # properties 与 yml 均用 _parse_kv_content 提取顶层 KV
            # properties: `key.subkey = value` / yml: `key: value`
            specs.update(_parse_kv_content(content))


def _parse_yaml_toml_top_level(content: str) -> dict[str, str]:
    """从 YAML/TOML 文本提取顶层 KV (无依赖降级方案).

    设计理由: 引入 pyyaml / tomli 增加依赖体积, 此处仅做轻量正则提取,
    覆盖 `key: value` (YAML) 与 `key = value` (TOML) 两种常见顶层形式.
    嵌套结构 / 多行字符串 / 锚点等复杂语法无法解析时降级为空, 不阻断主流程.

    Args:
        content: YAML / TOML 文件内容

    Returns:
        {KEY: VALUE} 字典 (仅顶层标量键). 复杂结构返回空字典.
    """
    result: dict[str, str] = {}
    # 仅匹配行首非缩进的 `key: value` (YAML) / `key = value` (TOML)
    # 排除注释行 (# 开头) 与节声明 ([xxx] / ---)
    pattern = re.compile(
        r'^([A-Za-z_][\w.\-]*)\s*[:=]\s*["\']?([^"\'\n#]+)["\']?\s*(?:#.*)?$'
    )
    for line in content.splitlines():
        m = pattern.match(line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            if key and value:
                result[key] = value
    return result
