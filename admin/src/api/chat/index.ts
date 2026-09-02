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
  created_at?: string;
  updated_at?: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

export interface ApiKeyStatus {
  configured: boolean;
  masked?: string | null;
}

const BASE = "/api/v1/chat";

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
  createConversation(data: { title?: string; model?: string } = {}) {
    return request<any, ChatConversation>({
      url: `${BASE}/conversations`,
      method: "post",
      data,
    });
  },
  updateConversation(id: number, data: { title?: string; model?: string }) {
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
  async streamChat(
    body: {
      messages: ChatMessage[];
      conversation_id?: number | null;
      model: string;
    },
    onChunk: (text: string) => void,
    signal?: AbortSignal
  ) {
    const baseUrl = import.meta.env.VITE_APP_BASE_API || "";
    const token = AuthStorage.getAccessToken();
    const resp = await fetch(`${baseUrl}${BASE}/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
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
          if (json.error) throw new Error(json.error);
          if (json.content) onChunk(json.content);
        } catch (e) {
          if (e instanceof Error && e.message !== "Unexpected end of JSON input") {
            throw e;
          }
        }
      }
    }
  },
};

export default ChatAPI;
