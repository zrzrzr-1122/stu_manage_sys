import axios from "axios";

const chatHttp = axios.create({
  baseURL: "/api/v1/portal/chat",
  timeout: 60000,
});

chatHttp.interceptors.request.use((config) => {
  const token = localStorage.getItem("portal_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

chatHttp.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body && body.code === "00000") return body.data;
    return Promise.reject(new Error(body?.msg || "请求失败"));
  },
  (error) => {
    const msg = error.response?.data?.msg || error.message || "网络异常";
    if (error.response?.status === 401) {
      localStorage.removeItem("portal_token");
      if (location.pathname !== "/login") location.href = "/login";
    }
    return Promise.reject(new Error(msg));
  }
);

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
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  thinking_content?: string | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
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
  model: string;
  stream: boolean;
  status: string;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  latency_ms?: number | null;
  error_message?: string | null;
  request_preview?: string | null;
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
};

async function parseSse(resp: Response, handlers: ChatStreamHandlers) {
  if (!resp.ok || !resp.body) throw new Error("流式请求失败");
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
      const json = JSON.parse(data);
      if (json.type === "error" || json.error) throw new Error(json.error || "生成失败");
      if (json.type === "thinking" && json.content) handlers.onThinking?.(json.content);
      else if (json.type === "content" && json.content) handlers.onContent?.(json.content);
      else if (json.type === "usage") handlers.onUsage?.(json);
      else if (json.content && !json.type) handlers.onContent?.(json.content);
    }
  }
}

export const ChatAPI = {
  listModels: () => chatHttp.get("/models") as Promise<ChatModel[]>,
  getApiKeyStatus: () => chatHttp.get("/api-key") as Promise<ApiKeyStatus>,
  saveApiKey: (api_key: string) => chatHttp.put("/api-key", { api_key }) as Promise<ApiKeyStatus>,
  deleteApiKey: () => chatHttp.delete("/api-key"),
  listConversations: () => chatHttp.get("/conversations") as Promise<ChatConversation[]>,
  createConversation: (data: Record<string, unknown> = {}) =>
    chatHttp.post("/conversations", data) as Promise<ChatConversation>,
  updateConversation: (id: number, data: Record<string, unknown>) =>
    chatHttp.patch(`/conversations/${id}`, data) as Promise<ChatConversation>,
  deleteConversation: (id: number) => chatHttp.delete(`/conversations/${id}`),
  listMessages: (id: number) => chatHttp.get(`/conversations/${id}/messages`) as Promise<ChatMessage[]>,
  listLlmLogs: (params: { conversation_id?: number; page_num?: number; page_size?: number } = {}) =>
    chatHttp.get("/llm-logs", { params }) as Promise<{
      list: LlmLogItem[];
      total: number;
    }>,
  getMemory: () =>
    chatHttp.get("/memory") as Promise<{ pinned: ChatConversation[]; max_pinned: number }>,
  setMemoryPinned: (id: number, memory_pinned: boolean) =>
    chatHttp.patch(`/conversations/${id}`, { memory_pinned }) as Promise<ChatConversation>,
  async completeChat(body: ChatCompletionParams, signal?: AbortSignal) {
    const token = localStorage.getItem("portal_token");
    const resp = await fetch("/api/v1/portal/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ...body, stream: false }),
      signal,
    });
    const json = await resp.json();
    if (json.code && json.code !== "00000") throw new Error(json.msg || "生成失败");
    return json.data as { content: string; thinking?: string; usage?: ChatUsage };
  },
  async streamChat(body: ChatCompletionParams, handlers: ChatStreamHandlers, signal?: AbortSignal) {
    const token = localStorage.getItem("portal_token");
    const resp = await fetch("/api/v1/portal/chat/completions", {
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
