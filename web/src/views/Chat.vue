<template>
  <div class="chat-wrap">
    <v-row>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <v-btn color="primary" block class="mb-2" @click="handleNewChat">新建对话</v-btn>
            <v-btn variant="outlined" block class="mb-2" @click="settingsOpen = true">API Key</v-btn>
            <v-btn variant="outlined" block class="mb-2" @click="openParams">会话参数</v-btn>
            <v-btn variant="outlined" block class="mb-2" @click="openMemory">记忆</v-btn>
            <v-btn variant="outlined" block class="mb-4" @click="openLogs">调用日志</v-btn>
            <v-list density="compact" nav>
              <v-list-item
                v-for="item in conversations"
                :key="item.id"
                :active="item.id === activeId"
                :title="`#${item.id} ${item.title}`"
                :subtitle="item.model"
                @click="selectConversation(item.id)"
              >
                <template #append>
                  <v-btn
                    :icon="item.memory_pinned ? 'mdi-star' : 'mdi-star-outline'"
                    :color="item.memory_pinned ? 'amber' : undefined"
                    variant="text"
                    size="small"
                    :title="item.memory_pinned ? '取消记忆' : '钉为记忆'"
                    @click.stop="togglePin(item)"
                  />
                  <v-btn icon="mdi-delete" variant="text" size="small" @click.stop="handleDelete(item.id)" />
                </template>
              </v-list-item>
            </v-list>
            <div v-if="!conversations.length" class="text-medium-emphasis text-center py-4">暂无会话</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="9">
        <v-card class="chat-main">
          <v-toolbar density="comfortable" color="surface">
            <v-toolbar-title>{{ activeTitle }}</v-toolbar-title>
            <v-spacer />
            <v-select
              v-model="selectedModel"
              :items="models"
              item-title="name"
              item-value="id"
              density="compact"
              hide-details
              style="max-width: 220px"
              @update:model-value="persistModel"
            />
          </v-toolbar>

          <div ref="msgBox" class="msg-box">
            <div v-if="!messages.length" class="welcome">
              <h3>学习助手</h3>
              <p>支持参数配置、Markdown、Token 与调用日志。</p>
            </div>
            <div v-for="(msg, idx) in messages" :key="idx" class="msg" :class="msg.role">
              <div class="bubble">
                <div class="role">{{ msg.role === "user" ? "我" : "助手" }}</div>
                <div
                  v-if="msg.role === 'assistant' && isGenerating && idx === messages.length - 1 && !msg.content"
                  class="content streaming-hint"
                >
                  正在生成…
                </div>
                <div
                  v-else-if="msg.role === 'assistant' && markdownEnabled"
                  class="content md-body"
                  v-html="renderMarkdown(msg.content)"
                />
                <div v-else class="content">{{ msg.content }}</div>
                <div v-if="msg.role === 'assistant' && msg.total_tokens" class="token-line">
                  Tokens: {{ msg.prompt_tokens || 0 }} + {{ msg.completion_tokens || 0 }} = {{ msg.total_tokens }}
                </div>
              </div>
            </div>
          </div>

          <v-card-text>
            <v-textarea
              v-model="inputText"
              rows="3"
              auto-grow
              max-rows="6"
              label="输入消息"
              hide-details
              @keydown="onKeydown"
            />
            <div class="actions">
              <v-chip v-if="!apiKeyConfigured" color="warning" size="small">尚未配置 API Key</v-chip>
              <v-chip v-if="!streamEnabled" color="info" size="small" class="ml-2">非流式</v-chip>
              <v-spacer />
              <v-btn v-if="isGenerating" class="mr-2" @click="stopGenerate">停止</v-btn>
              <v-btn color="primary" :loading="isGenerating" @click="sendMessage">发送</v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="settingsOpen" max-width="480">
      <v-card title="DeepSeek API Key">
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-3">Key 加密保存在你的账号下。</v-alert>
          <div v-if="apiKeyMasked" class="mb-2 text-medium-emphasis">当前已配置：{{ apiKeyMasked }}</div>
          <v-text-field v-model="apiKeyInput" label="API Key" type="password" autocomplete="off" />
        </v-card-text>
        <v-card-actions>
          <v-btn v-if="apiKeyConfigured" color="error" variant="text" @click="removeApiKey">移除</v-btn>
          <v-spacer />
          <v-btn variant="text" @click="settingsOpen = false">取消</v-btn>
          <v-btn color="primary" :loading="savingKey" @click="saveApiKey">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="paramsOpen" max-width="520">
      <v-card title="会话参数">
        <v-card-text>
          <v-select
            id="portal-chat-model"
            v-model="selectedModel"
            :items="models"
            item-title="name"
            item-value="id"
            label="模型"
            class="mb-2"
            @update:model-value="persistModel"
          />
          <v-text-field
            id="portal-chat-max-tokens"
            v-model.number="maxTokens"
            type="number"
            label="Max Tokens"
            class="mb-2"
            @change="persistParams"
          />
          <div class="mb-2">
            <div id="portal-chat-temp-label" class="text-body-2 mb-1">Temperature</div>
            <v-slider
              v-model="temperature"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              :disabled="selectedModel === 'deepseek-reasoner'"
              aria-labelledby="portal-chat-temp-label"
              @end="persistParams"
            />
          </div>
          <v-textarea
            id="portal-chat-system-prompt"
            v-model="systemPrompt"
            label="System Prompt"
            rows="4"
            class="mb-2"
            @change="persistParams"
          />
          <v-switch
            v-model="streamEnabled"
            label="Stream"
            color="primary"
            hide-details
            class="mb-1"
            @update:model-value="persistParams"
          />
          <v-switch
            v-model="markdownEnabled"
            label="Markdown"
            color="primary"
            hide-details
            @update:model-value="persistParams"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="paramsOpen = false">完成</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="memoryOpen" max-width="560">
      <v-card title="跨会话记忆">
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-3">
            在会话列表点星标钉选（最多 {{ memoryMaxPinned }} 个）。新建对话会自动引用这些会话的近期内容。学籍档案仍会自动注入。
          </v-alert>
          <v-list v-if="pinnedList.length" density="compact">
            <v-list-item
              v-for="row in pinnedList"
              :key="row.id"
              :title="`#${row.id} ${row.title}`"
              :subtitle="row.model"
            >
              <template #append>
                <v-btn variant="text" color="error" size="small" @click="togglePin(row, false)">取消</v-btn>
              </template>
            </v-list-item>
          </v-list>
          <div v-else class="text-medium-emphasis text-center py-4">尚未钉选会话</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="memoryOpen = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="logsOpen" max-width="720">
      <v-card title="LLM 调用日志">
        <v-card-text>
          <v-table density="compact">
            <thead>
              <tr>
                <th>时间</th>
                <th>会话#</th>
                <th>模型</th>
                <th>Tokens</th>
                <th>耗时</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in logs" :key="row.id">
                <td>{{ row.created_at }}</td>
                <td>{{ row.conversation_id ?? "-" }}</td>
                <td>{{ row.model }}</td>
                <td>{{ row.total_tokens ?? "-" }}</td>
                <td>{{ row.latency_ms ?? "-" }}</td>
                <td>{{ row.status }}</td>
              </tr>
            </tbody>
          </v-table>
          <div v-if="!logs.length" class="text-medium-emphasis text-center py-4">暂无日志</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="logsOpen = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import MarkdownIt from "markdown-it";
import DOMPurify from "dompurify";
import {
  ChatAPI,
  type ChatConversation,
  type ChatMessage,
  type ChatModel,
  type LlmLogItem,
} from "@/api/chat";

const md = new MarkdownIt({ html: false, linkify: true, breaks: true });

const conversations = ref<ChatConversation[]>([]);
const messages = ref<ChatMessage[]>([]);
const models = ref<ChatModel[]>([]);
const activeId = ref<number | null>(null);
const selectedModel = ref(localStorage.getItem("portal_chat_model") || "deepseek-chat");
const maxTokens = ref(2048);
const temperature = ref(0.7);
const systemPrompt = ref("");
const streamEnabled = ref(true);
const markdownEnabled = ref(true);
const inputText = ref("");
const isGenerating = ref(false);
const settingsOpen = ref(false);
const paramsOpen = ref(false);
const memoryOpen = ref(false);
const pinnedList = ref<ChatConversation[]>([]);
const memoryMaxPinned = ref(5);
const logsOpen = ref(false);
const apiKeyConfigured = ref(false);
const apiKeyMasked = ref<string | null>(null);
const apiKeyInput = ref("");
const savingKey = ref(false);
const msgBox = ref<HTMLElement | null>(null);
const logs = ref<LlmLogItem[]>([]);
let abortController: AbortController | null = null;

const activeTitle = computed(
  () => conversations.value.find((c) => c.id === activeId.value)?.title || "新对话"
);

function renderMarkdown(text: string) {
  return DOMPurify.sanitize(md.render(text || ""));
}

function applyConvSettings(conv?: ChatConversation | null) {
  if (!conv) return;
  if (conv.model) selectedModel.value = conv.model;
  if (conv.max_tokens != null) maxTokens.value = conv.max_tokens;
  if (conv.temperature != null) temperature.value = Number(conv.temperature);
  systemPrompt.value = conv.system_prompt || "";
  streamEnabled.value = conv.stream_enabled !== false;
  markdownEnabled.value = conv.markdown_enabled !== false;
}

async function persistModel(model: string) {
  selectedModel.value = model;
  localStorage.setItem("portal_chat_model", model);
  await persistParams();
}

async function persistParams() {
  if (!activeId.value) return;
  try {
    await ChatAPI.updateConversation(activeId.value, {
      model: selectedModel.value,
      max_tokens: maxTokens.value,
      temperature: temperature.value,
      system_prompt: systemPrompt.value || null,
      clear_system_prompt: !systemPrompt.value,
      stream_enabled: streamEnabled.value,
      thinking_enabled: false,
      markdown_enabled: markdownEnabled.value,
    });
    await loadConversations();
  } catch {
    /* ignore */
  }
}

function openParams() {
  if (!activeId.value) {
    alert("请先新建或选择会话");
    return;
  }
  paramsOpen.value = true;
}

async function openMemory() {
  memoryOpen.value = true;
  try {
    const data = await ChatAPI.getMemory();
    pinnedList.value = data?.pinned || [];
    memoryMaxPinned.value = data?.max_pinned || 5;
  } catch (e: any) {
    alert(e?.message || "加载记忆失败");
  }
}

async function togglePin(item: ChatConversation, force?: boolean) {
  const next = force === undefined ? !item.memory_pinned : force;
  try {
    const updated = await ChatAPI.setMemoryPinned(item.id, next);
    const idx = conversations.value.findIndex((c) => c.id === item.id);
    if (idx >= 0) {
      conversations.value[idx] = { ...conversations.value[idx], memory_pinned: updated.memory_pinned };
    }
    if (memoryOpen.value) {
      const data = await ChatAPI.getMemory();
      pinnedList.value = data?.pinned || [];
      memoryMaxPinned.value = data?.max_pinned || 5;
    }
  } catch (e: any) {
    alert(e?.message || "操作失败");
  }
}

async function openLogs() {
  logsOpen.value = true;
  const data = await ChatAPI.listLlmLogs({
    conversation_id: activeId.value || undefined,
    page_num: 1,
    page_size: 50,
  });
  logs.value = data.list || [];
}

async function refreshApiKey() {
  const data = await ChatAPI.getApiKeyStatus();
  apiKeyConfigured.value = !!data.configured;
  apiKeyMasked.value = data.masked || null;
}

async function loadConversations() {
  conversations.value = await ChatAPI.listConversations();
}

async function selectConversation(id: number) {
  activeId.value = id;
  applyConvSettings(conversations.value.find((c) => c.id === id));
  messages.value = await ChatAPI.listMessages(id);
  await scrollToBottom();
}

async function handleNewChat() {
  const conv = await ChatAPI.createConversation({
    model: selectedModel.value,
    max_tokens: maxTokens.value,
    temperature: temperature.value,
    system_prompt: systemPrompt.value || undefined,
    stream_enabled: streamEnabled.value,
    thinking_enabled: false,
    markdown_enabled: markdownEnabled.value,
  });
  await loadConversations();
  activeId.value = conv.id;
  applyConvSettings(conv);
  messages.value = [];
}

async function handleDelete(id: number) {
  if (!confirm("确认删除该会话？")) return;
  await ChatAPI.deleteConversation(id);
  if (activeId.value === id) {
    activeId.value = null;
    messages.value = [];
  }
  await loadConversations();
}

async function saveApiKey() {
  if (!apiKeyInput.value.trim()) return;
  savingKey.value = true;
  try {
    const data = await ChatAPI.saveApiKey(apiKeyInput.value.trim());
    apiKeyConfigured.value = !!data.configured;
    apiKeyMasked.value = data.masked || null;
    apiKeyInput.value = "";
    settingsOpen.value = false;
  } finally {
    savingKey.value = false;
  }
}

async function removeApiKey() {
  await ChatAPI.deleteApiKey();
  apiKeyConfigured.value = false;
  apiKeyMasked.value = null;
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function stopGenerate() {
  abortController?.abort();
  isGenerating.value = false;
}

async function scrollToBottom() {
  await nextTick();
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight;
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || isGenerating.value) return;
  if (!apiKeyConfigured.value) {
    settingsOpen.value = true;
    return;
  }
  if (!activeId.value) await handleNewChat();

  messages.value.push({ role: "user", content: text });
  inputText.value = "";
  messages.value.push({ role: "assistant", content: "" });
  const assistantIdx = messages.value.length - 1;
  const patchAssistant = (partial: Partial<ChatMessage>) => {
    const cur = messages.value[assistantIdx];
    if (!cur) return;
    messages.value[assistantIdx] = { ...cur, ...partial };
  };
  isGenerating.value = true;
  abortController = new AbortController();
  await scrollToBottom();

  const history = messages.value.slice(0, -1).map((m) => ({ role: m.role, content: m.content }));
  const payload = {
    messages: history,
    conversation_id: activeId.value,
    model: selectedModel.value,
    temperature: temperature.value,
    max_tokens: maxTokens.value,
    system_prompt: systemPrompt.value || null,
    thinking_enabled: false,
  };

  try {
    if (streamEnabled.value) {
      await ChatAPI.streamChat(
        payload,
        {
          onContent: (c) => {
            const cur = messages.value[assistantIdx];
            patchAssistant({ content: (cur?.content || "") + c });
            scrollToBottom();
          },
          onUsage: (u) => {
            patchAssistant({
              prompt_tokens: u.prompt_tokens,
              completion_tokens: u.completion_tokens,
              total_tokens: u.total_tokens,
            });
          },
        },
        abortController.signal
      );
    } else {
      const data = await ChatAPI.completeChat(payload, abortController.signal);
      patchAssistant({
        content: data.content || "",
        prompt_tokens: data.usage?.prompt_tokens,
        completion_tokens: data.usage?.completion_tokens,
        total_tokens: data.usage?.total_tokens,
      });
    }
    await loadConversations();
  } catch (e: any) {
    if (e?.name !== "AbortError" && !messages.value[assistantIdx]?.content) messages.value.pop();
  } finally {
    isGenerating.value = false;
    abortController = null;
  }
}

onMounted(async () => {
  models.value = await ChatAPI.listModels();
  await refreshApiKey();
  await loadConversations();
});
</script>

<style scoped>
.chat-main {
  min-height: 70vh;
  display: flex;
  flex-direction: column;
}
.msg-box {
  flex: 1;
  overflow: auto;
  padding: 16px;
  min-height: 420px;
  background: #fafafa;
}
.welcome {
  text-align: center;
  color: #888;
  padding: 48px 12px;
}
.msg {
  display: flex;
  margin-bottom: 12px;
}
.msg.user {
  justify-content: flex-end;
}
.msg.assistant {
  justify-content: flex-start;
}
.bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #eee;
}
.msg.user .bubble {
  background: #e3f2fd;
}
.role {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}
.content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}
.md-body {
  white-space: normal;
}
.md-body :deep(pre) {
  overflow: auto;
  padding: 8px;
  background: #1e1e1e;
  color: #eee;
  border-radius: 6px;
}
.streaming-hint {
  color: #888;
  font-style: italic;
}
.token-line {
  margin-top: 6px;
  font-size: 12px;
  color: #888;
}
.actions {
  display: flex;
  align-items: center;
  margin-top: 12px;
}
</style>
