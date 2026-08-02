## 变更描述

<!-- 简述本 PR 做了什么, 为什么 -->

## 变更类型

- [ ] feat (新功能)
- [ ] fix (Bug 修复)
- [ ] docs (文档)
- [ ] refactor (重构)
- [ ] perf (性能)
- [ ] test (测试)
- [ ] chore (构建/工具)

## 质量门禁自查

- [ ] 单元测试通过 (`pytest tests/unit/ -q`)
- [ ] `ruff check .` 通过
- [ ] `ruff format --check .` 通过
- [ ] `mypy src/ --strict` 通过
- [ ] 新功能有对应单元测试
- [ ] 文档已更新 (如涉及)

## 架构边界自查

- [ ] 依赖方向单向向内 (`common/` 不依赖 `agents/` 或业务模块)
- [ ] `tools/`/`rag/`/`llm/`/`memory/` 未互相 import
- [ ] 未引入“不推荐清单”中的方案 (如已引入, 已说明优势理由)
- [ ] LangGraph 图结构/State schema 变更已与维护者确认
- [ ] 未在本仓库新增前端工程或测试页 (UI 归属 agentinsight-demo)
- [ ] 未暴露 `/v1/feedback`、`/v1/ws`、`/v1/mcp/configs`
- [ ] 临时文件已放入 `temp/`

## 安全合规自查

- [ ] 无硬编码密钥/密码
- [ ] 无 `eval`/`exec` 求值用户输入
- [ ] 无 `.env` 入仓
- [ ] Git 凭据走 AES-GCM; 仓库内容未写入日志 / trace input
- [ ] JWT token 未写入日志

## 关联 Issue

Closes #<issue-number>

## 备注

<!-- 截图 / 测试结果 / 偏差说明 -->
