"""全局 Settings SSOT.

pydantic-settings Settings SSOT, 配置只经 config/ + 环境变量.
业务代码禁止硬编码 URL/密钥.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置 SSOT (Single Source of Truth).

    从 .env 加载, 生产环境用 .env.agent + .env.{env} 分层.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========== 环境与部署 ==========
    env: Literal["dev", "prod"] = "dev"
    enable_test_page: bool = True
    log_level: str = "INFO"

    # ========== LLM 网关 (LiteLLM) ==========
    # 三级 LLM 分层:
    # - FAST: 快速任务 (摘要/分类/JSON 解析), 默认 zhipuai/glm-4-flash (智谱免费层)
    # - SMART: 复杂推理 (报告写作/章节生成), 默认 deepseek/deepseek-v4-flash
    # - STRATEGIC: 规划 (子主题拆解/agent 角色), 默认 deepseek/deepseek-v4-pro
    # 如需全 DeepSeek 栈: 将 fast_llm 改为 "deepseek/deepseek-v4-flash"
    fast_llm: str = "zhipuai/glm-4-flash"
    smart_llm: str = "deepseek/deepseek-v4-flash"
    strategic_llm: str = "deepseek/deepseek-v4-pro"
    fast_token_limit: int = 3000
    smart_token_limit: int = 8192
    # deepseek-v4-pro 代码学习需输出完整 JSON；4000 易截断导致解析失败降级
    strategic_token_limit: int = 8192
    summary_token_limit: int = 700
    max_total_tokens: int = 128000  # 单次研究流程总 token 预算上限
    temperature: float = 0.4
    llm_timeout: int = 120  # LLM 调用超时 (秒); deepseek-v4-pro 报告生成需 60s+
    llm_max_retries: int = 2
    # graph.ainvoke 总超时 (秒, 防止节点卡死永久挂起)
    # docbot 单次报告生成含多节点 LLM 调用 + RAG 检索 + 章节级语义去重 + 并发子图
    # 12 章节架构文档: 12×D(SMART LLM~60s + dedup~5s) + 12×E(FAST LLM~15s) + F + G(SMART~60s)
    # 实测双报告+20章 API 评审可达 ~1800s+; 留余量 → 3600s (60 分钟)
    graph_total_timeout: int = 3600
    # LLM 响应缓存 (Redis)
    # 仅缓存 temperature=0 的成功响应; 异常/错误响应绝不缓存; 流式响应不缓存.
    llm_response_cache_enabled: bool = True
    llm_response_cache_ttl: int = 3600  # 缓存 TTL (秒, 默认 1 小时)
    litellm_proxy_base_url: str | None = None
    litellm_proxy_api_key: str | None = None

    # 模型 API Key (按需启用)
    deepseek_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    zhipu_api_key: str | None = None
    # 智谱 AI OpenAI 兼容端点 (LiteLLM 1.90.2 不原生支持 zhipuai/ 前缀,
    # 通过 openai/ 前缀 + api_base 接入智谱 GLM 系列)
    zhipu_api_base: str = "https://open.bigmodel.cn/api/paas/v4"
    # DashScope (阿里通义 Qwen) API Key, smart_llm=qwen-max 时启用
    dashscope_api_key: str | None = None

    # ========== Qdrant ==========
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "agents"
    qdrant_vector_size: int = 768  # bge-base-zh-v1.5 固定维度

    # Qdrant HNSW 索引参数调优
    qdrant_hnsw_m: int = 32  # HNSW 图连接数 (默认 16, 中文建议 32)
    qdrant_hnsw_ef_construct: int = 200  # 构建时搜索宽度 (默认 100, 建议 200)
    qdrant_hnsw_full_scan_threshold: int = 10000  # 全扫描阈值
    qdrant_quantization: str = "scalar"  # 量化方式 (scalar/int8/binary, 默认 scalar)

    # ========== Embeddings (远程 TEI) ==========
    embeddings_base_url: str = "http://embeddings:8088"
    embeddings_model: str = "BAAI/bge-base-zh-v1.5"
    embeddings_api_key: str | None = None  # TEI API_KEY 鉴权
    embeddings_max_client_batch_size: int = (
        4  # 客户端单次 TEI 请求上限 (匹配 TEI CPU max_batch_requests=4)
    )
    # 4 texts/请求 → 1 推理批次 → 1 permit; Semaphore(3) × 1 = 3 permits < 4 可用 → 无 429
    embeddings_max_concurrent: int = 3  # 客户端并发限流 (3 HTTP 请求 × 1 permit = 3, 留 1 余量)
    # TEI 服务端并发 (compose 插值用, 与客户端 embeddings_max_concurrent 不同)
    # embeddings_max_concurrent: 客户端 HTTP 请求并发 (业务代码读取)
    # embeddings_tei_max_concurrent: TEI 服务端 MAX_CONCURRENT_REQUESTS (compose 插值, 业务代码不读取)
    embeddings_tei_max_concurrent: int = 16
    # 429 重试配置 (指数退避)
    embeddings_max_retries: int = 3
    embeddings_retry_base_delay: float = 0.5  # 基础延迟 (秒), 实际 = base * 2^attempt

    # ========== Rerank ==========
    rerank_enabled: bool = False  # 默认不启用, rerank_enabled=True 时启用 bge-reranker-v2-m3
    rerank_base_url: str = "http://rerank:8089"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_top_k: int = 5
    rerank_api_key: str | None = None  # TEI API_KEY 鉴权

    # ========== PostgreSQL ==========
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "agents"
    postgres_user: str = "agis"
    postgres_password: str | None = None
    postgres_connection_pool_size: int = 10
    # PostgresSaver AsyncConnectionPool 连接池 min/max 配置化 (按负载调整)
    # langgraph-checkpoint-postgres 1.x AsyncConnectionPool 支持 min_size/max_size 参数;
    # min_size 不超过 max_size (checkpointer 内部会做 clamp 校验).
    postgres_pool_min_size: int = 4
    postgres_pool_max_size: int = 20

    @property
    def postgres_dsn(self) -> str:
        """PostgreSQL 连接串 (asyncpg 格式)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_dsn_psycopg(self) -> str:
        """PostgreSQL 连接串 (psycopg 格式, 用于 Checkpointer)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ========== Redis ==========
    redis_url: str = "redis://redis:6379/0"
    redis_auth: str | None = None  # Redis 鉴权密码 (与 docker-compose REDIS_AUTH 对齐)
    # Redis 连接池调优 (socket_timeout/max_connections 从 .env 暴露, 业务代码读取)
    redis_socket_timeout: float = 5.0  # 命令执行超时 (秒), 超时抛 ConnectionError
    redis_max_connections: int = 50  # 连接池上限 (高并发场景调优)
    # Redis 缓存 LRU 淘汰
    redis_cache_max_size: int = 1000  # LRU 最大缓存条目数 (超过时淘汰最久未访问)
    redis_cache_lru_enabled: bool = True  # 是否启用 LRU 淘汰 (默认 True, 关闭则仅 TTL)

    # ========== 可观测性 ==========
    agentinsight_public_key: str | None = None
    agentinsight_secret_key: str | None = None
    agentinsight_host: str = "https://agent.goldebridge.com"
    tracing_embedding_sample_rate: float = 0.5

    # ========== 用户身份解析 ==========
    # 无 JWT Token 时, 按 IP 生成确定性 UserId (SHA256 哈希, 不存储原始 IP)
    # 每日报告生成限额 (按 IP 限流, 默认 5 次/日, 仅报告成功才计数)
    # 0 = 不限制; 环境变量 IP_DAILY_REPORT_LIMIT 控制
    # 注意: 此配置已迁移到数据库 report_limits 表 (user_id IS NULL 的系统默认行)
    # 此环境变量仅作为数据库不可用时的降级 fallback
    ip_daily_report_limit: int = 5

    # ========== 自托管模式 (SELF_HOST) ==========
    # True (默认): 自托管模式, JWT Token 可选, 不存在时走 IP-based 用户身份解析
    # False: 云托管模式, JWT Token 本地解析, 不存在时走 IP-based 用户身份解析
    # 两种模式统一使用项目数据库处理报告限额, 不再调用远程 API
    self_host: bool = True

    # ========== JWT 本地解析 (HS256 Claims 规格) ==========
    # 密钥仅环境变量注入, 禁止入仓/硬编码
    jwt_signing_key: str = ""  # 从环境变量 JWT_SIGNING_KEY 读取 (HS256 密钥)
    jwt_issuer: str = ""  # 从环境变量 JWT_ISSUER 读取 (签发者)
    jwt_audience: str = ""  # 从环境变量 JWT_AUDIENCE 读取 (受众)
    jwt_algorithm: str = "HS256"  # JWT 签名算法 (固定 HS256)
    jwt_clock_skew: int = 5  # 时钟偏移容忍秒数
    jwt_local_verify: bool = True  # 是否启用本地 JWT 解析

    # ========== 会话与上下文 ==========
    context_max_chars: int = 500_000
    context_compressed_target: int = 200_000
    context_session_ttl: int = 2_592_000
    debounce_seconds: float = 1.0
    flush_interval_seconds: float = 0.5
    # 每用户每智能体最多可创建的会话数 (防止滥用, 默认 10)
    max_sessions_per_user: int = 10

    # ========== 数据隔离 ==========
    agent_name: str = "agentinsight-docbot"

    # ========== RAG 检索 ==========
    vector_weight: float = 0.7
    bm25_weight: float = 0.3
    score_threshold: float = 0.3
    rrf_k: int = 60
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    # ========== L2 BM25 分层过滤 (两层方案, 上下文压缩主路径) ==========
    # 两层路由: <8K Fast Path | >=8K BM25Filter (全量覆盖, 含 >50K 超长上下文)
    # 性能: 258 chunks BM25 本地计算 ~2s (远快于远程 TEI 推理)
    # 零新依赖 (rank-bm25 + jieba 已声明)
    bm25_filter_enabled: bool = True  # 默认启用, 上下文压缩主路径
    bm25_filter_char_threshold: int = (
        8000  # < 此值走 Fast Path 不压缩 (环境变量: BM25_FILTER_CHAR_THRESHOLD)
    )
    bm25_filter_char_upper: int = 50000  # 兼容字段, 保留供向后兼容
    bm25_filter_top_k: int = 20  # 返回 Top-K (与 embeddings_filter_top_k 对齐)
    bm25_filter_top_k_for_rerank: int = (
        50  # BM25 粗筛返回数量 (供 FastEmbed 精排用, 环境变量: BM25_FILTER_TOP_K_FOR_RERANK)
    )
    bm25_filter_score_threshold: float = (
        0.0  # BM25 分数阈值 (0.0=仅过滤零分; BM25 分数无上界, 不可与 cosine 阈值复用)
    )
    bm25_filter_chunk_size: int = 1000  # 分块大小 (与 embeddings_filter_chunk_size 一致)
    bm25_filter_chunk_overlap: int = 100  # 分块 overlap
    bm25_filter_timeout: float = 5.0  # 本地计算超时 (秒, 远快于旧 EmbeddingsFilter 15s)

    # ========== FastEmbed 精排 (两阶段检索第二阶段, 上下文压缩专用) ==========
    # 总 chunk 数 > embeddings_rerank_chunk_threshold 时, 启用 FastEmbed 精排:
    #   BM25 先召回 bm25_filter_top_k_for_rerank 个候选, FastEmbed 从中再选 embeddings_rerank_top_k 个
    # 总 chunk 数 <= embeddings_rerank_chunk_threshold 时, 直接返回 BM25 结果
    # 注: 此精排用 FastEmbed 本地 bge-small-zh-v1.5 (512维), 与私有数据 Qdrant 检索
    #     用的远程 TEI bge-base-zh-v1.5 (768维) 完全隔离, 不依赖远程 TEI 服务
    embeddings_rerank_top_k: int = (
        20  # FastEmbed 精排后返回 Top-K (环境变量: EMBEDDINGS_RERANK_TOP_K)
    )
    embeddings_rerank_chunk_threshold: int = (
        30  # 启用精排的 chunk 数量阈值 (环境变量: EMBEDDINGS_RERANK_CHUNK_THRESHOLD)
    )

    # ========== FastEmbed 本地 Embeddings (上下文压缩专用) ==========
    # 用于 FastEmbed 精排 + WrittenContentCompressor 跨子主题去重, 不依赖远程 TEI
    # 远程 TEI (bge-base-zh-v1.5, 768维) 仅用于私有数据 Qdrant 索引/检索
    # bge-small-zh-v1.5 ONNX INT8 模型, 输出 512 维向量
    fastembed_model_name: str = "BAAI/bge-small-zh-v1.5"
    fastembed_model_path: str = (
        "./models/bge-small-zh-v1.5-onnx"  # ONNX 模型本地路径 (环境变量: FASTEMBED_MODEL_PATH)
    )
    fastembed_dimension: int = 512  # bge-small-zh-v1.5 固定维度
    fastembed_max_length: int = 512  # 最大序列长度
    # ONNX Runtime 并行执行 (推理加速 2-4x)
    # intra_op_num_threads: 单操作内部并行线程数 (矩阵乘法等)
    # inter_op_num_threads: 操作间并行线程数 (独立操作并行)
    fastembed_onnx_intra_threads: int = (
        0  # 0=自动 (cpu_count), 环境变量: FASTEMBED_ONNX_INTRA_THREADS
    )
    fastembed_onnx_inter_threads: int = (
        0  # 0=自动 (cpu_count//2), 环境变量: FASTEMBED_ONNX_INTER_THREADS
    )

    # ========== 上下文压缩与去重参数 ==========
    # WrittenContentCompressor 跨章节去重阈值
    # 0.85 对齐 AIR 推荐值, 避免 docbot 章节间自然语义关联被误判为重复
    # (architecture 文档的 "系统概述" / "架构原则" / "整体架构" 等章节有概念重叠,
    #  阈值过低会导致正常章节被去重跳过, 破坏章节完整性)
    written_content_similarity_threshold: float = 0.85
    # 递归分块参数 (chunk_size=1000 是 RecursiveCharacterTextSplitter 默认值)
    # 参数供 BM25Filter/WrittenContentCompressor 复用 recursive_split.
    embeddings_filter_chunk_size: int = 1000
    embeddings_filter_chunk_overlap: int = 100
    # 精排返回 Top-K (EmbeddingsFilter k=20)
    # 供 ContextManager._embeddings_rerank (FastEmbed 精排) 使用.
    embeddings_filter_top_k: int = 20

    # ========== 报告输出 ==========
    default_report_format: Literal["markdown", "html", "pdf", "docx", "json"] = "markdown"
    default_report_type: Literal[
        "architecture",
        "design",
        "requirements",
        "testcase",
        "optimization",
        "performance",
        "defect",
        "api_doc",
    ] = "architecture"
    # 报告语言 (zh|en), 默认 zh; docbot 仅支持 2 种语言
    report_language: str = "zh"
    # 报告 YAML frontmatter 开关 (默认 False, 启用后在报告首部追加元信息块).
    # frontmatter 含 title/date/query/word_count/sources_count 字段, 便于下游解析.
    enable_frontmatter: bool = False

    # ========== CORS (禁 *) ==========
    cors_allow_origins: str = "http://localhost:3000,http://localhost:8068"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS 允许的源列表."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def supported_languages_list(self) -> list[str]:
        """docbot 支持的语言列表."""
        return [x.strip() for x in self.supported_languages.split(",") if x.strip()]

    @property
    def supported_report_types_list(self) -> list[str]:
        """docbot 支持的文档类型列表."""
        return [x.strip() for x in self.supported_report_types.split(",") if x.strip()]

    @property
    def allowed_git_domains_list(self) -> list[str]:
        """允许的 Git 域名白名单列表."""
        if not self.allowed_git_domains:
            return []
        return [x.strip() for x in self.allowed_git_domains.split(",") if x.strip()]

    # ===== docbot 专属配置 =====
    # 仓库大小限制（MB）
    max_repo_size_mb: int = 1024
    # D-E 修订循环每章节最多 3 轮
    max_revisions_per_chapter: int = 3
    # 单报告最大章节数
    max_chapters_per_report: int = 20
    # 单次请求最多并发派发 3 个 B 子图
    max_concurrent_reports: int = 3
    # 全局 LLM 调用并发上限
    max_llm_concurrency: int = 5
    # RAG 检索并发上限
    max_rag_concurrency: int = 10
    # 代码仓库加密密钥（AES-GCM, 32 字节）
    git_credential_key: str | None = None
    # 仓库克隆父目录
    repo_clone_root: str = "/tmp/repos"
    # 允许的 Git 域名白名单（逗号分隔，空表示允许全部）
    allowed_git_domains: str = ""
    # 文档默认大纲目录 (YAML 格式, 与代码同包发布)
    docbot_outlines_dir: str = "src/config/docbot/outlines"
    # 6 步流水线缓存 TTL（秒，默认 24 小时）
    docbot_cache_ttl: int = 86400
    # P2-5.4.1 多视角代码审问开关 (默认关闭, 开启后任务一改用多视角流程)
    # 多视角流程: 3 视角并发 (FAST 提问 → SMART 回答) → STRATEGIC 汇总
    # 成本约为单视角的 4-5 倍, 但代码理解深度显著提升
    docbot_multi_perspective_enabled: bool = False
    # 支持 2 种语言
    supported_languages: str = "zh,en"
    # 支持 8 种文档类型
    supported_report_types: str = (
        "architecture,design,requirements,testcase,optimization,performance,defect,api_doc"
    )
    # MCP 子进程配置（系统自带，不入 mcp_configs 表）
    mcp_git_command: str = "uvx"
    mcp_git_args: str = '["mcp-server-git"]'
    mcp_filesystem_command: str = "npx"
    mcp_filesystem_args: str = '["-y", "@modelcontextprotocol/server-filesystem", "/tmp/repos"]'

    # ========== 图像生成 (报告配图, 可选) ==========
    # 默认启用报告配图; SVG 模式经 DeepSeek V4 Flash /chat/completions 生成 SVG 代码
    # 留空 image_api_key 时复用 resolve_api_key 解析 (默认回退到 deepseek_api_key)
    image_generation_enabled: bool = True
    image_model: str = "deepseek/deepseek-v4-flash"
    image_api_key: str | None = None
    image_output_format: str = "svg"  # svg | url | b64 (svg 推荐, url/b64 为位图保留路径)
    image_quality: str = "standard"  # 位图质量 (standard|hd), SVG 模式忽略
    image_svg_temperature: float = 0.7
    image_svg_max_tokens: int = 16384

    # ========== 报告输出目录 (Publisher 生成 PDF/HTML 降级落盘) ==========
    upload_dir: str = "/tmp/uploads"

    @field_validator("env")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        """环境值校验."""
        if v not in ("dev", "prod"):
            raise ValueError(f"ENV 必须为 dev 或 prod, 实际: {v}")
        return v

    def validate_production(self) -> None:
        """生产环境强制校验.

        - 密钥必须存在
        - 生产关闭 Debug
        """
        if self.env != "prod":
            return
        errors: list[str] = []
        if not self.agentinsight_public_key or not self.agentinsight_secret_key:
            errors.append("生产环境必须配置 AGENTINSIGHT_PUBLIC_KEY 和 AGENTINSIGHT_SECRET_KEY")
        if not self.postgres_password:
            errors.append("生产环境必须配置 POSTGRES_PASSWORD")
        if errors:
            raise ValueError("生产环境配置校验失败:\n" + "\n".join(f"  - {e}" for e in errors))


@lru_cache
def get_settings() -> Settings:
    """获取全局 Settings 单例."""
    settings = Settings()
    settings.validate_production()
    return settings
