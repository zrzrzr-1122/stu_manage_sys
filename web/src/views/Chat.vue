<template>
  <div class="chat-wrap">
    <v-row>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <v-btn color="primary" block class="mb-2" @click="handleNewChat">新建对话</v-btn>
            <v-btn variant="outlined" block class="mb-4" @click="settingsOpen = true">
              API Key 设置
            </v-btn>
            <v-list density="compact" nav>
              <v-list-item
                v-for="item in conversations"
                :key="item.id"
                :active="item.id === activeId"
                :title="item.title"
                :subtitle="item.model"
                @click="selectConversation(item.id)"
              >
                <template #append>
                  <v-btn icon="mdi-delete" variant="text" size="small" @click.stop="handleDelete(item.id)" />
                </template>
              </v-list-item>
            </v-list>
            <div v-if="!conversations.length" class="text-medium-emphasis text-center py-4">
              暂无会话
            </div>
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
              <p>使用你自己的 DeepSeek API Key，对话仅属于当前学生账号。</p>
            </div>
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="msg"
              :class="msg.role"
            >
              <div class="bubble">
                <div class="role">{{ msg.role === "user" ? "我" : "助手" }}</div>
                <div class="content">{{ msg.content }}</div>
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
          <v-alert type="info" variant="tonal" class="mb-3">
            Key 加密保存在你的账号下，其他用户无法使用。
          </v-alert>
          <div v-if="apiKeyMasked" class="mb-2 text-medium-emphasis">
            当前已配置：{{ apiKeyMasked }}
          </div>
          <v-text-field
            v-model="apiKeyInput"
            label="API Key"
            type="password"
            autocomplete="off"
          />
        </v-card-text>
        <v-card-actions>
          <v-btn v-if="apiKeyConfigured" color="error" variant="text" @click="removeApiKey">
            移除
          </v-btn>
          <v-spacer />
          <v-btn variant="text" @click="settingsOpen = false">取消</v-btn>
          <v-btn color="primary" :loading="savingKey" @click="saveApiKey">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import {
  ChatAPI,
  type ChatConversation,
  type ChatMessage,
  type ChatModel,
} from "@/api/chat";

const conversations = ref<ChatConversation[]>([]);
const messages = ref<ChatMessage[]>([]);
const models = ref<ChatModel[]>([]);
const activeId = ref<number | null>(null);
const selectedModel = ref(localStorage.getItem("portal_chat_model") || "deepseek-chat");
const inputText = ref("");
const isGenerating = ref(false);
const settingsOpen = ref(false);
const apiKeyConfigured = ref(false);
const apiKeyMasked = ref<string | null>(null);
const apiKeyInput = ref("");
const savingKey = ref(false);
const msgBox = ref<HTMLElement | null>(null);
let abortController: AbortController | null = null;

const activeTitle = computed(() => {
  return conversations.value.find((c) => c.id === activeId.value)?.title || "新对话";
});

function persistModel(model: string) {
  selectedModel.value = model;
  localStorage.setItem("portal_chat_model", model);
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
  if (!confirm("确认删除该会话？")) return;
  await ChatAPI.deleteConversation(id);
  if (activeId.value === id) {
    activeId.value = null;
    messages.value = [];
  }
  await loadConversations();
}

async function saveApiKey() {
  if (!apiKeyInput.value.trim()) {
    alert("请输入 API Key");
    return;
  }
  savingKey.value = true;
  try {
    const data = await ChatAPI.saveApiKey(apiKeyInput.value.trim());
    apiKeyConfigured.value = !!data.configured;
    apiKeyMasked.value = data.masked || null;
    apiKeyInput.value = "";
    settingsOpen.value = false;
  } catch (e: any) {
    alert(e?.message || "保存失败");
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
    alert("请先配置自己的 DeepSeek API Key");
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
        messages: messages.value.filter((m) => m.content).map((m) => ({ role: m.role, content: m.content })),
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
      alert(e?.message || "生成失败");
      if (!assistant.content) messages.value.pop();
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
    alert(e?.message || "初始化失败");
  }
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
  max-height: 52vh;
  overflow: auto;
  padding: 16px;
  background: rgb(var(--v-theme-background));
}
.welcome {
  text-align: center;
  color: rgba(0, 0, 0, 0.55);
  padding: 40px 12px;
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
  padding: 10px 12px;
  border-radius: 10px;
  background: #eee;
}
.msg.user .bubble {
  background: #cfe2ff;
}
.role {
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 4px;
}
.content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}
.actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
}
</style>
