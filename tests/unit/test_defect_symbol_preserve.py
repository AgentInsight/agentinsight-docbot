"""defect 文档编号 DEF-* 不应被 SymbolValidator / strip 误删."""

from __future__ import annotations

from src.agents.docbot.content_filler import ContentFillerD
from src.agents.docbot.symbol_validator import _is_doc_id_or_abbrev


def test_def_ids_are_doc_ids() -> None:
    assert _is_doc_id_or_abbrev("DEF-001")
    assert _is_doc_id_or_abbrev("DEF001")
    assert _is_doc_id_or_abbrev("DEF")
    assert _is_doc_id_or_abbrev("BUG-002")
    assert _is_doc_id_or_abbrev("CWE-89")


def test_strip_preserves_def_prefix() -> None:
    content = "### DEF-001 吞异常 [严重度: High]\n- **类型**: exception\n"
    cleaned = ContentFillerD._strip_hallucinated_symbols(content, ["DEF", "High", "FooBarBaz"])
    assert "DEF-001" in cleaned
    assert "严重度: High" in cleaned
    assert "FooBarBaz" not in cleaned
