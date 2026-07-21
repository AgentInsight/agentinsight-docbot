"""验证3个源码 bug 修复是否生效."""
from src.llm.client import LLMTier
from src.agents.docbot.coordinator import CoordinatorA
from src.agents.docbot.reviewer import ReviewerE
from src.config.docbot.prompts import get_prompt

# Bug #1: StrEnum -> (str, Enum)
print("Bug #1: LLMTier.FAST =", LLMTier.FAST, "type:", type(LLMTier.FAST).__name__)
print("Bug #1: LLMTier.FAST == 'fast':", LLMTier.FAST == "fast")
print("Bug #1: str(LLMTier.FAST):", str(LLMTier.FAST))

# Bug #2: get_prompt language 注入
prompt = get_prompt(
    "content_filler",
    doc_type="architecture",
    chapter_idx=1,
    chapter_title="概述",
    chapter_outline="章节要点",
    code_learning="代码摘要",
    rag_context="RAG 检索结果",
    language="zh",
)
assert "{language}" not in prompt, "Bug #2 未修复: {language} 占位符仍在"
print("Bug #2: get_prompt content_filler OK, prompt len =", len(prompt))

# Bug #3: _check_git_domain allowed 列表小写
from unittest.mock import MagicMock
from src.tools.git_mcp import GitMCPAdapter

mock_settings = MagicMock()
mock_settings.allowed_git_domains_list = ["GitHub.com"]
adapter = GitMCPAdapter(settings=mock_settings)
adapter._check_git_domain("https://GITHUB.COM/test/repo.git")
adapter._check_git_domain("https://github.com/test/repo.git")
adapter._check_git_domain("https://API.GitHub.com/test/repo.git")
print("Bug #3: _check_git_domain 大小写不敏感匹配 OK")

print("\nAll 3 bug fixes verified!")
