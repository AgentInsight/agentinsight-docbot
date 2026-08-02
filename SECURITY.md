# 安全策略 | Security Policy

[中文](#中文) | [English](#english)

---

## 中文

## 报告漏洞

如果您发现安全漏洞, 请**不要**通过公开 Issue 报告。
请通过以下渠道私下报告:

- 邮箱: agentinsightcn@gmail.com
- GitHub Security Advisory (推荐): 使用仓库 "Security" 标签页的 "Report a vulnerability" 功能

## 响应 SLA

- 确认收到: 48 小时内
- 初步评估: 5 个工作日内
- 修复发布: 严重漏洞 30 天内, 一般漏洞 90 天内

## 支持版本

仅对最新发布版本 (latest release) 提供安全更新。

## 安全合规红线

本项目遵循严格的安全合规要求:

### 密钥管理
- 密钥仅通过环境变量注入, 禁止入仓/硬编码/日志
- Git 凭据使用 AES-GCM 加密存储, 密钥 `GIT_CREDENTIAL_KEY` 仅环境变量注入
- API Key 使用 SHA256 + BCrypt 双哈希存储(如适用)
- 发现硬编码密钥即 P0 暂停并人工介入

### PII 与仓库内容保护
- 用户会话内容加密存储
- 用户代码仓库内容不外泄(不写入日志、不入 `trace_generation` 的 input)
- 日志自动脱敏; API 响应禁止返回密码/密钥/Token 原文
- 最小化收集, 按用途设保留期

### Prompt Injection 防护
- 所有外部输入(含用户输入/RAG 检索结果/工具返回/代码仓库内容)经 Pydantic 校验
- 工具调用权限隔离 (read/write/execute/network 显式授权)
- 禁止 eval/exec 求值用户输入
- LLM 输出经结构化校验后再入工具
- 代码仓库 URL 白名单 (`ALLOWED_GIT_DOMAINS`)

### 传输与边界
- 生产环境强制 HTTPS
- 安全响应头中间件 (nosniff/DENY/HSTS) 不可绕过
- 生产环境关闭 Debug
- CORS 不推荐使用 * (生产环境应配置具体域名列表)

## 报告内容建议

为帮助我们快速处理, 请在报告中包含:
1. 漏洞描述与影响范围
2. 复现步骤 (最小化 PoC)
3. 影响版本 (git commit hash)
4. 建议的修复方案 (如有)
5. 您的联系方式 (用于跟进)

## 贡献者激励

对于确认的有效安全漏洞报告, 我们将在致谢列表中感谢报告者 (除非报告者希望保持匿名)。

---

## English

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** report it via public Issues.
Report it privately via:

- Email: agentinsightcn@gmail.com
- GitHub Security Advisory (recommended): Use the "Report a vulnerability" feature in the repository "Security" tab

## Response SLA

- Acknowledgment: within 48 hours
- Initial assessment: within 5 business days
- Fix release: 30 days for critical vulnerabilities, 90 days for general vulnerabilities

## Supported Versions

Only the latest release receives security updates.

## Security Compliance

This project follows strict security compliance requirements:

### Key Management
- Keys are injected via environment variables only; never committed/hardcoded/logged
- Git credentials are encrypted with AES-GCM; `GIT_CREDENTIAL_KEY` is env-injected only
- Hardcoded keys trigger immediate P0 suspension and manual intervention

### PII & Repository Content Protection
- User session content is encrypted at rest
- User repository contents must not leak into logs or `trace_generation` inputs
- Logs are redacted; API responses never return raw secrets

### Prompt Injection Defense
- All external inputs (including repository content) are validated via Pydantic
- Tool permissions are explicitly scoped (`read`/`write`/`execute`/`network`)
- `eval`/`exec` on user input is forbidden
- Repository URL allowlist via `ALLOWED_GIT_DOMAINS`

### Transport & Boundaries
- HTTPS is mandatory in production
- Security headers middleware (nosniff/DENY/HSTS) cannot be bypassed
- Debug mode is disabled in production
- CORS `*` is not recommended for production

## What to Include in a Report

1. Description and impact scope
2. Reproduction steps (minimal PoC)
3. Affected version (git commit hash)
4. Suggested fix (optional)
5. Your contact information

## Recognition

Valid security reports will be acknowledged in our credits list (unless the reporter prefers anonymity).
