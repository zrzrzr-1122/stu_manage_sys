<template>
  <div class="chat-page">
    <aside class="chat-sidebar">
      <div class="sidebar-actions">
        <el-button type="primary" class="w-full" @click="handleNewChat">
          新建对话
        </el-button>
        <el-button class="w-full" @click="settingsVisible = true">API Key 设置</el-button>
      </div>
      <el-scrollbar class="conv-scroll">
        <div
          v-for="item in conversations"
          :key="item.id"
          class="conv-item"
          :class="{ active: item.id === activeId }"
          @click="selectConversation(item.id)"
        >
          <div class="conv-title" :title="item.title">{{ item.title }}</div>
          <div class="conv-meta">
            <span>{{ item.model }}</span>
            <el-button
              link
              type="danger"
              size="small"
              @click.stop="handleDelete(item.id)"
            >
              删除
            </el-button>
          </div>
        </div>
        <el-empty v-if="!conversations.length" description="暂无会话" :image-size="64" />
      </el-scrollbar>
    </aside>

    <section class="chat-main">
      <header class="chat-header">
        <div class="title">{{ activeTitle }}</div>
        <el-select v-model="selectedModel" style="width: 220px" @change="persistModel">
          <el-option
            v-for="m in models"
            :key="m.id"
            :label="m.name"
            :value="m.id"
          />
        </el-select>
      </header>

      <el-scrollbar ref="scrollRef" class="msg-scroll">
        <div class="msg-list">
          <div v-if="!messages.length" class="welcome">
            <h3>AI 助手</h3>
            <p>使用你自己的 DeepSeek API Key，对话数据仅属于当前账号。</p>
          </div>
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="msg-row"
            :class="msg.role"
          >
            <div class="bubble">
              <div class="role">{{ msg.role === "user" ? "我" : "助手" }}</div>
              <div class="content">{{ msg.content }}</div>
            </div>
          </div>
        </div>
      </el-scrollbar>

      <footer class="chat-input">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行"
          @keydown="onKeydown"
        />
        <div class="input-actions">
          <el-tag v-if="!apiKeyConfigured" type="warning">尚未配置 API Key</el-tag>
          <el-button v-if="isGenerating" @click="stopGenerate">停止</el-button>
          <el-button type="primary" :loading="isGenerating" @click="sendMessage">
            发送
          </el-button>
        </div>
      </footer>
    </section>

    <el-dialog v-model="settingsVisible" title="DeepSeek API Key" width="480px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="Key 加密保存在你的账号下，其他用户无法使用。"
        class="mb-3"
      />
      <p v-if="apiKeyMasked" class="masked">当前已配置：{{ apiKeyMasked }}</p>
      <el-input
        v-model="apiKeyInput"
        type="password"
        show-password
        placeholder="sk-..."
        clearable
      />
      <template #footer>
        <el-button v-if="apiKeyConfigured" type="danger" plain @click="removeApiKey">
          移除
        </el-button>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingKey" @click="saveApiKey">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ChatAPI, {
  type ChatConversation,
  type ChatMessage,
  type ChatModel,
} from "@/api/chat";

defineOptions({ name: "ChatIndex" });

const conversations = ref<ChatConversation[]>([]);
const messages = ref<ChatMessage[]>([]);
const models = ref<ChatModel[]>([]);
const activeId = ref<number | null>(null);
const selectedModel = ref(localStorage.getItem("sms_chat_model") || "deepseek-chat");
const inputText = ref("");
const isGenerating = ref(false);
const settingsVisible = ref(false);
const apiKeyConfigured = ref(false);
const apiKeyMasked = ref<string | null>(null);
const apiKeyInput = ref("");
const savingKey = ref(false);
const scrollRef = ref();
let abortController: AbortController | null = null;

const activeTitle = computed(() => {
  const hit = conversations.value.find((c) => c.id === activeId.value);
  return hit?.title || "新对话";
});

function persistModel(model: string) {
  selectedModel.value = model;
  localStorage.setItem("sms_chat_model", model);
  if (activeId.value) {
    ChatAPI.updateConversation(activeId.value, { model }).catch(() => undefined);
  }
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
  const conv = conversations.value.find((c) => c.id === id);
  if (conv?.model) selectedModel.value = conv.model;
  messages.value = await ChatAPI.listMessages(id);
  await scrollToBottom();
}

async function handleNewChat() {
  const conv = await ChatAPI.createConversation({ model: selectedModel.value });
  await loadConversations();
  activeId.value = conv.id;
  messages.value = [];
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm("确认删除该会话？", "提示", { type: "warning" });
  await ChatAPI.deleteConversation(id);
  if (activeId.value === id) {
    activeId.value = null;
    messages.value = [];
  }
  await loadConversations();
}

async function saveApiKey() {
  if (!apiKeyInput.value.trim()) {
    ElMessage.warning("请输入 API Key");
    return;
  }
  savingKey.value = true;
  try {
    const data = await ChatAPI.saveApiKey(apiKeyInput.value.trim());
    apiKeyConfigured.value = !!data.configured;
    apiKeyMasked.value = data.masked || null;
    apiKeyInput.value = "";
    settingsVisible.value = false;
    ElMessage.success("已保存，仅本人可用");
  } finally {
    savingKey.value = false;
  }
}

async function removeApiKey() {
  await ChatAPI.deleteApiKey();
  apiKeyConfigured.value = false;
  apiKeyMasked.value = null;
  ElMessage.success("已移除");
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
  const wrap = scrollRef.value?.wrapRef as HTMLElement | undefined;
  if (wrap) wrap.scrollTop = wrap.scrollHeight;
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || isGenerating.value) return;
  if (!apiKeyConfigured.value) {
    settingsVisible.value = true;
    ElMessage.warning("请先配置自己的 DeepSeek API Key");
    return;
  }

  if (!activeId.value) {
    const conv = await ChatAPI.createConversation({ model: selectedModel.value });
    activeId.value = conv.id;
    await loadConversations();
  }

  messages.value.push({ role: "user", content: text });
  inputText.value = "";
  const assistant: ChatMessage = { role: "assistant", content: "" };
  messages.value.push(assistant);
  isGenerating.value = true;
  abortController = new AbortController();
  await scrollToBottom();

    try {
    await ChatAPI.streamChat(
      {
        messages: messages.value
          .filter((m) => m.content)
          .map((m) => ({ role: m.role, content: m.content })),
        conversation_id: activeId.value,
        model: selectedModel.value,
      },
      (chunk) => {
        assistant.content += chunk;
        scrollToBottom();
      },
      abortController.signal
    );
    await loadConversations();
  } catch (e: any) {
    if (e?.name !== "AbortError") {
      ElMessage.error(e?.message || "生成失败");
      if (!assistant.content) {
        messages.value.pop();
      }
    }
  } finally {
    isGenerating.value = false;
    abortController = null;
  }
}

onMounted(async () => {
  try {
    models.value = await ChatAPI.listModels();
    await refreshApiKey();
    await loadConversations();
  } catch (e: any) {
    ElMessage.error(e?.message || "初始化失败");
  }
});
</script>

<style scoped lang="scss">
.chat-page {
  display: flex;
  height: calc(100vh - 120px);
  min-height: 560px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}

.chat-sidebar {
  width: 280px;
  border-right: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-blank);
}

.sidebar-actions {
  padding: 12px;
  display: grid;
  gap: 8px;
}

.conv-scroll {
  flex: 1;
  padding: 0 8px 12px;
}

.conv-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  &:hover {
    background: var(--el-fill-color-light);
  }
  &.active {
    background: var(--el-color-primary-light-9);
  }
}

.conv-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-meta {
  margin-top: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  height: 56px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-lighter);
  .title {
    font-weight: 600;
  }
}

.msg-scroll {
  flex: 1;
  padding: 16px;
}

.welcome {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 48px 12px;
}

.msg-row {
  display: flex;
  margin-bottom: 14px;
  &.user {
    justify-content: flex-end;
  }
  &.assistant {
    justify-content: flex-start;
  }
}

.bubble {
  max-width: min(720px, 86%);
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--el-fill-color-light);
  .role {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-bottom: 4px;
  }
  .content {
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
  }
}

.msg-row.user .bubble {
  background: var(--el-color-primary-light-8);
}

.chat-input {
  border-top: 1px solid var(--el-border-color-lighter);
  padding: 12px 16px 16px;
}

.input-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.masked {
  margin-bottom: 10px;
  color: var(--el-text-color-secondary);
}

.mb-3 {
  margin-bottom: 12px;
}

.w-full {
  width: 100%;
}
</style>
