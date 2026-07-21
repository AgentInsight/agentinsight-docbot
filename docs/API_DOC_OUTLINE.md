---
report_type: api_doc
name_zh: API 文档
name_en: API Document
default_chapters: 12
max_chapters: 20
---

# API 文档 生成大纲

## 角色定位
你是一名 API 设计工程师，基于系统接口规范，生成结构完整、可直接驱动 SDK 与客户端集成的 API 文档。

## 目标读者
- 前端/移动端开发者：关注接口详情、请求响应示例、SDK
- 第三方开发者/集成商：关注认证授权、错误处理、Webhook
- 后端工程师：关注接口契约、数据模型、版本治理

## 章节结构

### 第1章 引言
**目的**：阐明编写目的、适用范围与参考文档。
**要点**：
- 编写目的（面向前端/移动端/第三方开发者/集成商）
- 适用范围（API 版本 v1.0、协议 HTTP/HTTPS、数据格式 JSON、风格 RESTful）
- 术语与缩略语（API、JWT、OAuth2、RBAC）
- 参考文档（系统架构文档、概要设计文档、OpenAPI 规范）
- 版本历史

### 第2章 API 概览
**目的**：提供基础信息、API 分类与清单。
**要点**：
- 基础信息（Base URL、协议 HTTPS、数据格式 JSON UTF-8、时区 UTC、时间格式 ISO 8601）
- API 分类（用户管理 /users、订单管理 /orders、商品管理 /products、认证 /auth、文件 /files 等）
- API 清单（编号 API-NNN/方法/路径/描述/鉴权）
- 通用响应结构（code/message/data/traceId/timestamp）
- OpenAPI 规范（推荐自动生成，规范文件、Swagger UI、Postman Collection 链接）
**示例/模板**：
```json
{
  "code": 0,
  "message": "success",
  "data": { },
  "traceId": "abc-123",
  "timestamp": "2026-07-20T10:00:00Z"
}
```

### 第3章 认证与授权
**目的**：定义认证方式、OAuth2 流程、Token 规范与权限矩阵。
**要点**：
- 认证方式（OAuth2 用户登录、API Key 服务端调用、JWT 会话保持、mTLS 服务间调用）
- OAuth2 流程（获取授权码 → 换 token → 携带 token 访问 → refresh_token 续期）
- Token 规范（类型 Bearer、长度、有效期 access 2h/refresh 30d、存储、撤销 /auth/revoke）
- 授权模型（RBAC 角色→权限、ABAC 属性→权限、资源所有者校验策略）
- 权限矩阵（角色 admin/user、资源 users、操作 CRUD/R(自己)）

### 第4章 通用约定
**目的**：统一命名、HTTP 方法语义、版本、分页、过滤与幂等性。
**要点**：
- 命名规范（路径复数名词 kebab-case `/users` `/order-items`、字段 camelCase `userId`、枚举 UPPER_SNAKE、时间 ISO 8601）
- HTTP 方法语义（GET 查询幂等安全、POST 创建、PUT 全量更新幂等、PATCH 部分更新、DELETE 删除幂等）
- 版本策略（URI 版本 `/v1/users`、兼容期 6 个月、弃用 Header `Deprecation`）
- 分页规范（cursor-based 默认 / offset，参数 cursor/limit 默认 20 最大 100，响应 items+nextCursor）
- 过滤与排序（`?status=active`、`?sort=-createdAt,lastName`、`?fields=id,name`）
- 幂等性（创建类接口支持 `Idempotency-Key` Header、重复请求返回首次结果、Key 保留 48h）
- 国际化（`Accept-Language: zh-CN`、`X-Timezone: Asia/Shanghai`、`X-Currency: CNY`）
- 请求头/响应头约定（Authorization、Content-Type、X-Request-Id、Idempotency-Key、X-RateLimit-*）

### 第5章 错误处理
**目的**：定义错误响应结构、HTTP 状态码与业务错误码。
**要点**：
- 错误响应结构（code/message/details/traceId/timestamp）
- HTTP 状态码（200/201/202/204/400/401/403/404/409/422/429/500/502/503/504 使用场景）
- 业务错误码分段（40000-40999 用户模块、41000-41999 订单模块、42000-42999 商品模块）
- 错误码清单（ERR_40001 参数缺失、ERR_40101 token 无效、ERR_40102 token 过期、ERR_40301 权限不足、ERR_40401 资源不存在、ERR_40901 资源已存在、ERR_42201 业务校验失败、ERR_42901 限流、ERR_50001 服务器错误）
- 错误重试建议（4xx 不重试除 429、5xx 指数退避、429 按 `Retry-After`）
**示例/模板**：
```json
{
  "code": 40001,
  "message": "参数缺失：user_id",
  "details": [{ "field": "user_id", "issue": "required" }],
  "traceId": "abc-123",
  "timestamp": "2026-07-20T10:00:00Z"
}
```

### 第6章 限流与配额
**目的**：定义限流策略、配额管理与豁免规则。
**要点**：
- 限流策略（RATE-001 全局 10000 QPS、RATE-002 单 IP 100 QPS、RATE-003 单用户 60 QPS、RATE-004 单接口 500 QPS）
- 配额管理（文件上传 10GB/月、API 调用 100 万次/月，超限拒绝+升级提示）
- 限流响应头（X-RateLimit-Limit/Remaining/Reset、Retry-After）
- 限流豁免（内部服务调用、监控探针、白名单 IP）

### 第7章 API 详情
**目的**：按统一模板详述每个接口的请求、响应、错误码与示例。
**要点**：
- API 详情模板（方法/路径/描述/鉴权/限流；Headers；路径参数；查询参数；请求体+字段说明；响应+字段说明；错误码；cURL/Python/JavaScript 示例）
- 认证模块（POST /auth/login、POST /auth/logout、POST /auth/refresh）
- 用户模块（GET /users、GET /users/{id}、POST /users、PUT /users/{id}、DELETE /users/{id}）
- 订单模块、商品模块、文件模块（POST /files/upload multipart/form-data 单文件≤100MB）
**示例/模板**：
```markdown
### API-NNN <接口名>
- **方法**：POST
- **路径**：/v1/orders
- **鉴权**：Bearer Token
#### 请求体
```json
{ "productId": "string", "quantity": 0 }
```
#### 请求体字段说明
| 字段 | 类型 | 必填 | 校验 | 说明 |
|------|------|------|------|------|
| productId | string | 是 | UUID | 商品 ID |
| quantity | int | 是 | ≥1 | 数量 |
#### 201 Created 响应
```json
{ "code": 0, "data": { "orderId": "string", "status": "PENDING" } }
```
#### cURL 示例
```bash
curl -X POST https://api.<domain>.com/v1/orders \
  -H "Authorization: Bearer <token>" \
  -d '{"productId":"prod-001","quantity":2}'
```
```

### 第8章 数据模型
**目的**：定义实体清单、字段类型规范、枚举值与公共字段。
**要点**：
- 实体清单（User/Order/Product 等，含描述与关键字段）
- 字段类型规范（string/int/float/boolean/timestamp ISO 8601/uuid/enum UPPER_SNAKE/object/array）
- 枚举值（订单状态 PENDING/PAID/SHIPPED/COMPLETED/CANCELLED，用户状态等）
- 公共字段（id uuid、createdAt、updatedAt、createdBy、updatedBy、version 乐观锁）

### 第9章 Webhook 与回调
**目的**：定义事件、注册、签名验证与重试策略。
**要点**：
- Webhook 事件（order.created、order.paid、order.shipped，含触发与载荷）
- Webhook 注册（POST /v1/webhooks，url + events 列表）
- 回调签名（HMAC-SHA256，Header `X-Signature: <hex>`，用 secret 校验）
- 重试策略（失败重试 3 次，指数退避 1s/2s/4s，死信处理）
- 回调示例（POST 请求，含 event/data/timestamp）

### 第10章 SDK 与示例
**目的**：提供官方 SDK、使用示例与 Playground。
**要点**：
- 官方 SDK（Python/JavaScript/Java/Go 仓库、版本、文档链接）
- SDK 使用示例（Python `client.orders.create(...)`、JavaScript `await client.orders.create(...)`）
- Postman/Insomnia（Collection、Environment、用法）
- cURL 示例库（常用接口示例集）
- Playground（在线试调、沙盒环境、测试 Key `sk_test_xxx`）

### 第11章 版本治理与弃用
**目的**：定义版本策略、变更分类与弃用流程。
**要点**：
- 版本策略（URI 版本 /v1/ /v2/、兼容期 6 个月、弃用通知 Header+邮件+文档）
- 变更分类（Patch 兼容加可选字段/修 bug、Minor 兼容加新接口/枚举值、Major 不兼容改字段类型/删字段/改语义）
- 弃用流程（标记弃用 → 通知用户 → 提供迁移指南 → 6 个月后下线）
- 变更日志（版本/日期/变更类型/内容）
- 迁移指南（版本间字段映射，如 v1 → v2）

### 第12章 附录
**目的**：提供完整错误码表、字段规范、FAQ 与最佳实践。
**要点**：
- 完整错误码表（与 §5.4 同步）
- 字段命名规范（路径 kebab-case、字段 camelCase、枚举 UPPER_SNAKE、时间 ISO 8601）
- 常见问题 FAQ（如何获取 token、token 过期、排查 429、处理 5xx）
- 最佳实践（使用 SDK、token 自动续期、幂等键机制、指数退避重试、关注 deprecation 通知）
- 参考资料（OpenAPI 3.0 规范、RESTful API Design Google、Stripe API Style Guide、Microsoft REST API Guidelines）
- 联系与支持（技术支持邮箱、工单系统、开发者社区、状态页）

## 写作规范
- 编号约定：API-NNN（接口）、ERR-NNNN（错误码）、RATE-NNN（限流规则）
- 所有接口必须按 §7.1 模板编写，便于自动化解析与 SDK 生成
- 推荐维护 OpenAPI 规范文件，自动生成接口详情
- 错误码按模块分段，编号不可重复
- 每个接口必须提供 cURL 示例和至少一种语言 SDK 示例
- 字段命名严格遵循 §4.1 命名规范

## 输出格式
- 默认语言：简体中文
- 默认格式：Markdown
- 章节编号：1, 1.1, 1.1.1
- 代码块：JSON/YAML/cURL/Python/JavaScript 标注语言类型
- 表格：使用 Markdown 表格
- 推荐配合：OpenAPI/Swagger UI 自动生成接口详情
- 转 Word：`pandoc 本文件 -o 输出.docx --toc --toc-depth=3`
