"""agentinsight-docbot 测试套件根包.

测试分层 (见 AGENTS.md 第 13 章):
- unit/         单元测试 (构建期, 不依赖外部服务)
- smoke/        冒烟测试 (基础导入 + 创建检查)
- functional/   功能测试 (部署后容器栈)
- api/          API 测试 (OpenAI 兼容端点)
- regression/   回归测试 (合并 main 前门禁)
- e2e/          端到端测试 (完整链路)
- exploratory/  探索性测试 (边界/降级场景)
- security/     安全测试
- performance/  性能测试 (延迟/吞吐/负载)
- integration/  集成测试
"""
