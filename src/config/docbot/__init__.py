"""docbot 专属配置：8 种文档 persona + 大纲加载器 + 提示词模板。"""
from src.config.docbot.outlines import load_outline, parse_markdown_outline
from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS, get_persona

__all__ = ["DOCBOT_REPORT_PERSONAS", "get_persona", "load_outline", "parse_markdown_outline"]
