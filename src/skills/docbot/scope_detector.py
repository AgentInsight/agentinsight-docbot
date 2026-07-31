"""v8-P0-E: 仓库 Scope 识别 (解决 monorepo 子项目污染).

职责:
1. 递归扫描根目录和一级子目录的构建文件, 识别 monorepo 子项目边界
2. 标记每个子项目的语言 / AGENTS.md / README 状态
3. is_in_scope 初始为 "unknown", 由 outline_refiner LLM 基于 AGENTS.md 声明判断
4. 格式化 Scope 信息注入 prompt, 强制约束仅描述 In-Scope 子项目

设计理由:
- 借鉴 monorepo 工具 (nx / turborepo) 的项目识别机制: 通过构建文件
  (*.csproj / package.json / pyproject.toml / go.mod / Cargo.toml / pom.xml /
  build.gradle / manage.py) 定位子项目边界, 而非依赖目录名约定
- 借鉴 AGENTS.md 的项目级声明约定: 子项目若含独立 AGENTS.md, 通常声明为
  独立产品, outline_refiner 可据此判断 Out-of-Scope
- 解决 "Out-of-Scope 内容污染" 问题: 参考文档把某些子项目列为 Out-of-Scope,
  生成文档却把整个仓库作为单一系统描述

失败降级:
- 仓库路径无效 / 扫描异常时返回空 Scope 结构, 仅告警, 不阻断主流程

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ========== 常量 ==========

# 构建文件 glob 模式 (根目录 + 一级子目录均扫描)
# 设计理由: 覆盖主流语言的构建文件, 与 nx/turborepo 的 project.json 类似,
# 通过构建文件存在性判定子项目边界, 避免依赖目录名约定
_BUILD_FILE_PATTERNS: tuple[str, ...] = (
    "*.csproj",
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "manage.py",
)

# v10-P0-4: 主项目入口文件提示 (用于启发式 scope 决策)
# 借鉴 Aider personalization: 主项目入口文件赋予高权重, 用于识别主项目
_MAIN_ENTRY_HINTS: tuple[str, ...] = (
    "Program.cs", "Main.cs",          # .NET 主入口
    "Startup.cs",                     # .NET 启动配置
    "manage.py", "main.py", "app.py", # Python 主入口
    "main.go",                        # Go 主入口
    "index.ts", "index.js", "main.ts", "main.js",  # Node 主入口
    "Application.java",               # Java Spring Boot
)

# v10-P0-4: API 构建文件 (非测试项目)
_API_BUILD_FILES: tuple[str, ...] = (
    "*.csproj",  # .NET API 项目 (排除测试项目)
)

# v10-P0-4: 辅助子项目名称 (Out-of-Scope 候选)
# 借鉴 Sweep.dev SWEEP.md: 从子项目名称推断 scope
_AUXILIARY_SCOPE_NAMES: frozenset[str] = frozenset({
    "sdk", "client", "clients", "docs", "doc", "examples",
    "demo", "benchmarks", "tests", "test", "scripts",
    "tools", "utils", "shared",
})

# 排除目录 (不作为子项目扫描)
# 设计理由: 这些目录为构建产物 / 依赖缓存 / 第三方代码, 非业务子项目
_EXCLUDED_DIRS: frozenset[str] = frozenset({
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    "bin",
    "obj",
    "packages",
    "vendor",
    "target",
})


# ========== 主入口 ==========


def detect_scopes(repo_path: str) -> dict[str, Any]:
    """v8-P0-E: 检测仓库 Scope (子项目边界).

    递归扫描根目录和一级子目录的构建文件, 识别 monorepo 子项目.
    借鉴 nx/turborepo 的项目识别机制 (构建文件定位) + AGENTS.md 项目级声明.

    Args:
        repo_path: 仓库本地路径

    Returns:
        {
            "is_monorepo": bool,
            "scopes": [
                {
                    "name": "子项目名",
                    "path": "子项目/",
                    "build_file": "子项目/*.csproj",
                    "language": "csharp|python|node|go|rust|java",
                    "has_agents_md": bool,
                    "has_readme": bool,
                    "is_in_scope": "unknown",  # 由 outline_refiner LLM 判断
                },
                ...
            ],
            "root_scope": {
                "name": "<repo_name>",
                "path": ".",
                "build_files": ["package.json", ...],
            },
        }

    Note:
        is_in_scope 初始恒为 "unknown", 不硬编码任何子项目的 In-Scope /
        Out-of-Scope 状态, 完全交由 outline_refiner LLM 基于 AGENTS.md 声明判断.
    """
    # 失败降级: 路径无效时返回空 Scope, 不阻断主流程
    repo = Path(repo_path)
    if not repo.is_dir():
        logger.warning(
            "v8-P0-E: 仓库路径无效或不存在: %s, 返回空 Scope",
            repo_path,
        )
        return _empty_scopes(repo)

    try:
        scopes = _scan_scopes(repo)
        root_build_files = _scan_root_build_files(repo)
    except Exception as exc:  # noqa: BLE001
        # 失败降级: 扫描异常不阻断主流程, 仅告警
        logger.warning(
            "v8-P0-E: Scope 扫描异常, 返回空 Scope: %s",
            exc,
        )
        return _empty_scopes(repo)

    # is_monorepo 判定:
    # (子项目数 > 0 且 根目录无构建文件) OR (子项目数 > 1)
    # 设计理由: 根目录无构建文件 + 存在子项目 → 子项目即业务主体;
    # 多个子项目 → 多业务模块共存, 无论根目录是否有 workspace 构建文件
    is_monorepo = (len(scopes) > 0 and not root_build_files) or (len(scopes) > 1)

    result: dict[str, Any] = {
        "is_monorepo": is_monorepo,
        "scopes": scopes,
        "root_scope": {
            "name": repo.name,
            "path": ".",
            "build_files": root_build_files,
        },
    }
    logger.info(
        "v8-P0-E: Scope 识别完成: is_monorepo=%s, scopes=%d (%s)",
        is_monorepo,
        len(scopes),
        [s["name"] for s in scopes],
    )
    return result


def _scan_root_build_files(repo: Path) -> list[str]:
    """扫描根目录构建文件 (主项目).

    设计理由: 根目录构建文件代表主项目, 若存在则根目录本身即业务主体,
    子项目可能仅为辅助模块 (非 monorepo 主力).
    """
    build_files: list[str] = []
    for pattern in _BUILD_FILE_PATTERNS:
        for p in repo.glob(pattern):
            if p.is_file():
                build_files.append(p.name)
    return build_files


def _scan_scopes(repo: Path) -> list[dict[str, Any]]:
    """扫描一级子目录构建文件, 识别子项目.

    设计理由: 仅扫描一级子目录 (非深度递归), 与 nx/turborepo 的 workspace
    根级项目探测一致; 深层嵌套项目由各自构建文件在所属层级管理.
    """
    scopes: list[dict[str, Any]] = []
    for sub in sorted(repo.iterdir()):
        if not sub.is_dir():
            continue
        if sub.name.startswith(".") or sub.name in _EXCLUDED_DIRS:
            continue
        sub_build_files = _scan_subdir_build_files(sub)
        if not sub_build_files:
            continue
        # 取第一个构建文件推断语言 (一个子项目通常只有一种主构建文件)
        build_file_name = sub_build_files[0]
        language = _detect_language(build_file_name)
        has_agents_md = (sub / "AGENTS.md").exists()
        has_readme = (sub / "README.md").exists()
        scopes.append({
            "name": sub.name,
            "path": f"{sub.name}/",
            "build_file": f"{sub.name}/{build_file_name}",
            "language": language,
            "has_agents_md": has_agents_md,
            "has_readme": has_readme,
            "is_in_scope": "unknown",  # 由 outline_refiner LLM 判断
        })
    # v10-P0-4: 启发式 scope 决策 (不依赖 LLM, 从仓库结构信号推断)
    scopes = _heuristic_scope_decision(repo, scopes)
    return scopes


def _score_subproject(repo: Path, scope: dict[str, Any]) -> tuple[float, str]:
    """v11-P0-3: 多信号加权评分, 识别真正的主项目.

    借鉴 Aider repomap.py:293 personalization 向量: 主入口文件 ×50, 测试文件 ×0.1.
    多信号加权可解决 v10 单信号 (主入口存在性) 在多主项目仓库 (如 API + Admin 都含主入口) 中的误判.

    信号权重 (借鉴 Aider personalization ×50/×10/×0.1):
    - Controller 文件数 (×10): API 项目核心信号, 直接反映接口规模
    - 代码量 (代码文件总大小): 主项目代码量通常远大于辅助项目
    - 文档完整性 (README/AGENTS.md 各 +5): 主项目通常有完整文档
    - 测试目录存在 (+10): 主项目通常含测试目录
    - 配置文件数 (+3 每个): 主项目配置更完整
    - Django Admin 强惩罚 (-50): Django Admin 后台通常不是文档主项目

    Returns:
        (score, reason_str)
    """
    score = 0.0
    reasons: list[str] = []

    name = scope.get("name", "").lower()
    sub_dir = repo / scope.get("path", "").rstrip("/") if scope.get("path") else repo

    # 信号 1: Controller 文件数 (API 项目核心信号, ×10)
    controller_count = 0
    for pattern in ("**/*Controller.cs", "**/controllers/**/*.py", "**/routes/**/*.ts"):
        try:
            controller_count += sum(1 for _ in sub_dir.glob(pattern))
        except Exception:  # noqa: BLE001
            pass
    score += controller_count * 10.0
    if controller_count > 0:
        reasons.append(f"Controller×{controller_count}")

    # 信号 2: 代码量 (主项目代码量通常 >100KB)
    try:
        total_size = 0
        for f in sub_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".cs", ".py", ".ts", ".tsx", ".js", ".java", ".go"):
                continue
            fstr = str(f)
            if "node_modules" in fstr or "venv" in fstr or "__pycache__" in fstr:
                continue
            try:
                total_size += f.stat().st_size
            except OSError:
                pass
        if total_size > 100_000:
            score += 30.0
            reasons.append(f"代码量{total_size // 1024}KB")
        elif total_size > 50_000:
            score += 15.0
            reasons.append(f"代码量{total_size // 1024}KB")
    except Exception:  # noqa: BLE001
        pass

    # 信号 3: 文档完整性 (README + AGENTS.md, 各 +5)
    if (sub_dir / "README.md").exists():
        score += 5.0
        reasons.append("README")
    if (sub_dir / "AGENTS.md").exists():
        score += 5.0
        reasons.append("AGENTS.md")

    # 信号 4: 测试目录 (主项目通常有 tests/ 目录, +10)
    for test_dir in ("tests", "test", "__tests__"):
        if (sub_dir / test_dir).is_dir():
            score += 10.0
            reasons.append(test_dir)
            break

    # 信号 5: 配置文件 (主项目有完整配置, 每个 +3)
    cfg_count = 0
    for cfg in (
        "appsettings.json", "appsettings.Development.json", "application.yml",
        "pyproject.toml", "package.json", "go.mod", "Cargo.toml", "pom.xml",
    ):
        if (sub_dir / cfg).exists():
            score += 3.0
            cfg_count += 1
    if cfg_count > 0:
        reasons.append(f"配置×{cfg_count}")

    # 惩罚信号: Admin/Django 后台 (含 admin.py + models.py + Django settings)
    is_django_admin = (
        (sub_dir / "admin.py").exists()
        and (sub_dir / "models.py").exists()
        and any((sub_dir / f).exists() for f in ("settings.py", "apps.py"))
    )
    if is_django_admin:
        score -= 50.0  # 强惩罚
        reasons.append("Django-Admin(惩罚-50)")

    # 惩罚信号: 辅助子项目名称
    if name in _AUXILIARY_SCOPE_NAMES:
        score -= 20.0
        reasons.append(f"辅助名称({name},-20)")

    return score, ", ".join(reasons)


def _heuristic_scope_decision(repo: Path, scopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """v11-P0-3: 多信号加权 scope 决策 (替代 v10 单信号版本).

    借鉴 Aider repomap.py:293 get_ranked_tags 的 personalization 向量设计:
    多信号加权评分, 取最高分得主为主项目, 其他按相对得分判断.

    决策规则:
    1. 计算每个子项目的综合得分
    2. 得分最高的标记为 In-Scope (主项目)
    3. 其他子项目按相对得分判断:
       - 得分 < 主项目 30% → Out-of-Scope (辅助项目)
       - 得分 ≥ 主项目 30% → 保留 unknown (交 LLM 判断)

    降级: 若所有子项目得分 ≤0 (无法识别主项目), 回退到 v10 单信号决策.
    """
    if not scopes:
        return scopes

    # v11 多信号加权评分
    scored: list[tuple[dict[str, Any], float, str]] = []
    for scope in scopes:
        score, reason = _score_subproject(repo, scope)
        scored.append((scope, score, reason))

    # 按得分降序排序
    scored.sort(key=lambda x: x[1], reverse=True)

    if not scored:
        return scopes

    top_score = scored[0][1]

    # 降级: 若最高分 ≤0, 回退到 v10 单信号决策 (避免误判)
    if top_score <= 0:
        logger.warning(
            "v11-P0-3: 多信号加权最高分 ≤0 (top_score=%.1f), 回退到 v10 单信号决策",
            top_score,
        )
        return _heuristic_scope_decision_v10_fallback(repo, scopes)

    # v11 决策
    result: list[dict[str, Any]] = []
    for scope, score, reason in scored:
        new_scope = dict(scope)  # 副本, 不修改原 dict
        new_scope["scope_score"] = score
        if score == top_score:
            new_scope["is_in_scope"] = "true"
            new_scope["scope_reason"] = f"v11 主项目(得分 {score:.1f}): {reason}"
        elif score < top_score * 0.3:
            new_scope["is_in_scope"] = "false"
            new_scope["scope_reason"] = (
                f"v11 辅助项目(得分 {score:.1f} < 主项目 30% × {top_score:.1f}): {reason}"
            )
        else:
            new_scope["is_in_scope"] = "unknown"
            new_scope["scope_reason"] = f"v11 待定(得分 {score:.1f}): {reason}"
        result.append(new_scope)

    # 统计日志
    in_scope_count = sum(1 for s in result if s.get("is_in_scope") == "true")
    out_scope_count = sum(1 for s in result if s.get("is_in_scope") == "false")
    unknown_count = sum(1 for s in result if s.get("is_in_scope") == "unknown")
    logger.info(
        "v11-P0-3: 多信号加权 scope 决策完成: in_scope=%d, out_scope=%d, unknown=%d (总=%d, top_score=%.1f)",
        in_scope_count,
        out_scope_count,
        unknown_count,
        len(result),
        top_score,
    )
    return result


def _heuristic_scope_decision_v10_fallback(repo: Path, scopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """v10 启发式 scope 决策 (作为 v11 的降级 fallback).

    当 v11 多信号加权无法决策时 (所有得分 ≤0), 使用 v10 单信号决策.
    保留 v10 原始逻辑以兼容旧仓库.
    """
    for scope in scopes:
        name = scope.get("name", "").lower()
        path = scope.get("path", "")
        sub_dir = repo / path.rstrip("/") if path else repo

        has_main_entry = any((sub_dir / entry).exists() for entry in _MAIN_ENTRY_HINTS)

        has_api_build = False
        try:
            for pattern in _API_BUILD_FILES:
                for p in sub_dir.glob(pattern):
                    if "test" not in p.stem.lower():
                        has_api_build = True
                        break
        except Exception:  # noqa: BLE001
            pass

        is_admin_like = (
            (sub_dir / "admin.py").exists()
            or (sub_dir / "apps.py").exists() and (sub_dir / "settings.py").exists()
            or name in ("admin", "admins", "backend", "backoffice")
        )

        is_auxiliary = name in _AUXILIARY_SCOPE_NAMES

        if has_main_entry or has_api_build:
            scope["is_in_scope"] = "true"
            scope["scope_reason"] = (
                f"v10 fallback: 含主入口/API 构建文件 "
                f"({'主入口' if has_main_entry else 'API构建文件'})"
            )
        elif is_admin_like:
            scope["is_in_scope"] = "false"
            scope["scope_reason"] = "v10 fallback: Django Admin 后台辅助项目"
        elif is_auxiliary:
            scope["is_in_scope"] = "false"
            scope["scope_reason"] = f"v10 fallback: 辅助子项目 ({name})"
        else:
            scope["is_in_scope"] = "unknown"
            scope["scope_reason"] = "v10 fallback: 无法判定, 交 LLM"

    return scopes


def _scan_subdir_build_files(sub: Path) -> list[str]:
    """扫描单个子目录的构建文件名."""
    found: list[str] = []
    for pattern in _BUILD_FILE_PATTERNS:
        for p in sub.glob(pattern):
            if p.is_file():
                found.append(p.name)
    return found


def _empty_scopes(repo: Path) -> dict[str, Any]:
    """构造空 Scope 结构 (失败降级返回值).

    设计理由: 主流程不依赖 Scope 信息即可继续 (退化为单项目处理),
    仅丢失 monorepo 边界识别能力, 不阻断文档生成.
    """
    return {
        "is_monorepo": False,
        "scopes": [],
        "root_scope": {
            "name": repo.name,
            "path": ".",
            "build_files": [],
        },
    }


def _detect_language(build_file_name: str) -> str:
    """根据构建文件名推断编程语言.

    设计理由: 构建文件名是语言生态的强信号 (如 .csproj 仅 C# 使用),
    比文件扩展名扫描更精准且开销更低.

    Args:
        build_file_name: 构建文件名 (如 "API.csproj" / "package.json")

    Returns:
        语言标识: csharp / python / node / go / rust / java / unknown
    """
    if build_file_name.endswith(".csproj"):
        return "csharp"
    if build_file_name == "package.json":
        return "node"
    if build_file_name in ("pyproject.toml", "manage.py"):
        return "python"
    if build_file_name == "go.mod":
        return "go"
    if build_file_name == "Cargo.toml":
        return "rust"
    if build_file_name in ("pom.xml", "build.gradle"):
        return "java"
    return "unknown"


def format_scopes_for_prompt(scopes: dict[str, Any]) -> str:
    """格式化 Scope 信息为 prompt 注入文本.

    展示 monorepo 状态 / 所有子项目清单 / 强制约束, 供 outline_refiner 判断
    In-Scope / Out-of-Scope. 借鉴 AGENTS.md 项目级声明约定, 让 LLM 基于子项目
    AGENTS.md 是否存在 + 是否声明独立产品 来判断边界.

    Args:
        scopes: detect_scopes() 返回的 Scope 字典

    Returns:
        格式化文本, 注入 outline_refine prompt
    """
    if not scopes or not scopes.get("scopes"):
        return "(单项目仓库, 无子项目)"

    lines: list[str] = [
        "# 仓库 Scope 识别 (v8-P0-E, monorepo 子项目边界)",
        f"monorepo: {scopes.get('is_monorepo', False)}",
        "",
        "子项目清单:",
    ]
    for scope in scopes.get("scopes", []):
        agents_md = "有 AGENTS.md" if scope.get("has_agents_md") else "无 AGENTS.md"
        readme = "有 README" if scope.get("has_readme") else "无 README"
        lines.append(
            f"- {scope['name']} ({scope['path']}): "
            f"语言={scope['language']}, "
            f"构建文件={scope['build_file']}, "
            f"{agents_md}, {readme}"
        )
    lines.extend([
        "",
        "# Scope 判断规则:",
        "- 子项目 is_in_scope 初始为 unknown, 你需基于以下信息判断 In-Scope / Out-of-Scope",
        "- 若子项目有独立 AGENTS.md 且声明为独立产品, 标记为 Out-of-Scope, 仅作为外部依赖简述",
        "- 若子项目是 SDK / 工具库, 可在附录简述, 不作为主功能需求来源",
        "- 必须仅描述 In-Scope 子项目, 禁止为 Out-of-Scope 子项目新增章节",
    ])
    return "\n".join(lines)
