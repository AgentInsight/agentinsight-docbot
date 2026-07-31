# agentinsight-docbot 前端详细设计文档（代码级）

> 版本：v1.1  
> 日期：2026-07-20  
> 配套：[architecture.md](./architecture.md) / [DESIGN_AGENT.md](./DESIGN_AGENT.md)

---

## 0. 文档导读

本文档是 `agentinsight-docbot`（下文简称 **docbot**）前端侧的代码级详细设计文档。核心要点：

1. **独立 frontend 工程**：docbot 自带 `frontend/` 工程在本仓库内独立维护，不依赖任何外部项目。
2. **技术栈**：Next.js 15 + React 19 + Zustand 5 + Tailwind CSS 4 + Vercel AI SDK 4.0 + next-intl。
3. **核心组件**：5 个核心组件（DocbotInput / RepoConfigPanel / ReportTypeSelect / RepoSelect / LanguageSelect）。
4. **API 客户端**：`/v1/repos` CRUD + 测试 + 同步。
5. **多语言**：2 种语言（简体中文 / English）。
6. **文档类型**：8 种（技术架构 / 概要设计 / 需求 / 测试用例 / 系统优化 / 性能分析 / 系统缺陷 / API 文档）。
7. **主框体**：代码仓库下拉 + 报告类型多选 + 语言选择 + 一键生成按钮。
8. **不暴露 MCP 配置**：`mcp-server-git` / `mcp-server-filesystem` 由系统启动时自动注册，前端不提供 MCP 配置面板。

---

## 1. 目录结构

```
agentinsight-docbot/frontend/
├── lib/
│   ├── agents.config.ts          # 单 Agent SSOT 配置（docbot）
│   ├── api-client.ts             # API 客户端（chat + repo API）
│   └── stores/
│       ├── agent-store.ts        # Agent 状态（currentAgent / currentSessionId）
│       └── docbot-store.ts       # docbot Zustand store
├── components/
│   ├── chat/
│   │   ├── chat-input.tsx        # 通用输入框（保留，docbot 不使用）
│   │   ├── docbot-input.tsx      # docbot 主输入框
│   │   ├── report-type-select.tsx # 报告类型多选
│   │   ├── repo-select.tsx       # 代码仓库下拉
│   │   ├── language-select.tsx   # 语言选择
│   │   └── format-select.tsx     # 格式选择
│   ├── settings/
│   │   └── repo-config-panel.tsx # 用户仓库配置面板（不提供 MCP 配置面板）
│   └── nav/
│       └── agent-list-nav.tsx    # Agent 切换器（预留多 Agent 扩展）
├── i18n/
│   ├── zh/
│   │   ├── common.json           # 通用文案
│   │   └── docbot.json           # docbot 专属文案
│   └── en/
│       ├── common.json
│       └── docbot.json
├── app/
│   └── [locale]/
│       ├── (chat)/
│       │   └── page.tsx          # 主对话页（渲染 DocbotInput + 进度消息 + 报告下载）
│       └── settings/
│           └── page.tsx          # 设置页（渲染 RepoConfigPanel）
└── middleware.ts                 # i18n 路由中间件
```

---

## 2. Agent SSOT 配置

### 2.1 `agents.config.ts`

```typescript
// frontend/lib/agents.config.ts
/**
 * Agent 配置 SSOT（Single Source of Truth）。
 *
 * 当前仅包含 docbot 单 Agent，预留多 Agent 扩展位。
 */

export type AgentId = 'agentinsight-docbot';

export type ReportType =
  | 'architecture'
  | 'design'
  | 'requirements'
  | 'testcase'
  | 'optimization'
  | 'performance'
  | 'defect'
  | 'api_doc';

export type ReportFormat = 'markdown' | 'html' | 'pdf' | 'docx' | 'json';
export type Language = 'zh' | 'en';

export interface AgentConfig {
  id: AgentId;
  name: string;
  nameKey: string; // i18n key
  port: number;
  apiBaseUrl: string; // 开发环境代理路径
  inputComponent: 'DocbotInput';
  settingsPanels: string[]; // 设置页要渲染的面板
  supportedFormats?: ReportFormat[];
  supportedLanguages?: Language[];
  supportedReportTypes?: { value: ReportType; labelKey: string }[];
  features: {
    multiAgent: boolean;
    humanReview: boolean; // 固定 false（docbot 不启用人审）
    repoConfig: boolean;  // 固定 true
    reportGeneration: boolean;
    mcpConfig: boolean;   // 固定 false（MCP 系统自带，不暴露配置）
  };
}

export const AGENTS_CONFIG = {
  agents: [
    {
      id: 'agentinsight-docbot',
      name: '技术文档助手',
      nameKey: 'agents.docbot.name',
      port: 8068,
      apiBaseUrl: '/api/docbot',
      inputComponent: 'DocbotInput',
      settingsPanels: ['RepoConfigPanel'], // 不含 MCPConfigPanel
      supportedFormats: ['markdown', 'html', 'pdf', 'docx', 'json'],
      supportedLanguages: ['zh', 'en'],
      supportedReportTypes: [
        { value: 'architecture', labelKey: 'docbot.report_types.architecture' },
        { value: 'design', labelKey: 'docbot.report_types.design' },
        { value: 'requirements', labelKey: 'docbot.report_types.requirements' },
        { value: 'testcase', labelKey: 'docbot.report_types.testcase' },
        { value: 'optimization', labelKey: 'docbot.report_types.optimization' },
        { value: 'performance', labelKey: 'docbot.report_types.performance' },
        { value: 'defect', labelKey: 'docbot.report_types.defect' },
        { value: 'api_doc', labelKey: 'docbot.report_types.api_doc' },
      ],
      features: {
        multiAgent: false,
        humanReview: false,
        repoConfig: true,
        reportGeneration: true,
        mcpConfig: false,
      },
    },
  ] as AgentConfig[],
} as const;

export function getAgentConfig(agentId: AgentId): AgentConfig {
  const agent = AGENTS_CONFIG.agents.find((a) => a.id === agentId);
  if (!agent) throw new Error(`Agent not found: ${agentId}`);
  return agent;
}

export function getDefaultAgent(): AgentConfig {
  return AGENTS_CONFIG.agents[0];
}
```

### 2.2 Agent 切换器（预留多 Agent 扩展位）

```typescript
// frontend/components/nav/agent-list-nav.tsx
'use client';

import { AGENTS_CONFIG, type AgentId } from '@/lib/agents.config';
import { useAgentStore } from '@/lib/stores/agent-store';

export function AgentListNav() {
  const { currentAgent, setCurrentAgent } = useAgentStore();

  return (
    <nav className="flex gap-2 p-2 border-b">
      {AGENTS_CONFIG.agents.map((agent) => (
        <button
          key={agent.id}
          onClick={() => setCurrentAgent(agent.id as AgentId)}
          className={`px-3 py-1 rounded ${
            currentAgent === agent.id ? 'bg-blue-500 text-white' : 'bg-gray-100'
          }`}
        >
          {agent.name}
        </button>
      ))}
    </nav>
  );
}
```

---

## 3. 主输入框组件：`DocbotInput`

### 3.1 组件结构

```typescript
// frontend/components/chat/docbot-input.tsx
'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { RepoSelect } from './repo-select';
import { ReportTypeSelect } from './report-type-select';
import { LanguageSelect } from './language-select';
import { FormatSelect } from './format-select';
import { useDocbotStore } from '@/lib/stores/docbot-store';
import { useAgentStore } from '@/lib/stores/agent-store';
import { apiClient } from '@/lib/api-client';
import type { ReportType, ReportFormat, Language } from '@/lib/agents.config';

export function DocbotInput() {
  const t = useTranslations('docbot');
  const { currentAgent } = useAgentStore();
  const {
    selectedRepoId,
    selectedReportTypes,
    selectedFormat,
    selectedLanguage,
    isGenerating,
    setGenerating,
    addProgressMessage,
  } = useDocbotStore();

  const [error, setError] = useState<string | null>(null);

  const canGenerate =
    selectedRepoId &&
    selectedReportTypes.length > 0 &&
    !isGenerating;

  const handleGenerate = useCallback(async () => {
    if (!canGenerate) return;
    setError(null);
    setGenerating(true);

    try {
      // 构造 OpenAI 兼容请求
      const instruction = {
        action: 'generate_docs',
        repo_id: selectedRepoId,
        report_types: selectedReportTypes,
        report_format: selectedFormat,
        language: selectedLanguage,
      };

      const response = await fetch(`${apiClient.getBaseUrl(currentAgent)}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...apiClient.getAuthHeaders(),
        },
        body: JSON.stringify({
          model: currentAgent,
          messages: [{ role: 'user', content: JSON.stringify(instruction) }],
          stream: true,
          session_id: useAgentStore.getState().currentSessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // SSE 流式解析
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;
            try {
              const event = JSON.parse(data);
              addProgressMessage(event);
            } catch {
              // 忽略解析错误
            }
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'generate_failed');
    } finally {
      setGenerating(false);
    }
  }, [canGenerate, selectedRepoId, selectedReportTypes, selectedFormat, selectedLanguage, currentAgent]);

  return (
    <div className="border-t bg-white p-4 space-y-3">
      {/* 第一行：代码仓库 + 语言 + 格式 */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium mb-1">
            {t('input.select_repo')}
          </label>
          <RepoSelect />
        </div>
        <div className="w-32">
          <label className="block text-sm font-medium mb-1">
            {t('input.select_format')}
          </label>
          <FormatSelect />
        </div>
        <div className="w-32">
          <label className="block text-sm font-medium mb-1">
            {t('input.select_language')}
          </label>
          <LanguageSelect />
        </div>
      </div>

      {/* 第二行：报告类型多选 */}
      <div>
        <label className="block text-sm font-medium mb-1">
          {t('input.select_report_types')}
        </label>
        <ReportTypeSelect />
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="text-red-600 text-sm bg-red-50 p-2 rounded">{error}</div>
      )}

      {/* 一键生成按钮 */}
      <div className="flex justify-end">
        <button
          onClick={handleGenerate}
          disabled={!canGenerate}
          className={`px-6 py-2 rounded-lg font-medium ${
            canGenerate
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isGenerating ? t('input.generating') : t('input.generate')}
        </button>
      </div>
    </div>
  );
}
```

### 3.2 子组件：`RepoSelect`

```typescript
// frontend/components/chat/repo-select.tsx
'use client';

import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react';
import { useDocbotStore } from '@/lib/stores/docbot-store';
import { useAgentStore } from '@/lib/stores/agent-store';
import { apiClient } from '@/lib/api-client';
import type { RepoInfo } from '@/lib/types';

export function RepoSelect() {
  const t = useTranslations('docbot');
  const { currentAgent } = useAgentStore();
  const { selectedRepoId, setSelectedRepoId } = useDocbotStore();
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadRepos = async () => {
      setLoading(true);
      try {
        const data = await apiClient.get<RepoInfo[]>(`${currentAgent}/v1/repos`);
        setRepos(data.filter((r) => r.enabled));
      } catch (e) {
        console.error('Failed to load repos:', e);
      } finally {
        setLoading(false);
      }
    };
    loadRepos();
  }, [currentAgent]);

  if (loading) {
    return <div className="text-sm text-gray-500">{t('input.loading_repos')}</div>;
  }

  if (repos.length === 0) {
    return (
      <div className="text-sm text-amber-600">
        {t('input.no_repos')}{' '}
        <a href="/settings" className="text-blue-600 underline">
          {t('input.go_to_settings')}
        </a>
      </div>
    );
  }

  return (
    <select
      value={selectedRepoId}
      onChange={(e) => setSelectedRepoId(e.target.value)}
      className="w-full border rounded px-2 py-1"
    >
      <option value="">{t('input.select_repo_placeholder')}</option>
      {repos.map((repo) => (
        <option key={repo.id} value={repo.id}>
          {repo.repo_name} ({repo.platform})
        </option>
      ))}
    </select>
  );
}
```

### 3.3 子组件：`ReportTypeSelect`

```typescript
// frontend/components/chat/report-type-select.tsx
'use client';

import { useTranslations } from 'next-intl';
import { useDocbotStore } from '@/lib/stores/docbot-store';
import { useAgentStore } from '@/lib/stores/agent-store';
import { getAgentConfig, type ReportType } from '@/lib/agents.config';

export function ReportTypeSelect() {
  const t = useTranslations('docbot');
  const { currentAgent } = useAgentStore();
  const { selectedReportTypes, setSelectedReportTypes } = useDocbotStore();
  const agentConfig = getAgentConfig(currentAgent);

  if (!agentConfig.supportedReportTypes) return null;

  const toggle = (type: ReportType) => {
    if (selectedReportTypes.includes(type)) {
      setSelectedReportTypes(selectedReportTypes.filter((t) => t !== type));
    } else {
      setSelectedReportTypes([...selectedReportTypes, type]);
    }
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {agentConfig.supportedReportTypes.map((rt) => (
        <label
          key={rt.value}
          className={`flex items-center gap-2 p-2 border rounded cursor-pointer ${
            selectedReportTypes.includes(rt.value)
              ? 'bg-blue-50 border-blue-500'
              : 'hover:bg-gray-50'
          }`}
        >
          <input
            type="checkbox"
            checked={selectedReportTypes.includes(rt.value)}
            onChange={() => toggle(rt.value)}
            className="rounded"
          />
          <span className="text-sm">{t(rt.labelKey.replace('docbot.', ''))}</span>
        </label>
      ))}
    </div>
  );
}
```

### 3.4 子组件：`LanguageSelect` / `FormatSelect`

```typescript
// frontend/components/chat/language-select.tsx
'use client';

import { useDocbotStore } from '@/lib/stores/docbot-store';
import { useAgentStore } from '@/lib/stores/agent-store';
import { getAgentConfig, type Language } from '@/lib/agents.config';

const LANGUAGE_LABELS: Record<Language, string> = {
  zh: '简体中文',
  en: 'English',
};

export function LanguageSelect() {
  const { currentAgent } = useAgentStore();
  const { selectedLanguage, setSelectedLanguage } = useDocbotStore();
  const agentConfig = getAgentConfig(currentAgent);

  if (!agentConfig.supportedLanguages) return null;

  return (
    <select
      value={selectedLanguage}
      onChange={(e) => setSelectedLanguage(e.target.value as Language)}
      className="w-full border rounded px-2 py-1"
    >
      {agentConfig.supportedLanguages.map((lang) => (
        <option key={lang} value={lang}>
          {LANGUAGE_LABELS[lang]}
        </option>
      ))}
    </select>
  );
}
```

```typescript
// frontend/components/chat/format-select.tsx
'use client';

import { useDocbotStore } from '@/lib/stores/docbot-store';
import { useAgentStore } from '@/lib/stores/agent-store';
import { getAgentConfig, type ReportFormat } from '@/lib/agents.config';

const FORMAT_LABELS: Record<ReportFormat, string> = {
  markdown: 'Markdown',
  html: 'HTML',
  pdf: 'PDF',
  docx: 'DOCX',
  json: 'JSON',
};

export function FormatSelect() {
  const { currentAgent } = useAgentStore();
  const { selectedFormat, setSelectedFormat } = useDocbotStore();
  const agentConfig = getAgentConfig(currentAgent);

  if (!agentConfig.supportedFormats) return null;

  return (
    <select
      value={selectedFormat}
      onChange={(e) => setSelectedFormat(e.target.value as ReportFormat)}
      className="w-full border rounded px-2 py-1"
    >
      {agentConfig.supportedFormats.map((fmt) => (
        <option key={fmt} value={fmt}>
          {FORMAT_LABELS[fmt]}
        </option>
      ))}
    </select>
  );
}
```

---

## 4. 用户仓库配置面板：`RepoConfigPanel`

> 注意：本面板是 docbot 设置页**唯一**的配置面板。`mcp-server-git` / `mcp-server-filesystem` 由系统启动时自动注册，所有用户共享，前端不暴露 MCP 配置入口。

### 4.1 主组件

```typescript
// frontend/components/settings/repo-config-panel.tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useAgentStore } from '@/lib/stores/agent-store';
import { apiClient } from '@/lib/api-client';
import type { RepoInfo, RepoCreateRequest, RepoUpdateRequest } from '@/lib/types';
import { RepoForm } from './repo-form';
import { RepoListItem } from './repo-list-item';

export function RepoConfigPanel() {
  const t = useTranslations('docbot');
  const { currentAgent } = useAgentStore();
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingRepo, setEditingRepo] = useState<RepoInfo | null>(null);
  const [showForm, setShowForm] = useState(false);

  const loadRepos = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get<RepoInfo[]>(`${currentAgent}/v1/repos`);
      setRepos(data);
    } catch (e) {
      console.error('Failed to load repos:', e);
    } finally {
      setLoading(false);
    }
  }, [currentAgent]);

  useEffect(() => {
    loadRepos();
  }, [loadRepos]);

  const handleCreate = async (req: RepoCreateRequest) => {
    await apiClient.post(`${currentAgent}/v1/repos`, req);
    setShowForm(false);
    await loadRepos();
  };

  const handleUpdate = async (id: string, req: RepoUpdateRequest) => {
    await apiClient.put(`${currentAgent}/v1/repos/${id}`, req);
    setEditingRepo(null);
    await loadRepos();
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t('settings.confirm_delete'))) return;
    await apiClient.delete(`${currentAgent}/v1/repos/${id}`);
    await loadRepos();
  };

  const handleTest = async (id: string) => {
    const result = await apiClient.post<{ success: boolean; error?: string; branches?: string[] }>(
      `${currentAgent}/v1/repos/${id}/test`
    );
    if (result.success) {
      alert(t('settings.test_success', { branches: result.branches?.join(', ') }));
    } else {
      alert(t('settings.test_failed', { error: result.error }));
    }
  };

  const handleSync = async (id: string) => {
    await apiClient.post(`${currentAgent}/v1/repos/${id}/sync`);
    alert(t('settings.sync_started'));
    await loadRepos();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">{t('settings.repo_config')}</h2>
        <button
          onClick={() => setShowForm(true)}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {t('settings.add_repo')}
        </button>
      </div>

      {loading && <div className="text-gray-500">{t('settings.loading')}</div>}

      {repos.length === 0 && !loading && (
        <div className="text-gray-500 text-center py-8">
          {t('settings.no_repos')}
        </div>
      )}

      {repos.map((repo) => (
        <RepoListItem
          key={repo.id}
          repo={repo}
          onEdit={() => setEditingRepo(repo)}
          onDelete={() => handleDelete(repo.id)}
          onTest={() => handleTest(repo.id)}
          onSync={() => handleSync(repo.id)}
        />
      ))}

      {(showForm || editingRepo) && (
        <RepoForm
          repo={editingRepo}
          onSubmit={editingRepo ? (req) => handleUpdate(editingRepo.id, req) : handleCreate}
          onCancel={() => {
            setShowForm(false);
            setEditingRepo(null);
          }}
        />
      )}
    </div>
  );
}
```

### 4.2 仓库表单组件

```typescript
// frontend/components/settings/repo-form.tsx
'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import type { RepoInfo, RepoCreateRequest, RepoUpdateRequest } from '@/lib/types';

interface RepoFormProps {
  repo: RepoInfo | null;
  onSubmit: (req: RepoCreateRequest | RepoUpdateRequest) => Promise<void>;
  onCancel: () => void;
}

const PLATFORMS = ['github', 'gitlab', 'gitee', 'bitbucket', 'coding', 'gitea', 'custom'];
const AUTH_TYPES = ['none', 'token', 'password', 'ssh_key'];

export function RepoForm({ repo, onSubmit, onCancel }: RepoFormProps) {
  const t = useTranslations('docbot');
  const [formData, setFormData] = useState({
    repo_name: repo?.repo_name || '',
    platform: repo?.platform || 'github',
    repo_url: repo?.repo_url || '',
    auth_type: repo?.auth_type || 'token',
    token: '',
    username: '',
    password: '',
    ssh_key: '',
    ssh_passphrase: '',
    default_branch: repo?.default_branch || 'main',
    clone_depth: repo?.clone_depth ?? 0,
    description: repo?.description || '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(formData);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border rounded p-4 space-y-3 bg-gray-50">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">
            {t('settings.repo_name')} *
          </label>
          <input
            type="text"
            required
            value={formData.repo_name}
            onChange={(e) => setFormData({ ...formData, repo_name: e.target.value })}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            {t('settings.platform')} *
          </label>
          <select
            value={formData.platform}
            onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
            className="w-full border rounded px-2 py-1"
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">
          {t('settings.repo_url')} *
        </label>
        <input
          type="text"
          required
          placeholder="https://github.com/owner/repo.git"
          value={formData.repo_url}
          onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
          className="w-full border rounded px-2 py-1"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">
          {t('settings.auth_type')} *
        </label>
        <select
          value={formData.auth_type}
          onChange={(e) => setFormData({ ...formData, auth_type: e.target.value })}
          className="w-full border rounded px-2 py-1"
        >
          {AUTH_TYPES.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </div>

      {/* 根据认证类型显示不同字段 */}
      {formData.auth_type === 'token' && (
        <div>
          <label className="block text-sm font-medium mb-1">
            {t('settings.token')}
            {repo?.has_token && <span className="text-xs text-gray-500 ml-2">({t('settings.encrypted')})</span>}
          </label>
          <input
            type="password"
            value={formData.token}
            onChange={(e) => setFormData({ ...formData, token: e.target.value })}
            placeholder={repo?.has_token ? t('settings.token_placeholder') : ''}
            className="w-full border rounded px-2 py-1"
          />
        </div>
      )}

      {formData.auth_type === 'password' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1">{t('settings.username')}</label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="w-full border rounded px-2 py-1"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t('settings.password')}</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full border rounded px-2 py-1"
            />
          </div>
        </div>
      )}

      {formData.auth_type === 'ssh_key' && (
        <div>
          <label className="block text-sm font-medium mb-1">{t('settings.ssh_key')}</label>
          <textarea
            value={formData.ssh_key}
            onChange={(e) => setFormData({ ...formData, ssh_key: e.target.value })}
            rows={4}
            placeholder="-----BEGIN OPENSSH PRIVATE KEY-----..."
            className="w-full border rounded px-2 py-1 font-mono text-xs"
          />
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">
            {t('settings.default_branch')}
          </label>
          <input
            type="text"
            value={formData.default_branch}
            onChange={(e) => setFormData({ ...formData, default_branch: e.target.value })}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            {t('settings.clone_depth')}
          </label>
          <input
            type="number"
            min={0}
            value={formData.clone_depth}
            onChange={(e) => setFormData({ ...formData, clone_depth: parseInt(e.target.value) || 0 })}
            className="w-full border rounded px-2 py-1"
          />
          <p className="text-xs text-gray-500 mt-1">{t('settings.clone_depth_hint')}</p>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">{t('settings.description')}</label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={2}
          className="w-full border rounded px-2 py-1"
        />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-1 border rounded hover:bg-gray-100"
        >
          {t('common.cancel')}
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? t('common.saving') : t('common.save')}
        </button>
      </div>
    </form>
  );
}
```

### 4.3 仓库列表项组件

```typescript
// frontend/components/settings/repo-list-item.tsx
'use client';

import { useTranslations } from 'next-intl';
import type { RepoInfo } from '@/lib/types';

interface RepoListItemProps {
  repo: RepoInfo;
  onEdit: () => void;
  onDelete: () => void;
  onTest: () => void;
  onSync: () => void;
}

export function RepoListItem({ repo, onEdit, onDelete, onTest, onSync }: RepoListItemProps) {
  const t = useTranslations('docbot');

  return (
    <div className="border rounded p-3 space-y-2">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-medium">{repo.repo_name}</h3>
          <p className="text-sm text-gray-600">{repo.repo_url}</p>
          <div className="flex gap-3 text-xs text-gray-500 mt-1">
            <span>{t('settings.platform')}: {repo.platform}</span>
            <span>{t('settings.auth_type')}: {repo.auth_type}</span>
            <span>{t('settings.branch')}: {repo.default_branch}</span>
          </div>
        </div>
        <span
          className={`text-xs px-2 py-1 rounded ${
            repo.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {repo.enabled ? t('settings.enabled') : t('settings.disabled')}
        </span>
      </div>

      {repo.last_synced_at && (
        <div className="text-xs text-gray-500">
          {t('settings.last_synced')}: {new Date(repo.last_synced_at).toLocaleString()}
          {repo.last_sync_status && (
            <span className={`ml-2 px-2 py-0.5 rounded ${
              repo.last_sync_status === 'success' ? 'bg-green-100' : 'bg-red-100'
            }`}>
              {repo.last_sync_status}
            </span>
          )}
        </div>
      )}

      <div className="flex gap-2 pt-2 border-t">
        <button
          onClick={onTest}
          className="text-sm px-2 py-1 border rounded hover:bg-gray-50"
        >
          {t('settings.test_connection')}
        </button>
        <button
          onClick={onSync}
          className="text-sm px-2 py-1 border rounded hover:bg-gray-50"
        >
          {t('settings.sync_now')}
        </button>
        <button
          onClick={onEdit}
          className="text-sm px-2 py-1 border rounded hover:bg-gray-50"
        >
          {t('common.edit')}
        </button>
        <button
          onClick={onDelete}
          className="text-sm px-2 py-1 border border-red-300 text-red-600 rounded hover:bg-red-50"
        >
          {t('common.delete')}
        </button>
      </div>
    </div>
  );
}
```

---

## 5. Zustand Store

```typescript
// frontend/lib/stores/docbot-store.ts
/**
 * docbot 专属 Zustand store。
 * 管理用户在 DocbotInput 中选择的参数 + 生成进度消息。
 */
import { create } from 'zustand';
import type { ReportType, ReportFormat, Language } from '@/lib/agents.config';

export interface ProgressMessage {
  id: string;
  type: 'logs' | 'content' | 'node_progress' | 'sources' | 'tool_call' | 'report' | 'error';
  timestamp: string;
  data: unknown;
}

interface DocbotState {
  // 用户选择
  selectedRepoId: string;
  selectedReportTypes: ReportType[];
  selectedFormat: ReportFormat;
  selectedLanguage: Language;

  // 生成状态
  isGenerating: boolean;
  progressMessages: ProgressMessage[];
  finalReports: Array<{
    report_id: string;
    report_type: string;
    title: string;
    summary: string;
    download_urls: Record<string, string>;
    image_svg?: string;
  }>;

  // Actions
  setSelectedRepoId: (id: string) => void;
  setSelectedReportTypes: (types: ReportType[]) => void;
  setSelectedFormat: (fmt: ReportFormat) => void;
  setSelectedLanguage: (lang: Language) => void;
  setGenerating: (generating: boolean) => void;
  addProgressMessage: (msg: ProgressMessage) => void;
  addFinalReport: (report: DocbotState['finalReports'][number]) => void;
  reset: () => void;
}

export const useDocbotStore = create<DocbotState>((set) => ({
  selectedRepoId: '',
  selectedReportTypes: [],
  selectedFormat: 'markdown',
  selectedLanguage: 'zh',

  isGenerating: false,
  progressMessages: [],
  finalReports: [],

  setSelectedRepoId: (id) => set({ selectedRepoId: id }),
  setSelectedReportTypes: (types) => set({ selectedReportTypes: types }),
  setSelectedFormat: (fmt) => set({ selectedFormat: fmt }),
  setSelectedLanguage: (lang) => set({ selectedLanguage: lang }),
  setGenerating: (generating) => set({ isGenerating: generating }),

  addProgressMessage: (msg) =>
    set((state) => ({
      progressMessages: [...state.progressMessages, msg],
    })),

  addFinalReport: (report) =>
    set((state) => ({
      finalReports: [...state.finalReports, report],
    })),

  reset: () =>
    set({
      selectedRepoId: '',
      selectedReportTypes: [],
      progressMessages: [],
      finalReports: [],
      isGenerating: false,
    }),
}));
```

---

## 6. API 客户端

```typescript
// frontend/lib/api-client.ts
/**
 * API 客户端，封装 docbot 后端的所有 HTTP 调用。
 *
 * 调用范围：
 * - /v1/chat/completions（SSE 流式）
 * - /v1/sessions（会话管理）
 * - /v1/reports（报告下载）
 * - /v1/repos（用户代码仓库 CRUD + 测试 + 同步）
 *
 * 注意：本系统不暴露以下端点：
 * - /v1/feedback（POST，人在回路反馈，docbot 不启用人审）
 * - /v1/ws/{session_id}（WebSocket，docbot 仅用 SSE）
 * - /v1/mcp/configs（GET/POST/PUT/DELETE，MCP 系统自带，不暴露配置）
 */
import { AGENTS_CONFIG, type AgentId } from '@/lib/agents.config';

class ApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor() {
    this.baseUrl = typeof window !== 'undefined' ? '' : 'http://localhost:8068';
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  getBaseUrl(agentId: AgentId): string {
    const agent = AGENTS_CONFIG.agents.find((a) => a.id === agentId);
    if (!agent) throw new Error(`Agent not found: ${agentId}`);
    // 开发环境通过 Next.js rewrite 代理到 /api/{agent}
    if (typeof window !== 'undefined') {
      return agent.apiBaseUrl;
    }
    // 服务端直连
    return `http://localhost:${agent.port}`;
  }

  getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};
    if (this.authToken) {
      headers.Authorization = `Bearer ${this.authToken}`;
    }
    return headers;
  }

  async get<T>(path: string): Promise<T> {
    const response = await fetch(this.resolveUrl(path), {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(this.resolveUrl(path), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(this.resolveUrl(path), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async delete(path: string): Promise<void> {
    const response = await fetch(this.resolveUrl(path), {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
  }

  private resolveUrl(path: string): string {
    // path 形如 'agentinsight-docbot/v1/repos'
    const [agentId, ...rest] = path.split('/');
    return `${this.getBaseUrl(agentId as AgentId)}/${rest.join('/')}`;
  }
}

export const apiClient = new ApiClient();
```

---

## 7. 类型定义

```typescript
// frontend/lib/types.ts
/**
 * docbot 前端类型定义。
 */
export interface RepoInfo {
  id: string;
  agent_id: string;
  user_id: string;
  repo_name: string;
  platform: 'github' | 'gitlab' | 'gitee' | 'bitbucket' | 'coding' | 'gitea' | 'custom';
  repo_url: string;
  auth_type: 'none' | 'token' | 'password' | 'ssh_key';
  has_token: boolean;
  has_username: boolean;
  has_password: boolean;
  has_ssh_key: boolean;
  default_branch: string;
  clone_depth: number;
  enabled: boolean;
  last_synced_at: string | null;
  last_sync_status: 'success' | 'failed' | 'pending' | null;
  last_sync_error: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface RepoCreateRequest {
  repo_name: string;
  platform: string;
  repo_url: string;
  auth_type: string;
  token?: string;
  username?: string;
  password?: string;
  ssh_key?: string;
  ssh_passphrase?: string;
  default_branch?: string;
  clone_depth?: number;
  description?: string;
}

export interface RepoUpdateRequest extends Partial<RepoCreateRequest> {
  enabled?: boolean;
}

export interface DocbotReport {
  report_id: string;
  report_type: string;
  title: string;
  summary: string;
  download_urls: Record<string, string>;
  image_svg?: string;
}
```

---

## 8. 主对话页

```typescript
// frontend/app/[locale]/(chat)/page.tsx
'use client';

import { useAgentStore } from '@/lib/stores/agent-store';
import { getAgentConfig } from '@/lib/agents.config';
import { DocbotInput } from '@/components/chat/docbot-input';
import { ProgressMessageList } from '@/components/chat/progress-message-list';
import { useDocbotStore } from '@/lib/stores/docbot-store';

export default function ChatPage() {
  const { currentAgent } = useAgentStore();
  const agentConfig = getAgentConfig(currentAgent);
  const { progressMessages, finalReports } = useDocbotStore();

  return (
    <div className="flex flex-col h-screen">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto">
        <ProgressMessageList messages={progressMessages} />
        {finalReports.length > 0 && (
          <div className="p-4 border-t">
            <h3 className="font-semibold mb-2">生成的文档</h3>
            {finalReports.map((report) => (
              <div key={report.report_id} className="border rounded p-3 mb-2">
                <h4 className="font-medium">{report.title}</h4>
                <p className="text-sm text-gray-600 mt-1">{report.summary}</p>
                <div className="flex gap-2 mt-2">
                  {Object.entries(report.download_urls).map(([fmt, url]) => (
                    <a
                      key={fmt}
                      href={url}
                      className="text-sm px-2 py-1 border rounded hover:bg-blue-50"
                      download
                    >
                      {fmt.toUpperCase()}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 输入区 */}
      {agentConfig.inputComponent === 'DocbotInput' && <DocbotInput />}
    </div>
  );
}
```

### 8.1 进度消息列表组件

```typescript
// frontend/components/chat/progress-message-list.tsx
'use client';

import { useTranslations } from 'next-intl';
import type { ProgressMessage } from '@/lib/stores/docbot-store';

interface ProgressMessageListProps {
  messages: ProgressMessage[];
}

export function ProgressMessageList({ messages }: ProgressMessageListProps) {
  const t = useTranslations('docbot');

  if (messages.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        {t('input.empty_hint')}
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      {messages.map((msg) => (
        <ProgressMessageItem key={msg.id} message={msg} />
      ))}
    </div>
  );
}

function ProgressMessageItem({ message }: { message: ProgressMessage }) {
  const t = useTranslations('docbot');

  switch (message.type) {
    case 'logs':
      return (
        <div className="text-sm text-gray-600 font-mono">
          <span className="text-gray-400">[{message.timestamp}]</span>{' '}
          {String(message.data)}
        </div>
      );
    case 'node_progress':
      return (
        <div className="bg-blue-50 p-2 rounded text-sm">
          <span className="font-medium">{t('progress.node')}:</span>{' '}
          {String(message.data)}
        </div>
      );
    case 'tool_call':
      return (
        <details className="bg-gray-50 p-2 rounded text-sm">
          <summary className="cursor-pointer">
            {t('progress.tool_call')}: {(message.data as { tool_name?: string }).tool_name}
          </summary>
          <pre className="mt-2 text-xs overflow-x-auto">
            {JSON.stringify(message.data, null, 2)}
          </pre>
        </details>
      );
    case 'sources':
      return (
        <details className="bg-gray-50 p-2 rounded text-sm">
          <summary className="cursor-pointer">
            {t('progress.sources')}: {(message.data as unknown[]).length}
          </summary>
          <ul className="mt-2 text-xs space-y-1">
            {(message.data as Array<{ source?: string; score?: number }>).map((s, i) => (
              <li key={i}>{s.source} (score: {s.score})</li>
            ))}
          </ul>
        </details>
      );
    case 'content':
      return (
        <div className="bg-white border rounded p-3 text-sm">
          {String(message.data)}
        </div>
      );
    case 'error':
      return (
        <div className="bg-red-50 border border-red-200 p-2 rounded text-sm text-red-700">
          {t('progress.error')}: {String(message.data)}
        </div>
      );
    default:
      return null;
  }
}
```

---

## 9. 设置页

```typescript
// frontend/app/[locale]/settings/page.tsx
'use client';

import { useAgentStore } from '@/lib/stores/agent-store';
import { getAgentConfig } from '@/lib/agents.config';
import { RepoConfigPanel } from '@/components/settings/repo-config-panel';

const PANEL_COMPONENTS: Record<string, React.ComponentType> = {
  RepoConfigPanel,
  // 注意：不注册 MCPConfigPanel，因为 MCP 服务由系统启动时自动注册
};

export default function SettingsPage() {
  const { currentAgent } = useAgentStore();
  const agentConfig = getAgentConfig(currentAgent);

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold">{agentConfig.name} - Settings</h1>
      {agentConfig.settingsPanels.map((panelName) => {
        const Panel = PANEL_COMPONENTS[panelName];
        return Panel ? <Panel key={panelName} /> : null;
      })}
    </div>
  );
}
```

---

## 10. 多语言资源

仅支持简体中文（`zh`）与 English（`en`）两种语言。

### 10.1 简体中文

```json
// frontend/i18n/zh/docbot.json
{
  "agents": {
    "docbot": {
      "name": "技术文档助手"
    }
  },
  "report_types": {
    "architecture": "技术架构文档",
    "design": "概要设计文档",
    "requirements": "需求文档",
    "testcase": "测试用例文档",
    "optimization": "系统优化文档",
    "performance": "性能分析文档",
    "defect": "系统缺陷文档",
    "api_doc": "API 文档"
  },
  "input": {
    "select_repo": "代码仓库",
    "select_repo_placeholder": "请选择代码仓库",
    "select_report_types": "报告类型（可多选）",
    "select_format": "文档格式",
    "select_language": "语言",
    "generate": "一键生成文档",
    "generating": "正在生成...",
    "loading_repos": "正在加载仓库列表...",
    "no_repos": "尚未配置任何代码仓库",
    "go_to_settings": "前往设置",
    "empty_hint": "选择代码仓库和报告类型，点击一键生成"
  },
  "progress": {
    "node": "节点",
    "tool_call": "工具调用",
    "sources": "检索来源",
    "error": "错误"
  },
  "settings": {
    "repo_config": "代码仓库配置",
    "add_repo": "添加仓库",
    "loading": "加载中...",
    "no_repos": "暂无仓库配置，点击右上角添加",
    "repo_name": "仓库名称",
    "platform": "平台",
    "repo_url": "仓库 URL",
    "auth_type": "认证方式",
    "token": "Token",
    "token_placeholder": "已加密，留空表示不修改",
    "encrypted": "已加密",
    "username": "用户名",
    "password": "密码",
    "ssh_key": "SSH 私钥",
    "default_branch": "默认分支",
    "branch": "分支",
    "clone_depth": "克隆深度",
    "clone_depth_hint": "0=完整克隆，1=浅克隆（推荐）",
    "description": "描述",
    "enabled": "已启用",
    "disabled": "已禁用",
    "last_synced": "最后同步",
    "test_connection": "测试连接",
    "sync_now": "立即同步",
    "test_success": "连接成功，可用分支：{{branches}}",
    "test_failed": "连接失败：{{error}}",
    "sync_started": "同步任务已启动",
    "confirm_delete": "确定要删除此仓库配置吗？"
  }
}
```

### 10.2 English

```json
// frontend/i18n/en/docbot.json
{
  "agents": {
    "docbot": {
      "name": "Tech Docs Assistant"
    }
  },
  "report_types": {
    "architecture": "Technical Architecture Document",
    "design": "High-Level Design Document",
    "requirements": "Requirements Document",
    "testcase": "Test Case Document",
    "optimization": "System Optimization Document",
    "performance": "Performance Analysis Document",
    "defect": "System Defect Document",
    "api_doc": "API Document"
  },
  "input": {
    "select_repo": "Code Repository",
    "select_repo_placeholder": "Select a repository",
    "select_report_types": "Report Types (multi-select)",
    "select_format": "Document Format",
    "select_language": "Language",
    "generate": "Generate Documents",
    "generating": "Generating...",
    "loading_repos": "Loading repositories...",
    "no_repos": "No repositories configured",
    "go_to_settings": "Go to Settings",
    "empty_hint": "Select a repository and report types, then click Generate"
  },
  "progress": {
    "node": "Node",
    "tool_call": "Tool Call",
    "sources": "Sources",
    "error": "Error"
  },
  "settings": {
    "repo_config": "Repository Configuration",
    "add_repo": "Add Repository",
    "loading": "Loading...",
    "no_repos": "No repositories configured. Click Add to create one.",
    "repo_name": "Repository Name",
    "platform": "Platform",
    "repo_url": "Repository URL",
    "auth_type": "Auth Type",
    "token": "Token",
    "token_placeholder": "Encrypted, leave empty to keep",
    "encrypted": "encrypted",
    "username": "Username",
    "password": "Password",
    "ssh_key": "SSH Private Key",
    "default_branch": "Default Branch",
    "branch": "Branch",
    "clone_depth": "Clone Depth",
    "clone_depth_hint": "0=full, 1=shallow (recommended)",
    "description": "Description",
    "enabled": "Enabled",
    "disabled": "Disabled",
    "last_synced": "Last Synced",
    "test_connection": "Test Connection",
    "sync_now": "Sync Now",
    "test_success": "Connection successful. Branches: {{branches}}",
    "test_failed": "Connection failed: {{error}}",
    "sync_started": "Sync task started",
    "confirm_delete": "Delete this repository configuration?"
  }
}
```

---

## 11. Next.js 配置

### 11.1 `next.config.js`

```javascript
// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 开发环境 API 代理到 docbot 后端
  async rewrites() {
    return [
      {
        source: '/api/docbot/:path*',
        destination: 'http://localhost:8068/:path*',
      },
    ];
  },
  // 其他配置（i18n / experimental / webpack 等）按本仓库实际需求设置
};

module.exports = nextConfig;
```

### 11.2 中间件

```typescript
// frontend/middleware.ts
/**
 * i18n 路由中间件，处理 [locale] 前缀解析。
 * 仅支持 'zh' 和 'en' 两种 locale。
 */
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const LOCALES = ['zh', 'en'] as const;
const DEFAULT_LOCALE = 'zh';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const pathnameIsMissingLocale = LOCALES.every(
    (locale) => !pathname.startsWith(`/${locale}/`) && pathname !== `/${locale}`
  );

  if (pathnameIsMissingLocale) {
    const locale = DEFAULT_LOCALE;
    return NextResponse.redirect(
      new URL(`/${locale}${pathname.startsWith('/') ? '' : '/'}${pathname}`, request.url)
    );
  }
}

export const config = {
  matcher: ['/((?!_next|api|.*\\..*).*)'],
};
```

---

## 12. SSE 流式响应处理

### 12.1 进度消息类型映射

```typescript
// frontend/lib/sse-parser.ts
/**
 * SSE 消息解析器，将后端推送的事件解析为 ProgressMessage。
 *
 * docbot 仅通过 SSE 推送进度，不使用 WebSocket（即不暴露 /v1/ws/{session_id}）。
 * 事件类型：logs / content / node_progress / sources / tool_call / report / error
 */
import type { ProgressMessage } from '@/lib/stores/docbot-store';

export function parseSSELine(line: string): ProgressMessage | null {
  if (!line.startsWith('data: ')) return null;
  const data = line.slice(6);
  if (data === '[DONE]') return null;

  try {
    const event = JSON.parse(data);

    // 后端推送的事件类型映射到前端 ProgressMessage.type
    const typeMap: Record<string, ProgressMessage['type']> = {
      logs: 'logs',
      content: 'content',
      node_progress: 'node_progress',
      sources: 'sources',
      tool_call: 'tool_call',
      report: 'report',
      error: 'error',
    };

    return {
      id: event.id || crypto.randomUUID(),
      type: typeMap[event.type] || 'logs',
      timestamp: event.timestamp || new Date().toISOString(),
      data: event.data ?? event,
    };
  } catch {
    return null;
  }
}

export async function* parseSSEStream(
  response: Response
): AsyncGenerator<ProgressMessage> {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const msg = parseSSELine(line);
      if (msg) yield msg;
    }
  }
}
```

### 12.2 Vercel AI SDK 集成

```typescript
// frontend/lib/hooks/use-docbot-generate.ts
/**
 * docbot 一键生成 Hook，封装 SSE 流式处理 + 进度消息分发。
 *
 * 不使用 Vercel AI SDK 的 useChat，因为 docbot 的输入不是自由文本，
 * 而是结构化参数（repo_id + report_types + format + language）。
 */
import { useCallback, useState } from 'react';
import { useAgentStore } from '@/lib/stores/agent-store';
import { useDocbotStore } from '@/lib/stores/docbot-store';
import { apiClient } from '@/lib/api-client';
import { parseSSEStream } from '@/lib/sse-parser';

export function useDocbotGenerate() {
  const { currentAgent, currentSessionId } = useAgentStore();
  const {
    selectedRepoId,
    selectedReportTypes,
    selectedFormat,
    selectedLanguage,
    setGenerating,
    addProgressMessage,
    addFinalReport,
  } = useDocbotStore();
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(async () => {
    if (!selectedRepoId || selectedReportTypes.length === 0) return;

    setGenerating(true);
    setError(null);

    try {
      const instruction = {
        action: 'generate_docs',
        repo_id: selectedRepoId,
        report_types: selectedReportTypes,
        report_format: selectedFormat,
        language: selectedLanguage,
      };

      const response = await fetch(
        `${apiClient.getBaseUrl(currentAgent)}/v1/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...apiClient.getAuthHeaders(),
          },
          body: JSON.stringify({
            model: currentAgent,
            messages: [{ role: 'user', content: JSON.stringify(instruction) }],
            stream: true,
            session_id: currentSessionId,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      // SSE 流式解析
      for await (const msg of parseSSEStream(response)) {
        addProgressMessage(msg);

        // 如果是最终报告，添加到 finalReports
        if (msg.type === 'report' && typeof msg.data === 'object' && msg.data !== null) {
          const report = msg.data as Parameters<typeof addFinalReport>[0];
          addFinalReport(report);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'generate_failed');
    } finally {
      setGenerating(false);
    }
  }, [
    selectedRepoId,
    selectedReportTypes,
    selectedFormat,
    selectedLanguage,
    currentAgent,
    currentSessionId,
    setGenerating,
    addProgressMessage,
    addFinalReport,
  ]);

  return { generate, error };
}
```

---

## 13. 测试页（`static/index.html`）

docbot 后端在 `static/index.html` 提供一个轻量级测试页，用于快速验证 `/v1/chat/completions` 与 `/v1/repos` 端点。测试页固定指向端口 8068 与 `agent_id='agentinsight-docbot'`。

测试页**不包含**以下功能（与后端不暴露的端点一致）：
- 不发起 `POST /v1/feedback`（docbot 不启用人审）
- 不建立 `WS /v1/ws/{session_id}` 连接（docbot 仅用 SSE）
- 不调用 `/v1/mcp/configs` 的任何方法（MCP 系统自带）

---

## 14. 构建与部署

### 14.1 开发模式

```bash
# 启动 docbot 后端
cd agentinsight-docbot
uvicorn server:app --host 0.0.0.0 --port 8068 --reload

# 启动 frontend（本仓库自带）
cd agentinsight-docbot/frontend
npm run dev  # 通过 next.config.js rewrites 代理 /api/docbot/* 到 localhost:8068
```

### 14.2 Docker 构建

docbot 镜像构建（不含 frontend，frontend 由本仓库独立构建）：

```bash
# 生产联网模式
docker compose -p agentinsight-docbot -f docker-compose.yml --env-file .env up -d --build

# QA 模式
docker-build.qa.bat

# 生产离线模式
docker-build.offline.sh
```

---

## 15. 测试用例

### 15.1 单元测试

```typescript
// frontend/__tests__/docbot-input.test.tsx
import { render, screen } from '@testing-library/react';
import { DocbotInput } from '@/components/chat/docbot-input';

// mock next-intl
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// mock store
jest.mock('@/lib/stores/docbot-store', () => ({
  useDocbotStore: () => ({
    selectedRepoId: '',
    selectedReportTypes: [],
    selectedFormat: 'markdown',
    selectedLanguage: 'zh',
    isGenerating: false,
    setGenerating: jest.fn(),
    addProgressMessage: jest.fn(),
  }),
}));

describe('DocbotInput', () => {
  it('renders all form fields', () => {
    render(<DocbotInput />);
    expect(screen.getByText('input.select_repo')).toBeInTheDocument();
    expect(screen.getByText('input.select_report_types')).toBeInTheDocument();
    expect(screen.getByText('input.select_format')).toBeInTheDocument();
    expect(screen.getByText('input.select_language')).toBeInTheDocument();
    expect(screen.getByText('input.generate')).toBeInTheDocument();
  });

  it('disables generate button when no repo selected', () => {
    render(<DocbotInput />);
    const button = screen.getByText('input.generate');
    expect(button).toBeDisabled();
  });
});
```

### 15.2 配置校验测试

```typescript
// frontend/__tests__/agents-config.test.ts
import { AGENTS_CONFIG, getAgentConfig } from '@/lib/agents.config';

describe('agents.config.ts', () => {
  it('only contains docbot agent', () => {
    expect(AGENTS_CONFIG.agents).toHaveLength(1);
    expect(AGENTS_CONFIG.agents[0].id).toBe('agentinsight-docbot');
  });

  it('supports exactly 8 report types', () => {
    const cfg = getAgentConfig('agentinsight-docbot');
    expect(cfg.supportedReportTypes).toHaveLength(8);
    const values = cfg.supportedReportTypes!.map((r) => r.value);
    expect(values).toContain('api_doc');
    expect(values).toEqual(
      expect.arrayContaining([
        'architecture', 'design', 'requirements', 'testcase',
        'optimization', 'performance', 'defect', 'api_doc',
      ])
    );
  });

  it('supports exactly 2 languages (zh / en)', () => {
    const cfg = getAgentConfig('agentinsight-docbot');
    expect(cfg.supportedLanguages).toEqual(['zh', 'en']);
  });

  it('does not register MCPConfigPanel', () => {
    const cfg = getAgentConfig('agentinsight-docbot');
    expect(cfg.settingsPanels).not.toContain('MCPConfigPanel');
    expect(cfg.settingsPanels).toEqual(['RepoConfigPanel']);
    expect(cfg.features.mcpConfig).toBe(false);
  });

  it('disables human review', () => {
    const cfg = getAgentConfig('agentinsight-docbot');
    expect(cfg.features.humanReview).toBe(false);
  });
});
```

### 15.3 e2e 测试

```typescript
// frontend/e2e/docbot.spec.ts
import { test, expect } from '@playwright/test';

test('docbot 一键生成流程', async ({ page }) => {
  // 1. 打开主页
  await page.goto('http://localhost:3000/zh');

  // 2. 进入设置页配置仓库
  await page.click('text=设置');
  await page.click('text=添加仓库');
  await page.fill('[placeholder="仓库 URL"]', 'https://github.com/facebook/react.git');
  await page.fill('[placeholder="仓库名称"]', 'React 测试仓库');
  await page.click('text=保存');

  // 3. 返回主页，选择仓库 + 报告类型
  await page.goBack();
  await page.click('[data-testid="repo-select"]');
  await page.click('text=React 测试仓库');
  await page.click('text=技术架构文档');

  // 4. 点击一键生成
  await page.click('text=一键生成文档');

  // 5. 验证进度消息出现
  await expect(page.locator('text=正在生成...')).toBeVisible();

  // 6. 验证报告下载链接出现
  await expect(page.locator('text=生成的文档')).toBeVisible({ timeout: 300_000 });
  await expect(page.locator('a:has-text("MARKDOWN")')).toBeVisible();
});
```

---

## 16. 设计决策记录

### 16.1 为什么不用 Vercel AI SDK 的 `useChat`？

docbot 的输入是**结构化参数**（repo_id + report_types + format + language），而非自由文本对话。`useChat` 假设输入是 message string，强制使用会破坏参数化语义。因此自定义 `useDocbotGenerate` Hook。

### 16.2 为什么 docbot 不启用人审？

docbot 是文档生成，用户需求明确（选了哪些报告类型就生成哪些），中途人审反而打断流程。如需调整，用户可在生成完成后基于结果重新生成。因此后端不暴露 `/v1/feedback` 端点。

### 16.3 为什么 docbot 不使用 WebSocket？

docbot 仅用 SSE 推送生成进度，不需要双向通信。WebSocket 在单向进度推送场景下增加了复杂度（连接管理 / 心跳 / 重连），收益为零。因此后端不暴露 `/v1/ws/{session_id}` 端点。

### 16.4 为什么前端不提供 MCP 配置面板？

`mcp-server-git` / `mcp-server-filesystem` 是 docbot 系统自带的工具服务，所有用户共享，不需要用户配置，也不存入数据库 `mcp_configs` 表。前端暴露配置入口会让用户误以为是个人配置，反而引起混乱。因此后端不暴露 `/v1/mcp/configs` 端点，前端 `settingsPanels` 不含 `MCPConfigPanel`。

### 16.5 为什么 docbot 用独立 store？

`selectedRepoId` / `progressMessages` / `finalReports` 等 docbot 状态与通用 chat 状态（messages / isStreaming）语义不同，独立 store 边界清晰。

### 16.6 为什么支持语言缩减为 2 种？

docbot 主要面向中文和英文用户，移除日韩语言可降低维护成本，避免无翻译资源时的占位符问题。如未来需要扩展，可在 `agents.config.ts.supportedLanguages` 中追加，并在 `i18n/` 下新增对应目录。

### 16.7 为什么文档类型从 7 种扩展为 8 种？

新增 `api_doc`（API 文档）是因为 API 文档是技术文档体系的核心组成部分，与架构 / 设计 / 测试用例同等重要。对应后端 `DOCBOT_REPORT_PERSONAS.api_doc` persona 与 `docs/API_DOC_OUTLINE.md` 默认大纲。

---

**文档结束**。智能体侧实现详见 [DESIGN_AGENT.md](./DESIGN_AGENT.md)。
