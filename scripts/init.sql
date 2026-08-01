-- agentinsight-agents 主目录统一数据库初始化脚本
-- 单库 agents, 业务表含 agent_id+user_id 双列复合索引
-- LangGraph PostgresSaver 表由官方 SDK 管理 (thread_id 已含会话隔离)
--
-- 本文件为所有智能体 (researcher/docbot) 共享的业务表 DDL 真源 (Source of Truth)
-- 部署机制:
--   1. docker-compose*.yml 将本文件挂载到 postgres 容器 /docker-entrypoint-initdb.d/init.sql
--   2. postgres 容器首次启动时自动执行 (仅首次, 后续靠 DDL 幂等性保证)
--   3. 本文件每次更新后, 需删除 postgres_data 卷重新构建 postgres 容器:
--      docker compose -p agentinsight down -v  # 危险: 会清空所有数据
--      或仅重建 postgres: docker compose -p agentinsight up --build -d --force-recreate postgres
--   4. 各子项目 scripts/init.sql 为本文件的同步副本 (主目录修改后由 sync 脚本同步)
--
-- 设计原则:
-- 1. CREATE TABLE 定义与最终状态一致 (新部署直接正确)
-- 2. ALTER TABLE 保留作为旧表兜底 (CREATE TABLE IF NOT EXISTS 对已存在的表是 no-op, 不会添加新列)
-- 3. 所有 DDL 使用 IF NOT EXISTS / IF EXISTS / CREATE OR REPLACE 保证幂等 (重复执行不出错)
-- 4. 唯一索引创建前清理重复数据 (防止历史脏数据导致索引创建失败)
-- 5. agent_id 列允许各 Agent 通过相同 schema 隔离数据 (researcher/docbot 不再各自维护独立 DDL)

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ========== LangGraph Checkpointer 表 ==========
-- 由 langgraph-checkpoint-postgres SDK 自动管理, 此处仅占位说明
-- 实际表名: checkpoints / writes / migrations (由 SDK 创建)

-- ========== 业务表: 研究会话 ==========
-- 合并: title 字段 + query/report_type/report_format 去掉 NOT NULL (原 ALTER 迁移, 现合并到 CREATE)
CREATE TABLE IF NOT EXISTS research_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,           -- 即 thread_id
    agent_id VARCHAR(64) NOT NULL,             -- agent_name, 全局唯一隔离键
    user_id VARCHAR(64) NOT NULL,              -- 用户隔离
    query TEXT,                                -- 原始研究请求 (允许空会话)
    report_type VARCHAR(32) DEFAULT 'detailed_report',  -- 空会话无报告类型 (任务1: 默认详细报告)
    report_format VARCHAR(16) DEFAULT 'markdown',    -- 空会话无报告格式
    language VARCHAR(8) DEFAULT 'zh',               -- 报告语言 (zh/en)
    agent_role VARCHAR(256),                   -- LLM 动态生成的角色 persona
    agent_role_server VARCHAR(64),             -- 角色简称 (如 financial_analyst)
    title VARCHAR(256),                        -- 会话列表显示标题
    status VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed
    total_cost_usd NUMERIC(12,6) DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    client_ip VARCHAR(64),                     -- 客户端 IP 地址 (审计追溯用, PII)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days')
);
-- 索引: 删除被复合索引前缀覆盖的冗余单列索引 (idx_research_sessions_agent_user, idx_research_sessions_session)
CREATE INDEX IF NOT EXISTS idx_research_sessions_expires ON research_sessions(expires_at);
-- 复合索引 (agent_id + user_id + updated_at DESC): 支持按用户列出会话列表 (按最近更新排序)
CREATE INDEX IF NOT EXISTS idx_research_sessions_agent_user_updated
    ON research_sessions(agent_id, user_id, updated_at DESC);

-- ========== 业务表: 研究报告存储 ==========
-- 合并: created_at/updated_at 加 NOT NULL 约束 (原 ALTER 迁移, 现合并到 CREATE)
CREATE TABLE IF NOT EXISTS research_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    query TEXT NOT NULL,
    report_md TEXT NOT NULL,
    report_format VARCHAR(32) DEFAULT 'markdown',
    sources JSONB DEFAULT '[]'::jsonb,
    agent_role VARCHAR(256),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 索引: 删除被复合索引前缀覆盖的冗余单列索引 (idx_research_reports_session, idx_research_reports_user, idx_research_reports_created)
-- 复合索引 (agent_id, user_id): 多 Agent 数据隔离
CREATE INDEX IF NOT EXISTS idx_research_reports_agent_user ON research_reports(agent_id, user_id);
-- 复合索引 (session_id, agent_id, user_id): 加速按会话检索报告
CREATE INDEX IF NOT EXISTS idx_research_reports_session_agent_user ON research_reports(session_id, agent_id, user_id);
-- 迁移: 已有 research_reports 表补充新增列 (PostgreSQL 9.6+, 旧表兜底)
ALTER TABLE IF EXISTS research_reports ADD COLUMN IF NOT EXISTS report_id UUID DEFAULT gen_random_uuid();
ALTER TABLE IF EXISTS research_reports ADD COLUMN IF NOT EXISTS query TEXT;
ALTER TABLE IF EXISTS research_reports ADD COLUMN IF NOT EXISTS report_format VARCHAR(32) DEFAULT 'markdown';
ALTER TABLE IF EXISTS research_reports ADD COLUMN IF NOT EXISTS agent_role VARCHAR(256);
ALTER TABLE IF EXISTS research_reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
-- docbot 扩展列: 文档类型标签/摘要/SVG 配图 (8 种文档类型: architecture|design|requirements|testcase|optimization|performance|defect|api_doc)
ALTER TABLE IF EXISTS research_reports
    ADD COLUMN IF NOT EXISTS report_type_label VARCHAR(64),
    ADD COLUMN IF NOT EXISTS report_summary TEXT,
    ADD COLUMN IF NOT EXISTS report_image_svg TEXT;
-- P1-5.3.2 文档漂移检测: 标记文档是否因代码变更而过期
ALTER TABLE IF EXISTS research_reports
    ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS stale_reason TEXT,
    ADD COLUMN IF NOT EXISTS stale_detected_at TIMESTAMPTZ;
-- docbot 索引: 按 agent_id + user_id + report_type_label 查询用户的某类文档 (见 architecture.md §5.3)
CREATE INDEX IF NOT EXISTS idx_research_reports_agent_user_type
    ON research_reports(agent_id, user_id, report_type_label);
-- 兜底唯一索引: 旧表无 report_id PK 时保证唯一 (新表已有 PK, DO 块条件化避免冗余)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'research_reports'
          AND indexname = 'research_reports_pkey'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'research_reports'
          AND indexname = 'idx_research_reports_report_id'
    ) THEN
        CREATE UNIQUE INDEX idx_research_reports_report_id ON research_reports(report_id);
    END IF;
END $$;

-- ========== 业务表: Token 使用记录 (用户需求 10, Token 优化审计) ==========
CREATE TABLE IF NOT EXISTS token_usage_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    stage VARCHAR(64) NOT NULL,                -- planning/researching/reviewing/writing
    llm_tier VARCHAR(16) NOT NULL,             -- fast/smart/strategic
    model VARCHAR(64),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_token_usage_logs_agent_user ON token_usage_logs(agent_id, user_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_logs_session ON token_usage_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_logs_stage ON token_usage_logs(stage);

-- ========== 业务表: 报告行级引用溯源 (P1-5.3.1, 2026-07-29 新增) ==========
-- 存储文档中 [src/foo.py:L42-L58] 形式引用 → 代码位置映射, 支持引用可追溯性
-- 设计参考: STORM 引用机制; 引用校验由 structure_validator + citation_extractor 完成
CREATE TABLE IF NOT EXISTS report_citations (
    id BIGSERIAL PRIMARY KEY,
    report_id UUID NOT NULL,                   -- 关联 research_reports.report_id
    agent_id VARCHAR(64) NOT NULL,             -- 多 Agent 数据隔离
    user_id VARCHAR(64) NOT NULL,              -- 用户隔离
    session_id VARCHAR(64) NOT NULL,           -- 会话隔离
    report_type_label VARCHAR(64),             -- 8 种文档类型之一
    chapter_idx INTEGER,                       -- 引用所在章节序号 (1-based)
    file_path VARCHAR(512) NOT NULL,           -- 被引用的代码文件路径 (如 src/foo.py)
    line_start INTEGER,                        -- 行号起始 (可选, 单行引用时等于 line_end)
    line_end INTEGER,                          -- 行号结束 (可选)
    raw_reference VARCHAR(256),                -- 原始引用文本 (如 [src/foo.py:L42-L58])
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 复合索引: 按 report_id 查询所有引用 (报告下载页"点击引用跳转代码"用)
CREATE INDEX IF NOT EXISTS idx_report_citations_report ON report_citations(report_id);
-- 复合索引: 多 Agent 数据隔离 + 按用户检索
CREATE INDEX IF NOT EXISTS idx_report_citations_agent_user
    ON report_citations(agent_id, user_id);
-- 复合索引: 按文件路径反查引用了该文件的所有报告 (代码变更触发文档漂移检测用, P1-5.3.2)
CREATE INDEX IF NOT EXISTS idx_report_citations_file_path
    ON report_citations(agent_id, user_id, file_path);
-- 外键约束: report_id 应在 research_reports 中存在 (延迟约束, 允许先建引用后补报告)
-- 注: 不加 FK 强制约束, 因 final_cache 写入顺序可能先于 research_reports 落库

-- ========== V7: 时间戳字段完整性修复 (P0) ==========
-- 1. 回填 research_reports 历史 NULL 值 (幂等: 二次执行无 NULL 行可更新)
UPDATE research_reports SET created_at = NOW() WHERE created_at IS NULL;
UPDATE research_reports SET updated_at = NOW() WHERE updated_at IS NULL;

-- 2. 加固 research_reports NOT NULL 约束 (旧表兜底, 新表 CREATE TABLE 已含 NOT NULL)
-- SET NOT NULL 在列已为 NOT NULL 时是 no-op, 幂等安全
ALTER TABLE IF EXISTS research_reports
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT NOW();

-- 3. 通用触发器函数: 自动维护 updated_at (幂等: CREATE OR REPLACE)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. 为状态会变更的表挂触发器 (PostgreSQL 14+ 支持 CREATE OR REPLACE TRIGGER)
CREATE OR REPLACE TRIGGER trg_research_sessions_updated_at
    BEFORE UPDATE ON research_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_research_reports_updated_at
    BEFORE UPDATE ON research_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========== 业务表: 用户代码仓库配置 (docbot 专属, 仅个人仓库) ==========
-- 存储 user_git_repos 配置 (AES-GCM 加密敏感字段), MCP 工具 mcp-server-git + mcp-server-filesystem
-- 由 server.py lifespan 启动子进程, 所有用户共享, 不入此表, 不暴露 CRUD 端点
CREATE TABLE IF NOT EXISTS user_git_repos (
    id VARCHAR(64) PRIMARY KEY,                 -- uuid4
    agent_id VARCHAR(64) NOT NULL,              -- agent_name, 全局唯一隔离键
    user_id VARCHAR(64) NOT NULL,               -- 用户隔离
    repo_name VARCHAR(256) NOT NULL,            -- 仓库名称（用户自定义）
    platform VARCHAR(32) NOT NULL,              -- github|gitlab|gitee|bitbucket|coding|gitea|custom
    repo_url TEXT NOT NULL,                     -- 仓库克隆 URL
    default_branch VARCHAR(64) DEFAULT 'main',  -- 默认分支
    auth_type VARCHAR(16) NOT NULL DEFAULT 'none', -- none|token|password|ssh_key
    encrypted_token TEXT,                       -- AES-GCM 加密后的 token
    encrypted_username TEXT,                    -- AES-GCM 加密后的用户名
    encrypted_password TEXT,                    -- AES-GCM 加密后的密码
    encrypted_ssh_key TEXT,                     -- AES-GCM 加密后的 SSH 私钥
    ssh_passphrase TEXT,                        -- AES-GCM 加密后的 SSH passphrase
    clone_depth INTEGER NOT NULL DEFAULT 0,     -- 0=完整克隆, >0=浅克隆深度
    enabled BOOLEAN NOT NULL DEFAULT TRUE,      -- 是否启用
    last_synced_at TIMESTAMPTZ,                 -- 最后同步时间
    last_sync_status VARCHAR(32),               -- success|failed|pending
    last_sync_error TEXT,                       -- 最后同步错误信息
    last_doc_commit_hash VARCHAR(40),           -- P1-5.3.2: 上次生成文档时的 commit hash (40 字符 SHA-1)
    last_doc_synced_at TIMESTAMPTZ,             -- P1-5.3.2: 上次文档生成对应的同步时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_git_repos_agent_user ON user_git_repos(agent_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_git_repos_enabled ON user_git_repos(agent_id, user_id, enabled);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_git_repos_unique_name
    ON user_git_repos(agent_id, user_id, repo_name);
-- 旧表兜底: P1-5.3.2 新增 last_doc_commit_hash / last_doc_synced_at 列
ALTER TABLE IF EXISTS user_git_repos
    ADD COLUMN IF NOT EXISTS last_doc_commit_hash VARCHAR(40),
    ADD COLUMN IF NOT EXISTS last_doc_synced_at TIMESTAMPTZ;
CREATE OR REPLACE TRIGGER trg_user_git_repos_updated_at
    BEFORE UPDATE ON user_git_repos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 旧表兜底: research_reports 字段长度统一 VARCHAR(64) (与其他表一致)
-- 新表 CREATE TABLE 已是 VARCHAR(64), 旧表通过 ALTER 迁移
ALTER TABLE IF EXISTS research_reports ALTER COLUMN session_id TYPE VARCHAR(64);
ALTER TABLE IF EXISTS research_reports ALTER COLUMN user_id TYPE VARCHAR(64);
ALTER TABLE IF EXISTS research_reports ALTER COLUMN agent_id TYPE VARCHAR(64);

-- ========== 业务表: 对话消息存储 (以 UserId 为单位的会话持久化) ==========
-- 存储用户与 Agent 的完整对话内容 (user / assistant 消息)
-- 按 session_id + agent_id + user_id 三级隔离, 支持会话列表与消息分页加载
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,             -- 即 thread_id
    agent_id VARCHAR(64) NOT NULL,               -- agent_name, 全局唯一隔离键
    user_id VARCHAR(64) NOT NULL,                -- 用户隔离
    role VARCHAR(16) NOT NULL,                   -- user | assistant
    content TEXT NOT NULL,                       -- 消息内容
    message_metadata JSONB,                      -- 可选元数据 (如 sources, tool_calls)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 复合索引: 按 session + agent + user 隔离, 按时间倒序分页查询
CREATE INDEX IF NOT EXISTS idx_chat_messages_session
    ON chat_messages(session_id, agent_id, user_id, created_at DESC);
-- 复合索引: 按 agent + user 查询消息统计
CREATE INDEX IF NOT EXISTS idx_chat_messages_agent_user
    ON chat_messages(agent_id, user_id, created_at DESC);

-- ========== research_sessions 表适配会话持久化需求 ==========
-- 旧表兜底: 新增 title 字段 (新表 CREATE TABLE 已含)
ALTER TABLE IF EXISTS research_sessions
    ADD COLUMN IF NOT EXISTS title VARCHAR(256);
-- 旧表兜底: 放宽 query 约束 (新表 CREATE TABLE 已去掉 NOT NULL)
ALTER TABLE IF EXISTS research_sessions ALTER COLUMN query DROP NOT NULL;
-- 旧表兜底: 放宽 report_type 约束 (新表 CREATE TABLE 已去掉 NOT NULL)
ALTER TABLE IF EXISTS research_sessions ALTER COLUMN report_type DROP NOT NULL;
-- 旧表兜底: 放宽 report_format 约束 (新表 CREATE TABLE 已去掉 NOT NULL)
ALTER TABLE IF EXISTS research_sessions ALTER COLUMN report_format DROP NOT NULL;
-- 旧表兜底: 新增 language 字段 (新表 CREATE TABLE 已含)
ALTER TABLE IF EXISTS research_sessions ADD COLUMN IF NOT EXISTS language VARCHAR(8) DEFAULT 'zh';
-- 旧表兜底: 新增 client_ip 字段 (新表 CREATE TABLE 已含, 审计追溯用)
ALTER TABLE IF EXISTS research_sessions ADD COLUMN IF NOT EXISTS client_ip VARCHAR(64);

-- 清理 research_sessions 历史重复数据 (保留每个 session 三元组的最小 id, 防止唯一索引创建失败)
DELETE FROM research_sessions
WHERE id NOT IN (
    SELECT MIN(id) FROM research_sessions
    GROUP BY session_id, agent_id, user_id
);

-- 唯一索引 (session_id, agent_id, user_id): 支持 ON CONFLICT 幂等插入 (ensure_session 方法)
CREATE UNIQUE INDEX IF NOT EXISTS idx_research_sessions_unique_session
    ON research_sessions(session_id, agent_id, user_id);

-- ========== 业务表: 每日报告生成限额 (从环境变量迁移到数据库) ==========
-- 语义说明 (agent_id + user_id 三级默认):
--   (agent_id IS NULL, user_id IS NULL) → 全局默认 (所有 Agent 的兜底)
--   (agent_id = 'xxx',  user_id IS NULL) → Agent 级默认
--   (agent_id = 'xxx',  user_id = 'yyy') → 用户级专属
-- 用户有限额时用用户的, 没有则用 Agent 级, 再没有用全局 (非取较高者)
CREATE TABLE IF NOT EXISTS report_limits (
    id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(64),                     -- NULL = 全局默认; 非 NULL = Agent 级/用户级
    user_id VARCHAR(64),                      -- NULL = (agent_id 级) 默认; 非 NULL = 用户专属
    daily_limit INTEGER NOT NULL DEFAULT 5,    -- 每日报告生成限额 (>0 有效; 0/缺失回退下级或默认, 不表示不限制)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 旧表兜底: 新增 agent_id 列 (新表 CREATE TABLE 已含)
ALTER TABLE IF EXISTS report_limits ADD COLUMN IF NOT EXISTS agent_id VARCHAR(64);
-- 旧表兜底: 移除 user_id 列级 UNIQUE 约束 (改为复合唯一索引)
-- 列级 UNIQUE 约束名默认为 <table>_<column>_key
ALTER TABLE IF EXISTS report_limits DROP CONSTRAINT IF EXISTS report_limits_user_id_key;
-- 删除旧唯一索引 (user_id 单列), 改为 (agent_id, user_id) 复合唯一索引
DROP INDEX IF EXISTS idx_report_limits_user;
-- 唯一索引: (agent_id, user_id) 支持 ON CONFLICT 幂等 upsert
-- COALESCE 处理 NULL: PostgreSQL 中 NULL != NULL, 用 COALESCE 将 NULL 视为 '' 保证全局默认行唯一
CREATE UNIQUE INDEX IF NOT EXISTS idx_report_limits_agent_user
    ON report_limits (COALESCE(agent_id, ''), COALESCE(user_id, ''));
-- 触发器: 自动维护 updated_at
CREATE OR REPLACE TRIGGER trg_report_limits_updated_at
    BEFORE UPDATE ON report_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- 预置全局默认限额 (agent_id IS NULL, user_id IS NULL, daily_limit = 5)
-- 清理历史重复记录 (旧 ON CONFLICT bug 导致每次启动新增一行, 保留 id 最小的一条)
-- 同时清理所有 (agent_id, user_id) 组合的重复行 (不仅限于全局默认)
DELETE FROM report_limits
WHERE id NOT IN (
    SELECT MIN(id) FROM report_limits
    GROUP BY COALESCE(agent_id, ''), COALESCE(user_id, '')
);
-- 用 WHERE NOT EXISTS 保证幂等: 已存在则不插入 (管理员可手动调整后不被重置)
-- 不用 ON CONFLICT (COALESCE(...)): PostgreSQL 推断用原始 NULL 值比较, NULL != NULL 导致冲突检测失败
INSERT INTO report_limits (agent_id, user_id, daily_limit)
SELECT NULL, NULL, 5
WHERE NOT EXISTS (
    SELECT 1 FROM report_limits
    WHERE agent_id IS NULL AND user_id IS NULL
);
-- 预置 docbot Agent 级默认限额 (agent_id='agentinsight-docbot', user_id IS NULL, daily_limit=3)
-- 用户有专属限额时取用户级; 否则取本行 Agent 级; 再否则回退全局默认
INSERT INTO report_limits (agent_id, user_id, daily_limit)
SELECT 'agentinsight-docbot', NULL, 3
WHERE NOT EXISTS (
    SELECT 1 FROM report_limits
    WHERE agent_id = 'agentinsight-docbot' AND user_id IS NULL
);

-- ========== 业务表: 每日报告生成使用次数 (从 Redis 迁移到数据库) ==========
-- 按 agent_id + UserId + 日期 记录当日报告生成次数
CREATE TABLE IF NOT EXISTS daily_report_usage (
    id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,             -- agent_name, 全局唯一隔离键
    user_id VARCHAR(64) NOT NULL,              -- 用户 ID (IP-based 或 JWT 解析)
    usage_date DATE NOT NULL,                  -- 使用日期 (北京时间 YYYY-MM-DD)
    daily_count INTEGER NOT NULL DEFAULT 0,    -- 当日已生成次数
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 旧表兜底: 新增 agent_id 列 (新表 CREATE TABLE 已含 NOT NULL)
ALTER TABLE IF EXISTS daily_report_usage ADD COLUMN IF NOT EXISTS agent_id VARCHAR(64);
-- 旧表兜底: 加固 agent_id NOT NULL 约束 (新表 CREATE TABLE 已含)
ALTER TABLE IF EXISTS daily_report_usage ALTER COLUMN agent_id SET NOT NULL;
-- 删除旧唯一索引 (user_id, usage_date), 改为 (agent_id, user_id, usage_date) 复合唯一索引
DROP INDEX IF EXISTS idx_daily_report_usage_user_date;
-- 唯一约束: (agent_id, user_id, usage_date) 支持 ON CONFLICT 幂等 upsert
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_report_usage_agent_user_date
    ON daily_report_usage(agent_id, user_id, usage_date);
-- 复合索引: (agent_id, user_id) 支持按用户统计用量
CREATE INDEX IF NOT EXISTS idx_daily_report_usage_agent_user
    ON daily_report_usage(agent_id, user_id);
-- 触发器: 自动维护 updated_at
CREATE OR REPLACE TRIGGER trg_daily_report_usage_updated_at
    BEFORE UPDATE ON daily_report_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========== 业务表: MCP 配置 (researcher 专属, 系统/用户 MCP 配置) ==========
-- 存储 MCP (Model Context Protocol) 服务配置, 支持三种传输模式:
--   stdio (本地模式): command 必填, 通过 stdin/stdout 与本地进程通信
--   sse (远程模式): server_url 必填, 通过 SSE 连接远程 HTTP 服务器
--   streamable_http (远程模式): server_url 必填, 通过 HTTP 流连接远程服务器
-- 数据隔离:
--   系统 MCP: agent_id IS NULL AND is_system = TRUE (全局共享, 用户可查看/克隆但不可编辑/删除)
--   用户 MCP: agent_id = $1 AND user_id = $2 AND is_system = FALSE (用户私有)
CREATE TABLE IF NOT EXISTS mcp_configs (
    id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(64),                     -- NULL = 系统 MCP (全局共享); 非 NULL = 用户 MCP
    user_id VARCHAR(64),                      -- 用户 MCP 时必填 (系统 MCP 为 NULL)
    name VARCHAR(64) NOT NULL,                -- 配置名称
    server_url TEXT,                          -- MCP Server URL (stdio 模式可空, sse/streamable_http 必填)
    transport_type VARCHAR(32) NOT NULL,      -- stdio / sse / streamable_http
    command VARCHAR(256),                     -- 启动命令 (stdio 模式必填, 如 npx/uvx/python)
    args JSONB,                               -- 命令参数 (list[str], stdio 模式)
    env_vars JSONB,                           -- 环境变量 (dict[str, str], stdio 模式, 含 Key 等)
    enabled BOOLEAN NOT NULL DEFAULT FALSE,   -- 是否启用 (新增/更新时测试失败自动设为 FALSE)
    is_system BOOLEAN NOT NULL DEFAULT FALSE, -- 是否系统公用 MCP (用户不可编辑/删除)
    description TEXT,                         -- 描述
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 旧表兜底: CREATE TABLE IF NOT EXISTS 对已存在的表是 no-op, 不会添加新列
-- 若 mcp_configs 表是旧版创建的 (缺少 is_system/enabled/description 等列), INSERT 会失败
-- 用 ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS 补齐缺失列 (幂等, 已存在则 no-op)
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS agent_id VARCHAR(64);
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS user_id VARCHAR(64);
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS name VARCHAR(64) NOT NULL DEFAULT '';
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS server_url TEXT;
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS transport_type VARCHAR(32) NOT NULL DEFAULT 'stdio';
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS command VARCHAR(256);
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS args JSONB;
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS env_vars JSONB;
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE IF EXISTS mcp_configs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
-- 旧表约束修正: 旧版 mcp_configs 的 user_id 为 NOT NULL, 阻止系统 MCP 插入 (系统 MCP user_id IS NULL)
-- DROP NOT NULL 幂等: 若已为 nullable 则 no-op, 若为 NOT NULL 则放宽 (PostgreSQL ≥9.6)
-- 必须在 INSERT 系统 MCP 之前执行, 否则所有系统 MCP INSERT 都会失败
ALTER TABLE IF EXISTS mcp_configs ALTER COLUMN user_id DROP NOT NULL;
-- 旧表默认值修正: 旧版 enabled 默认为 TRUE (新装即启用, 不安全), 改为 FALSE (用户显式启用)
-- SET DEFAULT 幂等: 重复执行无副作用
ALTER TABLE IF EXISTS mcp_configs ALTER COLUMN enabled SET DEFAULT FALSE;
-- 旧表版本列: 旧版有 version 列 (新版已移除), 保留不影响功能 (向后兼容)
-- 不做 DROP COLUMN, 避免数据丢失
-- 复合索引: 用户 MCP 查询 (agent_id + user_id + is_system = FALSE)
CREATE INDEX IF NOT EXISTS idx_mcp_configs_agent_user ON mcp_configs(agent_id, user_id, is_system);
-- 索引: 系统 MCP 查询 (agent_id IS NULL AND is_system = TRUE)
CREATE INDEX IF NOT EXISTS idx_mcp_configs_system ON mcp_configs(is_system) WHERE is_system = TRUE;
-- 唯一索引重建: 旧版索引无 WHERE 子句 (覆盖系统 MCP, 阻止同 name 系统配置共存)
-- 新版仅约束用户 MCP (is_system = FALSE), 系统 MCP 不受唯一约束 (可重复 INSERT 兜底)
-- DROP IF EXISTS 幂等: 不存在则 no-op, 存在则删除后重建
DROP INDEX IF EXISTS idx_mcp_configs_unique_name;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mcp_configs_unique_name
    ON mcp_configs(COALESCE(agent_id, ''), COALESCE(user_id, ''), name) WHERE is_system = FALSE;
-- 触发器: 自动维护 updated_at
CREATE OR REPLACE TRIGGER trg_mcp_configs_updated_at
    BEFORE UPDATE ON mcp_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 预置系统 MCP 配置 (agent_id IS NULL, is_system = TRUE)
-- 用户可通过 POST /v1/mcp/system/{config_id}/clone 克隆到自己的列表
-- 所有系统 MCP 默认禁用 (enabled=FALSE), 用户克隆后需填 Key 并测试通过才可启用
--
-- 幂等策略: 先删除所有系统 MCP, 再重新插入
-- (系统 MCP 为预置模板, 用户克隆后变 is_system=FALSE, 不受此删除影响)
DELETE FROM mcp_configs WHERE is_system = TRUE;

-- 1. fetch (Python, uvx) - 网页抓取工具 (官方参考实现, 无需 Key)
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'fetch', NULL, 'stdio', 'uvx', '["mcp-server-fetch"]'::jsonb, NULL, FALSE, TRUE, 'MCP Fetch - 网页抓取工具 (无需 Key)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'fetch' AND is_system = TRUE);

-- 2. git (Python, uvx) - Git 仓库操作工具 (官方参考实现, 需调整路径)
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'git', NULL, 'stdio', 'uvx', '["mcp-server-git", "--repository", "/tmp/repo"]'::jsonb, NULL, FALSE, TRUE, 'MCP Git - Git 仓库操作工具 (需调整路径)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'git' AND is_system = TRUE);

-- 3. clickhouse (Python, uvx) - ClickHouse 数据库查询工具
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'clickhouse', NULL, 'stdio', 'uvx', '["mcp-server-clickhouse"]'::jsonb,
    '{"CLICKHOUSE_HOST": "", "CLICKHOUSE_USER": "", "CLICKHOUSE_PASSWORD": ""}'::jsonb,
    FALSE, TRUE, 'MCP ClickHouse - ClickHouse 数据库查询工具 (需配置连接)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'clickhouse' AND is_system = TRUE);

-- 4. confluence (TypeScript, npx) - Confluence 文档协作工具
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'confluence', NULL, 'stdio', 'npx', '["-y", "@modelcontextprotocol/server-confluence"]'::jsonb,
    '{"CONFLUENCE_URL": "", "CONFLUENCE_PERSONAL_TOKEN": ""}'::jsonb,
    FALSE, TRUE, 'MCP Confluence - Confluence 文档协作工具 (需配置 API Token)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'confluence' AND is_system = TRUE);

-- 5. elasticsearch (Python, uvx) - Elasticsearch 搜索引擎工具
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'elasticsearch', NULL, 'stdio', 'uvx', '["mcp-server-elasticsearch"]'::jsonb,
    '{"ELASTICSEARCH_URL": "", "ELASTICSEARCH_API_KEY": ""}'::jsonb,
    FALSE, TRUE, 'MCP Elasticsearch - Elasticsearch 搜索引擎工具 (需配置连接)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'elasticsearch' AND is_system = TRUE);

-- 6. github (TypeScript, npx) - GitHub 仓库管理工具 (官方参考实现)
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'github', NULL, 'stdio', 'npx', '["-y", "@modelcontextprotocol/server-github"]'::jsonb,
    '{"GITHUB_PERSONAL_ACCESS_TOKEN": ""}'::jsonb,
    FALSE, TRUE, 'MCP GitHub - GitHub 仓库管理工具 (需配置 Personal Access Token)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'github' AND is_system = TRUE);

-- 7. google-drive (TypeScript, npx) - Google Drive 文件管理工具
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'google-drive', NULL, 'stdio', 'npx', '["-y", "@modelcontextprotocol/server-google-drive"]'::jsonb,
    '{"GOOGLE_DRIVE_OAUTH_TOKEN": "", "GOOGLE_DRIVE_CLIENT_ID": "", "GOOGLE_DRIVE_CLIENT_SECRET": ""}'::jsonb,
    FALSE, TRUE, 'MCP Google Drive - Google Drive 文件管理工具 (需配置 OAuth 凭据)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'google-drive' AND is_system = TRUE);

-- 8. mongodb (Python, uvx) - MongoDB 数据库工具
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'mongodb', NULL, 'stdio', 'uvx', '["mcp-server-mongodb"]'::jsonb,
    '{"MONGODB_URI": ""}'::jsonb,
    FALSE, TRUE, 'MCP MongoDB - MongoDB 数据库工具 (需配置连接 URI)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'mongodb' AND is_system = TRUE);

-- 9. notion (TypeScript, npx) - Notion 文档协作工具
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'notion', NULL, 'stdio', 'npx', '["-y", "@modelcontextprotocol/server-notion"]'::jsonb,
    '{"NOTION_API_TOKEN": ""}'::jsonb,
    FALSE, TRUE, 'MCP Notion - Notion 文档协作工具 (需配置 API Token)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'notion' AND is_system = TRUE);

-- 10. wikipedia (Python, uvx) - 维基百科查询工具 (无需 Key)
INSERT INTO mcp_configs (agent_id, user_id, name, server_url, transport_type, command, args, env_vars, enabled, is_system, description)
SELECT NULL, NULL, 'wikipedia', NULL, 'stdio', 'uvx', '["mcp-server-wikipedia"]'::jsonb, NULL, FALSE, TRUE, 'MCP Wikipedia - 维基百科查询工具 (无需 Key)'
WHERE NOT EXISTS (SELECT 1 FROM mcp_configs WHERE name = 'wikipedia' AND is_system = TRUE);

-- ========== 初始化完成 ==========
-- 注: 此处不再使用 'agentinsight-docbot' 字面量, agent_id 由各 Agent 在运行时动态写入
-- (旧表兜底的 UPDATE daily_report_usage SET agent_id = 'agentinsight-docbot' 已移除,
--  新部署的 daily_report_usage 表在 agent_id 列有 NOT NULL 约束, 应用层必须显式指定 agent_id)
