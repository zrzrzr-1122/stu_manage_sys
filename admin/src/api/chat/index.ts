import request from "@/utils/request";
import { AuthStorage } from "@/utils/auth";

export interface ChatModel {
  id: string;
  name: string;
  description: string;
}

export interface ChatConversation {
  id: number;
  title: string;
  model: string;
  system_prompt?: string | null;
  max_tokens?: number | null;
  temperature?: number | null;
  stream_enabled?: boolean;
  thinking_enabled?: boolean;
  markdown_enabled?: boolean;
  memory_pinned?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  thinking_content?: string | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  created_at?: string;
  data_queries?: DataQuerySummary[] | null;
}

export interface DataQuerySummary {
  ok?: boolean | null;
  question?: string | null;
  sql?: string | null;
  row_count?: number | null;
  truncated?: boolean | null;
  metrics?: Record<string, unknown> | null;
  scope_note?: string | null;
  error?: string | null;
  generated?: boolean | null;
  retried?: boolean | null;
  tables?: string[] | null;
  columns?: string[] | null;
  rows?: Record<string, unknown>[] | null;
}

export interface ApiKeyStatus {
  configured: boolean;
  masked?: string | null;
}

export interface ChatUsage {
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
}

export interface LlmLogItem {
  id: number;
  conversation_id?: number | null;
  message_id?: number | null;
  model: string;
  stream: boolean;
  temperature?: number | null;
  max_tokens?: number | null;
  request_preview?: string | null;
  status: string;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  latency_ms?: number | null;
  error_message?: string | null;
  created_at?: string;
}

export interface ChatCompletionParams {
  messages: { role: string; content: string }[];
  conversation_id?: number | null;
  model?: string;
  temperature?: number | null;
  max_tokens?: number | null;
  system_prompt?: string | null;
  stream?: boolean;
  thinking_enabled?: boolean;
}

export type ChatStreamHandlers = {
  onContent?: (text: string) => void;
  onThinking?: (text: string) => void;
  onUsage?: (usage: ChatUsage) => void;
  onDataQueries?: (queries: DataQuerySummary[]) => void;
  onStatus?: (text: string) => void;
  onDone?: (messageId?: number) => void;
};

const BASE = "/api/v1/chat";

async function parseSse(
  resp: Response,
  handlers: ChatStreamHandlers
) {
  if (!resp.ok || !resp.body) {
    throw new Error("流式请求失败");
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trim();
      if (data === "[DONE]") return;
      try {
        const json = JSON.parse(data);
        if (json.type === "error" || json.error) {
          throw new Error(json.error || json.msg || "生成失败");
        }
        if (json.type === "thinking" && json.content) handlers.onThinking?.(json.content);
        else if (json.type === "content" && json.content) handlers.onContent?.(json.content);
        else if (json.type === "status") handlers.onStatus?.(json.content || "");
        else if (json.type === "data_queries" && Array.isArray(json.data_queries)) {
          handlers.onDataQueries?.(json.data_queries);
        }
        else if (json.type === "usage") handlers.onUsage?.(json);
        else if (json.type === "done") handlers.onDone?.(json.message_id);
        else if (json.content && !json.type) handlers.onContent?.(json.content);
      } catch (e) {
        if (e instanceof Error && e.message !== "Unexpected end of JSON input") throw e;
      }
    }
  }
}

const ChatAPI = {
  listModels() {
    return request<any, ChatModel[]>({ url: `${BASE}/models`, method: "get" });
  },
  getApiKeyStatus() {
    return request<any, ApiKeyStatus>({ url: `${BASE}/api-key`, method: "get" });
  },
  saveApiKey(apiKey: string) {
    return request<any, ApiKeyStatus>({
      url: `${BASE}/api-key`,
      method: "put",
      data: { api_key: apiKey },
    });
  },
  deleteApiKey() {
    return request({ url: `${BASE}/api-key`, method: "delete" });
  },
  listConversations() {
    return request<any, ChatConversation[]>({ url: `${BASE}/conversations`, method: "get" });
  },
  createConversation(data: Partial<ChatConversation> = {}) {
    return request<any, ChatConversation>({
      url: `${BASE}/conversations`,
      method: "post",
      data,
    });
  },
  updateConversation(id: number, data: Record<string, unknown>) {
    return request<any, ChatConversation>({
      url: `${BASE}/conversations/${id}`,
      method: "patch",
      data,
    });
  },
  deleteConversation(id: number) {
    return request({ url: `${BASE}/conversations/${id}`, method: "delete" });
  },
  listMessages(id: number) {
    return request<any, ChatMessage[]>({
      url: `${BASE}/conversations/${id}/messages`,
      method: "get",
    });
  },
  listLlmLogs(params: { conversation_id?: number | null; page_num?: number; page_size?: number } = {}) {
    return request<any, { list: LlmLogItem[]; total: number; pageNum: number; pageSize: number }>({
      url: `${BASE}/llm-logs`,
      method: "get",
      params,
    });
  },
  getMemory() {
    return request<any, { pinned: ChatConversation[]; max_pinned: number }>({
      url: `${BASE}/memory`,
      method: "get",
    });
  },
  setMemoryPinned(id: number, memory_pinned: boolean) {
    return request<any, ChatConversation>({
      url: `${BASE}/conversations/${id}`,
      method: "patch",
      data: { memory_pinned },
    });
  },
  async completeChat(body: ChatCompletionParams, signal?: AbortSignal) {
    const baseUrl = import.meta.env.VITE_APP_BASE_API || "";
    const token = AuthStorage.getAccessToken();
    const resp = await fetch(`${baseUrl}${BASE}/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ...body, stream: false }),
      signal,
    });
    const json = await resp.json();
    if (json.code && json.code !== "00000") {
      throw new Error(json.msg || "生成失败");
    }
    return (json.data || json) as {
      content: string;
      thinking?: string;
      usage?: ChatUsage;
      message_id?: number;
      data_queries?: DataQuerySummary[];
    };
  },
  async streamChat(body: ChatCompletionParams, handlers: ChatStreamHandlers, signal?: AbortSignal) {
    const baseUrl = import.meta.env.VITE_APP_BASE_API || "";
    const token = AuthStorage.getAccessToken();
    const resp = await fetch(`${baseUrl}${BASE}/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ...body, stream: true }),
      signal,
    });
    await parseSse(resp, handlers);
  },
};

export default ChatAPI;
