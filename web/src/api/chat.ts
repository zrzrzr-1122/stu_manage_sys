import axios from "axios";

const chatHttp = axios.create({
  baseURL: "/api/v1/portal/chat",
  timeout: 60000,
});

chatHttp.interceptors.request.use((config) => {
  const token = localStorage.getItem("portal_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

chatHttp.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body && body.code === "00000") {
      return body.data;
    }
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
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ApiKeyStatus {
  configured: boolean;
  masked?: string | null;
}

export const ChatAPI = {
  listModels: () => chatHttp.get("/models") as Promise<ChatModel[]>,
  getApiKeyStatus: () => chatHttp.get("/api-key") as Promise<ApiKeyStatus>,
  saveApiKey: (api_key: string) =>
    chatHttp.put("/api-key", { api_key }) as Promise<ApiKeyStatus>,
  deleteApiKey: () => chatHttp.delete("/api-key"),
  listConversations: () => chatHttp.get("/conversations") as Promise<ChatConversation[]>,
  createConversation: (data: { title?: string; model?: string } = {}) =>
    chatHttp.post("/conversations", data) as Promise<ChatConversation>,
  updateConversation: (id: number, data: { title?: string; model?: string }) =>
    chatHttp.patch(`/conversations/${id}`, data) as Promise<ChatConversation>,
  deleteConversation: (id: number) => chatHttp.delete(`/conversations/${id}`),
  listMessages: (id: number) => chatHttp.get(`/conversations/${id}/messages`) as Promise<ChatMessage[]>,
  async streamChat(
    body: { messages: ChatMessage[]; conversation_id?: number | null; model: string },
    onChunk: (text: string) => void,
    signal?: AbortSignal
  ) {
    const token = localStorage.getItem("portal_token");
    const resp = await fetch("/api/v1/portal/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
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
        if (json.error) throw new Error(json.error);
        if (json.content) onChunk(json.content);
      }
    }
  },
};
