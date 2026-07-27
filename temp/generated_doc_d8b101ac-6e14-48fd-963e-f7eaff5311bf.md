## 系统概述

### 业务背景与目标

随着电商业务的快速增长，原有的单体订单处理系统在性能、可扩展性和维护性方面逐渐成为瓶颈。日均订单量从早期的 5 万笔激增至 150 万笔，双十一峰值请求量超过 2000 TPS，系统响应时间从 50ms 恶化至 2 秒以上，故障率逐月攀升。同时，业务方提出了拆分订单生命周期、支持多渠道（App、小程序、第三方平台）统一接入、以及实时库存扣减与多仓调拨等新需求。为此，公司决定启动新一代订单中台的建设。

**业务目标**  
1. **高可用与弹性伸缩**：支持峰值 5000 TPS 的平稳运行，通过容器化部署实现分钟级自动扩缩。  
2. **流程可配置化**：将订单处理流程（创建、支付、发货、退款等）拆解为可编排的工作流，业务方可通过配置平台自定义节点行为，减少研发重复投入。  
3. **数据一致性保障**：在分布式环境下保证最终一致性，特别是库存扣减、资金结算等关键账务环节，避免超卖和重复支付。  
4. **可观测性**：提供全链路的调用链路跟踪、业务指标监控和日志聚合，支撑快速故障定位和容量规划。

### 系统定位与核心价值

**系统定位**：作为公司电商技术栈中的核心业务中台，负责所有订单相关的领域逻辑、状态流转、事件发布及外部系统集成。它向下依赖商品、库存、用户、支付、物流等基础服务，向上为交易前台（B2C/B2B/跨境）提供统一、稳定的订单操作 API 和消息推送通道。

**核心价值**：
- **领域驱动设计（DDD）落地**：将订单拆分为“订单聚合”、“出库单”、“退款单”、“调拨单”等独立限界上下文，每个上下文拥有专属的仓储与领域服务，降低模块耦合。代码仓库中 `src/order/domain/aggregate/order_aggregate.py` 定义了订单聚合根，其内的 `OrderEntity` 类封装了订单状态转换规则，禁止直接修改内部状态（见第 78-102 行 `_transition_state` 私有方法）。
- **事件驱动架构**：通过 RabbitMQ 发布领域事件（如 `OrderCreatedEvent`、`PaymentReceivedEvent`），下游服务异步消费，实现削峰填谷和业务可扩展。事件定义集中于 `src/shared/event/order_events.py`，例如 `OrderShippedEvent` 包含 `shipment_id`、`carrier_code` 等字段。
- **标准化接口契约**：所有对外 API 遵循 RESTful 风格，并使用 OpenAPI 3.0 规范进行定义（`docs/openapi/order_api.yaml`），支持自动生成客户端 SDK 和 API 文档。
- **容错与降级**：引入断路器模式（Resilience4j）保护对下游库存服务的调用，当库存服务响应超时或失败率达到阈值时，订单创建接口返回预设的备选库存量，避免级联故障。

### 利益相关方矩阵

以下矩阵列出了系统的关键利益相关方及其关注点、影响力（高：决策性影响；中：重要输入；低：知情）和参与方式。数据来源包括项目启动会议纪要（`docs/project/stakeholder_analysis.md`）以及日常迭代中的需求评审记录。

| 角色                   | 关注点                                                                 | 影响力 | 参与方式                                   |
| ---------------------- | ---------------------------------------------------------------------- | ------ | ------------------------------------------ |
| 业务产品经理           | 订单流程灵活性、多渠道支持、报表数据准确性                             | 高     | 定期需求评审、UAT 验收、业务指标定义         |
| 交易前台开发团队       | API 稳定性、文档完整性、响应时间、错误码明确性                          | 高     | API 对接联调、日常 bug 反馈、性能压测       |
| 库存与商品服务团队     | 库存扣减原子性、超卖防护、补偿机制                                   | 中     | 接口协议协商、故障应急演练、数据对账         |
| 财务与结算团队         | 资金流水一致性、退款流程可追溯、日结对账文件格式                       | 中     | 对账报告自动化接收、异常订单标记处理         |
| 运维 SRE 团队          | 系统监控指标、告警阈值、日志查询效率、部署回滚成功率                  | 中     | 设置 Prometheus 规则、Grafana 看板、容器调度 |
| 测试质量保障团队       | 冒烟测试覆盖率、压力测试场景、边界条件、幂等性验证                     | 低     | 参与 CI 流水线、维护自动化测试用例、性能测试 |
| 安全合规团队           | 敏感数据加密、防篡改、审计日志、GDPR 合规                              | 中     | 代码安全扫描、渗透测试、数据脱敏方案审查     |

### 范围边界 In-Scope / Out-of-Scope

通过项目章程（`docs/project/charter.md`）和迭代 Backlog 归纳，本系统的范围边界定义如下：

#### In-Scope（范围内）
- 订单的创建、修改、取消、关闭、拆分、合并等核心生命周期管理。
- 订单状态机的集中定义与实时校验（状态表定义于 `src/order/domain/spec/order_state_machine.py`，使用有限状态机库 transitions 实现，共 9 个状态、15 条合法转换）。
- 基于领域事件的异步通知：发送至消息队列，供物流、营销、数据分析等下游消费。
- 对外统一 REST API（`src/order/interfaces/api/v1/order_controller.py` 路由定义）。
- 与库存服务的同步/异步扣减并发的乐观锁机制（`src/order/infrastructure/adapters/stock_adapter.py` 封装 `deduct_stock` 方法，携带版本号）。
- 与支付服务的对账与退款对接（`src/order/interfaces/adapters/payment_gateway.py`），含支付回调处理。
- 后台管理界面中的订单查询、详情展示、手工干预（如强制关单、补偿库存）。
- 多租户支持（通过 `X-Tenant-Id` 请求头隔离数据）。

#### Out-of-Scope（范围外）
- 具体的前端页面 UI 实现（仅提供管理后台 API，不包含 H5/小程序/PC 的前端渲染）。
- 商品详情页库存实时显示（由商品服务自身缓存解决）。
- 支付核心逻辑（仅对接支付网关，不做资金清结算）。
- 物流配送的实际运单管理（只生成出库指令到 WMS，不管理包裹轨迹）。
- 退款审批工作流（简化处理：系统自动审核一定金额以下的退款，超额的生成工单转人工，人工流程属于单独的人事系统）。
- 用户积分、优惠券等营销工具的计算（仅接收计算后的结果，不参与规则引擎）。

### 读者画像与阅读路径

本技术文档面向不同角色提供差异化的阅读路径。建议按角色优先阅读以下章节（章节编号为本文档内假设编号，最终以实际目录为准）：

| 读者角色                     | 推荐阅读章节                       | 阅读目的                                               |
| ---------------------------- | ---------------------------------- | ------------------------------------------------------ |
| **新增业务开发工程师**       | 架构概览 → 核心领域模型 → API 契约 → 工作流配置 | 理解系统宏观结构，快速上手开发新 API 和修改业务流程。    |
| **运维 / SRE**               | 部署架构 → 可观测性 → 容灾与弹性伸缩 → 告警规则 | 掌握系统部署拓扑、监控指标和故障恢复流程。              |
| **测试工程师**               | API 契约 → 测试策略 → 性能测试基线               | 基于 OpenAPI 生成集成测试，设计压测场景。                |
| **业务产品经理**             | 系统概述 → 业务功能列表 → 工作流配置 → 版本发布计划 | 了解系统边界，配置订单流程，跟踪版本更新。               |
| **安全审计人员**             | 安全与合规 → 数据加密与审计日志                       | 检查敏感数据处理方式、权限模型和日志审计完整性。         |

### 术语表

下表列出了本系统中使用的重要术语及其定义，在文档正文中首次出现时也会附带链接指引。

| 术语            | 英文名              | 定义                                                                                 |
|----------------|--------------------|--------------------------------------------------------------------------------------|
| 订单聚合根      | Order Aggregate    | 领域驱动设计中的聚合根，负责维护订单内所有实体（订单项、收件信息、支付记录）的一致性。 |
| 领域事件        | Domain Event       | 订单生命周期中发生的重要业务动作，如 `OrderCreated`，用于解耦下游处理。              |
| 补偿事务        | Compensating Transaction | 当分布式操作中部分调用失败时，反向调用已成功的服务以撤销之前的效果（如退还库存）。   |
| 工作流引擎      | Workflow Engine    | 基于 Temporal 的流程编排组件（初期选型），支持通过 JSON 定义节点顺序与决策规则。    |
| 明细分页        | Cursor Pagination  | 基于游标的分页方式，避免深度分页偏移量问题，用于订单列表接口。                        |
| 租户隔离        | Tenant Isolation   | 通过 `tenant_id` 字段实现多租户数据隔离，每个租户拥有独立的配置（如流程定义、库存池）。 |
| 幂等键          | Idempotency Key    | 客户端生成的唯一标识，确保同一请求被服务端最多处理一次，防止重复下单。                |
| SLA 降级        | SLA Degradation    | 当依赖服务故障时，自动切换至预设的降级策略（如从实时库存扣减改为预分配库存）。       |

> **说明**：部分术语在代码仓库中有直接映射。例如 `IdempotencyKey` 类定义于 `src/shared/utils/idempotency.py`，其 `validate` 方法检查 Redis 中是否已存在该 key（见第 34-48 行）。

## 架构原则与决策

### 架构原则

架构原则是系统设计的核心约束，它们直接来源于业务需求、技术战略和质量属性。以下原则通过项目代码仓库的实际结构、接口定义和模块划分得以体现。

| # | 原则 | 理由 | 含义 | 反例 |
|---|------|------|------|------|
| 1 | **领域驱动分层** | 将复杂业务逻辑与技术基础设施解耦，使核心领域保持纯净可测试。 | 代码组织按 `domain/` `application/` `infrastructure/` `interfaces/` 四层划分；领域层不引入任何框架注解或数据库连接（见 `src/domain/model/order.py`:1-10）。 | 在 `domain/` 下直接调用 SQLAlchemy Session（曾出现于旧版本 `src/domain/repository/order_repo.py` 第 45 行，后重构为接口隔离）。 |
| 2 | **命令查询职责分离（CQRS）** | 读操作与写操作频率、数据模型差异大，分离后可独立优化。 | 写入路径走 `CommandHandler`（如 `src/order/commands/create_order.py`:15-40），查询路径走 `QueryHandler`（如 `src/order/queries/get_order.py`:10-30）；二者使用不同的数据投影（读写模型分离）。 | 统一使用同一聚合根既返回数据又执行变更（过去在 `src/order/service.py` 第 80 行的 `place_order_and_return_summary` 曾违反此原则，后被拆分）。 |
| 3 | **事件溯源（可选）** | 需要完整审计日志与历史状态回溯，通过事件重建聚合状态。 | 聚合根状态通过事件流恢复（`src/domain/events/order_events.py`:5-20），事件存储于 `EventStore`（`src/infrastructure/event_store.py`:60-100）。 | 直接使用 `UPDATE` 覆盖数据库行导致丢失变更历史（历史遗留模块 `src/legacy/stock_adjust.py` 曾使用 `UPDATE`，现已被标记为待迁移）。 |
| 4 | **依赖倒置（DIP）** | 高层模块不应依赖低层实现，所有依赖指向抽象接口。 | 领域层定义 `Repository` 接口（`src/domain/repository/interfaces.py`:1-5），基础设施层实现具体仓储（`src/infrastructure/persistence/postgres_order_repo.py`:1-10）；业务代码 `src/application/usecases/place_order.py` 仅依赖接口。 | 业务服务直接实例化 `PostgresOrderRepository`（曾出现在 `src/application/usecases/place_order.py` 第 25 行，违反依赖倒置，后改为依赖注入）。 |
| 5 | **单一职责（SRP）** | 每个模块、类、方法只负责一个明确的职责。 | `src/domain/entity/product.py` 只封装产品属性（`name`, `price`），不包含持久化逻辑；`src/application/services/pricing.py` 只处理定价规则。 | `src/infrastructure/cache/redis_cache.py` 原混入了序列化与缓存失效两种职责（第 30-60 行），后拆分为 `serializer.py` 和 `cache_adapter.py`。 |

这些原则在架构评审中被持续验证。每次新增功能必须检查是否偏离以上原则；若必须偏离，则需记录为例外决策（见 ADR 索引表）。

### 设计准则

设计准则是将原则落实为可操作的具体规则，涵盖接口、一致性、失败处理三个维度。

#### 接口设计准则

- **契约式设计**：所有服务间接口必须有明确的输入输出契约，使用 Pydantic 模型作为请求/响应定义（如 `src/interfaces/api/schemas/order_schema.py`:10-30）。接口接受严格的类型校验，不允许隐式转换。
- **统一资源标识**：RESTful API 遵循资源命名规范，动词仅限 GET/POST/PUT/PATCH/DELETE。例如订单资源路径为 `/api/v1/orders/{order_id}`（定义在 `src/interfaces/api/routers/order_router.py`:5-15）。
- **版本化管理**：接口版本通过 URL 前缀 `v1`, `v2` 标识，或通过 `Accept` 头部协商。当前主版本为 `v1`，向后兼容策略记录在 ADR-003 中。

#### 一致性准则

- **命名风格**：Python 代码遵循 PEP 8，类名使用 PascalCase（`CreateOrderHandler`），函数/变量使用 snake_case（`get_order_by_id`），常量全大写（`MAX_RETRY_COUNT = 3`）。配置文件 `src/config.py` 第 10-30 行展示了环境变量命名规范。
- **错误响应格式**：所有 API 错误统一返回 `{"error": {"code": "ORDER_NOT_FOUND", "message": "订单不存在", "details": {}}}` 结构（见 `src/interfaces/api/error_handlers.py`:20-40）。内部异常通过 `ApplicationError` 基类捕获并转换为标准响应（`src/domain/exceptions.py`:1-10）。
- **日志格式**：生产环境使用 JSON 结构化日志，包含 `timestamp`, `level`, `service`, `trace_id`, `message` 字段（`src/infrastructure/logging/logger.py`:15-25）。调试环境可换回纯文本。

#### 失败处理准则

- **重试与退避**：对外部服务调用（如支付网关）采用指数退避重试，最大重试次数为 3（`src/infrastructure/payment/client.py`:50-70 中的 `retry_with_backoff` 函数）。
- **熔断机制**：当外部服务连续 5 次失败或超时达到阈值时，熔断器打开，后续请求直接快速失败（`src/infrastructure/circuit_breaker.py`:30-55）。熔断器状态通过健康检查端点暴露。
- **降级方案**：关键非核心功能（如推荐、个性化推送）在依赖不可用时优雅降级，返回空缓存或默认值。例如 `src/application/services/recommendation.py`:80-90 捕获 `ConnectionError` 后返回空列表。
- **幂等性**：写操作（创建订单、修改库存）必须支持幂等性，通过 `Idempotency-Key` 头部或操作本身天然幂等（如 `SET` 操作）。`src/application/middleware/idempotency.py`:5-20 实现了基于 Redis 的幂等键验证。

这些准则在代码评审清单中作为必检项（见 `docs/code_review_checklist.md` 第 12-25 行），所有合并请求必须通过自动 lint 校验规则 `src/.pylintrc` 配置。

### ADR 索引表

架构决策记录（Architecture Decision Records，ADR）用于捕获关键决策的上下文、选项和结论。以下索引表列出了项目中的重要决策。

| ADR 编号 | 标题 | 日期 | 状态 | 简要影响 |
|----------|------|------|------|----------|
| ADR-001 | 采用微服务架构，优先拆分订单、库存、支付三个服务 | 2024-01-15 | 已采纳 | 服务间通过异步消息（RabbitMQ）通信，事件总线定义在 `src/infrastructure/message_bus/`。 |
| ADR-002 | 选择 PostgreSQL 作为主数据库，Redis 作为缓存和事件溯源存储 | 2024-02-01 | 已采纳 | 聚合根持久化使用 PostgreSQL 序列化 JSONB（`src/infrastructure/persistence/postgres_order_repo.py`:40-50）；事件溯源表设计参考 `src/infrastructure/event_store.py`:70-80。 |
| ADR-003 | API 版本策略：URL 路径前缀版本控制（`/v1/`），v1 稳定期持续 6 个月 | 2024-03-10 | 已采纳 | 客户端无需携带版本头部，但需配合 `Deprecated` 头通知升级。 |
| ADR-004 | 全局唯一 ID 采用 ULID 而非 UUIDv4，提升排序性能 | 2024-04-20 | 已采纳 | 使用 `src/domain/value_objects/id.py` 中的 `ULIDGenerator` 类；数据库主键采用 ULID 的二进制排序。 |
| ADR-005 | 错误处理统一使用 `ApplicationError` 基类，禁止向外层抛出裸 `Exception` | 2024-05-05 | 已采纳 | 所有业务异常（`OrderNotFoundError`、`InsufficientStockError`）继承自 `ApplicationError`（`src/domain/exceptions.py`:15-25），由全局异常处理器统一转换。 |
| ADR-006 | 数据一致性采用最终一致性模式，跨服务事务通过 Saga 编排实现 | 2024-06-12 | 已采纳 | Saga 编排器位于 `src/application/sagas/create_order_saga.py`:5-35，使用步骤表驱动补偿动作。 |
| ADR-007 | 日志聚合使用 ELK 栈，每个服务输出 JSON 日志至标准输出 | 2024-07-01 | 已采纳 | 日志配置在 `src/infrastructure/logging/` 中，通过环境变量 `LOG_FORMAT=json` 控制。 |
| ADR-008 | 测试策略：单元测试覆盖领域逻辑，集成测试覆盖服务边界，契约测试覆盖 API 接口 | 2024-08-15 | 已采纳 | 测试目录 `tests/` 按 `unit/`、`integration/`、`contract/` 分层；契约使用 `pact-python`（`tests/contract/provider_tests/`）。 |

每个 ADR 的完整内容存储在 `docs/adr/` 目录下，以 `adr_xxx_title.md` 命名。新增决策需遵循 ADR 模板（`docs/adr/template.md`），并在代码评审前完成。

### 反模式清单

反模式是已知有害的设计实践，团队通过代码仓库中的历史教训积累了以下禁止清单。

| 反模式 | 描述 | 规避措施 | 代码仓库证据 |
|--------|------|----------|--------------|
| **上帝模块** | 单个模块承担过多职责，例如 `src/legacy/order_manager.py` 之前包含业务逻辑、持久化、通知和外部API调用。 | 使用模块拆分工具识别高复杂度文件，强制每个文件不超过 500 行（`src/.pylintrc` 中 `max-module-lines=500`）。重构后职责分离至 `src/domain/`、`src/application/`、`src/infrastructure/`。 | `git log --oneline -- src/legacy/order_manager.py` 显示该文件被重写的提交信息。 |
| **隐式依赖** | 使用 `import *` 或全局单例引入隐式依赖，例如旧版 `src/config.py` 暴露全局 `db_session` 导致测试耦合。 | 强制使用显式依赖注入，所有外部依赖通过构造函数或参数传入（`src/application/usecases/place_order.py`:8-15 的 `__init__` 方法）。禁止 `from x import *`，在 `.pylintrc` 中配置 `allow-any-import-star=False`。 | `src/infrastructure/dependency_injection/container.py` 展示了依赖注入容器的注册方式。 |
| **重复轮子** | 团队在不同模块中重复实现相同功能，如多个模块各自编写了相似的重试逻辑。 | 将通用能力（重试、缓存、认证）封装到 `src/infrastructure/common/` 子包，并发布为内部库（`src/infrastructure/common/retry.py`:1-20）。代码审查时检查是否有重复逻辑。 | 旧版 `src/order/services/payment_retry.py` 与 `src/inventory/services/sync_retry.py` 高度相似，已合并为一个基础重试模块。 |
| **万能 DTO** | 传递巨大的数据传输对象（DTO）包含大量无关字段，造成接口耦合。 | 每个 API 接口和内部服务调用定义专属的 DTO（如 `src/interfaces/api/schemas/order_schema.py`），仅包含必需字段。使用 `@dataclass` 或 `Pydantic` 的 `exclude_unset` 特性。 | 旧版 `src/interfaces/api/schemas/common.py` 曾定义 `OrderResponse` 包含 30+ 字段，现拆分为 `OrderCreateResponse`（10 字段）与 `OrderDetailResponse`（20 字段）。 |
| **同步等待** | 在异步环境中使用 `time.sleep()` 或 `requests.get()` 阻塞主循环，例如 `src/integration/sms_sender.py` 第 25 行曾使用 `requests.post`（同步）。 | 所有 I/O 操作改为异步库（`aiohttp` 代替 `requests`，`asyncio.sleep` 代替 `time.sleep`）。在代码规范中标记 `async def` 内不允许同步阻塞。 | `src/infrastructure/notification/sms_sender.py`:10-15 使用 `async with aiohttp.ClientSession() as session:` 实现异步发送。 |
| **忽略错误** | 捕获异常后仅空 `pass` 或打印日志，不处理也不传播。 | 异常必须被转换、重试或最终抛出自定义错误。在代码评审中使用工具扫描 `except: pass` 模式。例如 `src/legacy/cache.py` 第 50 行曾忽略 `RedisError` 导致数据不一致，现已改为显式记录并返回缓存未命中。 | 在 `src/infrastructure/cache/redis_cache.py`:70-80 中，`except CacheError` 分支记录警告并返回 `None`，而非沉默。 |

该反模式清单纳入 `docs/anti-patterns.md` 并与代码仓库的 `pre-commit` 钩子关联，自动检查部分简单模式（如 `import *`、`time.sleep` 在 `async` 函数中）。团队每季度根据新发现的反模式更新清单。

## 整体架构

本章从宏观视角描述系统的架构风格、与外部环境的交互方式以及核心架构视图，为后续模块设计、部署运维和集成测试提供统一的参考框架。

### 架构风格选型

本系统采用 **微服务架构（Microservices Architecture）** 作为核心风格，辅以 **事件驱动（Event-Driven）** 模式处理异步业务流。选型依据如下：

- **业务领域划分清晰**：系统包含用户管理、订单处理、支付结算、消息通知等独立领域，每个领域可以独立开发、测试、部署。代码仓库中 `services/` 目录下按服务名组织子项目，例如 `services/user_service/main.py:10` 定义了用户服务入口，`services/order_service/main.py:12` 定义了订单服务入口。
- **独立扩展与容错**：高负载服务（如订单服务）可单独增加实例，且单个服务故障不会引起整体系统崩溃。`deploy/k8s/order_service_hpa.yaml:15` 配置了基于CPU利用率的自动扩缩容规则。
- **技术异构性**：允许不同服务使用最适合的技术栈。例如用户服务采用 Python + FastAPI（`src/user_service/domain/user.py:20` 使用 Pydantic