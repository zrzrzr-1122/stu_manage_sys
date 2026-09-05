<template>
  <div class="chat-page">
    <aside class="chat-sidebar">
      <div class="sidebar-actions">
        <el-button type="primary" class="w-full" @click="handleNewChat">新建对话</el-button>
        <el-button class="w-full" @click="settingsVisible = true">API Key</el-button>
        <el-button class="w-full" @click="openParams">会话参数</el-button>
        <el-button class="w-full" @click="openMemory">记忆</el-button>
        <el-button class="w-full" @click="openLogs">调用日志</el-button>
      </div>
      <el-scrollbar class="conv-scroll">
        <div
          v-for="item in conversations"
          :key="item.id"
          class="conv-item"
          :class="{ active: item.id === activeId }"
          @click="selectConversation(item.id)"
        >
          <div class="conv-title" :title="`${item.title}（双击重命名）`" @dblclick.stop="handleRename(item)">
            <span class="conv-id">#{{ item.id }}</span>
            {{ item.title }}
          </div>
          <div class="conv-meta">
            <span>{{ item.model }}</span>
            <div class="conv-actions">
              <el-button
                link
                type="primary"
                size="small"
                title="重命名"
                @click.stop="handleRename(item)"
              >
                重命名
              </el-button>
              <el-button
                link
                :type="item.memory_pinned ? 'warning' : 'info'"
                size="small"
                :title="item.memory_pinned ? '取消记忆' : '钉为记忆'"
                @click.stop="togglePin(item)"
              >
                {{ item.memory_pinned ? "★" : "☆" }}
              </el-button>
              <el-button link type="danger" size="small" @click.stop="handleDelete(item.id)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="!conversations.length" description="暂无会话" :image-size="64" />
      </el-scrollbar>
    </aside>

    <section class="chat-main">
      <header class="chat-header">
        <div class="title title-editable" :title="'点击重命名'" @click="renameActive">
          {{ activeTitle }}
          <span class="title-edit-hint">编辑</span>
        </div>
        <div class="header-actions">
          <el-select v-model="selectedModel" style="width: 200px" @change="persistModel">
            <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
          <el-tag v-if="!modelSupportsTools" type="warning" size="small">当前模型无法查库</el-tag>
        </div>
      </header>

      <el-scrollbar ref="scrollRef" class="msg-scroll">
        <div class="msg-list">
          <div v-if="!messages.length" class="welcome">
            <h3>AI 助手</h3>
            <p>支持模型/温度/Max Tokens/System Prompt，Markdown 与 Token 用量展示。</p>
          </div>
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="msg-row"
            :class="msg.role"
          >
            <div class="bubble">
              <div class="role">{{ msg.role === "user" ? "我" : "助手" }}</div>
              <div
                v-if="msg.role === 'assistant' && isGenerating && idx === messages.length - 1 && !msg.content"
                class="content streaming-hint"
              >
                {{ statusHint || "正在生成…" }}
              </div>
              <div
                v-else-if="msg.role === 'assistant' && markdownEnabled"
                class="content md-body"
                v-html="renderMarkdown(msg.content)"
              />
              <div v-else class="content">{{ msg.content }}</div>
              <div
                v-if="msg.role === 'assistant' && msg.data_queries?.length"
                class="data-query-panel"
              >
                <details v-for="(dq, qi) in msg.data_queries" :key="qi" class="dq-item" open>
                  <summary>
                    数据查询
                    <span v-if="dq.ok === false" class="dq-bad">失败</span>
                    <span v-else-if="dq.row_count != null">· {{ dq.row_count }} 行</span>
                  </summary>
                  <p v-if="dq.question" class="dq-q">问：{{ dq.question }}</p>
                  <p v-if="dq.error" class="dq-err">{{ dq.error }}</p>
                  <div v-if="dq.rows?.length" class="dq-table-wrap">
                    <table class="dq-table">
                      <thead>
                        <tr>
                          <th v-for="col in dq.columns || Object.keys(dq.rows[0] || {})" :key="col">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, ri) in dq.rows" :key="ri">
                          <td v-for="col in dq.columns || Object.keys(dq.rows[0] || {})" :key="col">
                            {{ row[col] ?? "" }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <pre v-if="dq.sql" class="dq-sql">{{ dq.sql }}</pre>
                  <div v-if="dq.sql" class="dq-actions">
                    <el-button link type="primary" size="small" @click="copyText(dq.sql!)">复制 SQL</el-button>
                  </div>
                  <p v-if="dq.scope_note" class="dq-note">{{ dq.scope_note }}</p>
                  <p v-if="dq.metrics" class="dq-note">
                    口径：不及格 {{ (dq.metrics as any).fail }}；及格 {{ (dq.metrics as any).pass }}；优秀 {{ (dq.metrics as any).excellent }}
                  </p>
                </details>
              </div>
              <div v-if="msg.role === 'assistant' && msg.total_tokens" class="token-line">
                Tokens: {{ msg.prompt_tokens || 0 }} + {{ msg.completion_tokens || 0 }} = {{ msg.total_tokens }}
              </div>
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
          <el-tag v-if="!streamEnabled" type="info">非流式</el-tag>
          <el-button v-if="isGenerating" @click="stopGenerate">停止</el-button>
          <el-button type="primary" :loading="isGenerating" @click="sendMessage">发送</el-button>
        </div>
      </footer>
    </section>

    <el-dialog v-model="settingsVisible" title="DeepSeek API Key" width="480px">
      <el-alert type="info" :closable="false" show-icon title="Key 加密保存在你的账号下，其他用户无法使用。" class="mb-3" />
      <p v-if="apiKeyMasked" class="masked">当前已配置：{{ apiKeyMasked }}</p>
      <el-input v-model="apiKeyInput" type="password" show-password placeholder="sk-..." clearable />
      <template #footer>
        <el-button v-if="apiKeyConfigured" type="danger" plain @click="removeApiKey">移除</el-button>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingKey" @click="saveApiKey">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="paramsVisible" title="会话参数" size="420px">
      <div class="param-form">
        <div class="param-row">
          <label class="param-label" for="sms-chat-title">会话名称</label>
          <el-input
            id="sms-chat-title"
            v-model="conversationTitle"
            maxlength="200"
            show-word-limit
            placeholder="会话显示名称"
            @change="persistTitle"
          />
        </div>
        <div class="param-row">
          <label class="param-label" for="sms-chat-model">模型</label>
          <el-select id="sms-chat-model" v-model="selectedModel" class="w-full" @change="persistModel">
            <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </div>
        <div class="param-row">
          <label class="param-label" for="sms-chat-max-tokens">Max Tokens</label>
          <el-input-number
            id="sms-chat-max-tokens"
            v-model="maxTokens"
            :min="1"
            :max="8192"
            @change="persistParams"
          />
        </div>
        <div class="param-row">
          <span class="param-label" id="sms-chat-temp-label">Temperature</span>
          <el-slider
            v-model="temperature"
            :min="0"
            :max="2"
            :step="0.1"
            :disabled="selectedModel === 'deepseek-reasoner'"
            aria-labelledby="sms-chat-temp-label"
            @change="persistParams"
          />
          <div v-if="selectedModel === 'deepseek-reasoner'" class="hint">Reasoner 通常忽略 Temperature</div>
        </div>
        <div class="param-row">
          <label class="param-label" for="sms-chat-system-prompt">System Prompt</label>
          <el-input
            id="sms-chat-system-prompt"
            v-model="systemPrompt"
            type="textarea"
            :rows="5"
            maxlength="4000"
            show-word-limit
            @change="persistParams"
          />
        </div>
        <div class="param-row param-row--inline">
          <span class="param-label" id="sms-chat-stream-label">Stream</span>
          <el-switch
            v-model="streamEnabled"
            aria-labelledby="sms-chat-stream-label"
            @change="persistParams"
          />
        </div>
        <div class="param-row param-row--inline">
          <span class="param-label" id="sms-chat-markdown-label">Markdown</span>
          <el-switch
            v-model="markdownEnabled"
            aria-labelledby="sms-chat-markdown-label"
            @change="persistParams"
          />
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="memoryVisible" title="跨会话记忆" width="520px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        :title="`在会话列表点 ★ 钉选（最多 ${memoryMaxPinned} 个）。新建对话会自动引用这些会话的近期内容。`"
        class="mb-3"
      />
      <el-table :data="pinnedList" size="small" empty-text="尚未钉选会话">
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="danger" @click="togglePin(row, false)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button type="primary" @click="memoryVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="logsVisible" title="LLM 调用日志" size="560px">
      <el-table :data="logs" size="small" border v-loading="logsLoading" empty-text="暂无日志">
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column prop="conversation_id" label="会话#" width="80" />
        <el-table-column prop="model" label="模型" width="130" />
        <el-table-column prop="total_tokens" label="Tokens" width="80" />
        <el-table-column prop="latency_ms" label="耗时ms" width="80" />
        <el-table-column prop="status" label="状态" width="70" />
        <el-table-column label="详情" min-width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click="previewLog = row">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="logs-pager">
        <el-pagination
          layout="prev, pager, next"
          :total="logsTotal"
          :page-size="logsPageSize"
          :current-page="logsPage"
          @current-change="(p: number) => { logsPage = p; loadLogs(); }"
        />
      </div>
      <el-dialog v-model="previewVisible" title="请求预览" width="640px" append-to-body>
        <pre class="preview-box">{{ previewLog?.request_preview || previewLog?.error_message || '-' }}</pre>
      </el-dialog>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import MarkdownIt from "markdown-it";
import DOMPurify from "dompurify";
import ChatAPI, {
  type ChatConversation,
  type ChatMessage,
  type ChatModel,
  type DataQuerySummary,
  type LlmLogItem,
} from "@/api/chat";

defineOptions({ name: "ChatIndex" });

const md = new MarkdownIt({ html: false, linkify: true, breaks: true });

const conversations = ref<ChatConversation[]>([]);
const messages = ref<ChatMessage[]>([]);
const models = ref<ChatModel[]>([]);
const activeId = ref<number | null>(null);
const selectedModel = ref(localStorage.getItem("sms_chat_model") || "deepseek-chat");
const conversationTitle = ref("");
const maxTokens = ref(2048);
const temperature = ref(0.7);
const systemPrompt = ref("");
const streamEnabled = ref(true);
const markdownEnabled = ref(true);
const inputText = ref("");
const isGenerating = ref(false);
const statusHint = ref("");
const settingsVisible = ref(false);
const paramsVisible = ref(false);
const memoryVisible = ref(false);
const pinnedList = ref<ChatConversation[]>([]);
const memoryMaxPinned = ref(5);
const logsVisible = ref(false);
const apiKeyConfigured = ref(false);
const apiKeyMasked = ref<string | null>(null);
const apiKeyInput = ref("");
const savingKey = ref(false);
const scrollRef = ref();
const logs = ref<LlmLogItem[]>([]);
const logsTotal = ref(0);
const logsPage = ref(1);
const logsPageSize = 20;
const logsLoading = ref(false);
const previewLog = ref<LlmLogItem | null>(null);
let abortController: AbortController | null = null;

const activeTitle = computed(() => conversations.value.find((c) => c.id === activeId.value)?.title || "新对话");
const modelSupportsTools = computed(() => {
  const m = models.value.find((x) => x.id === selectedModel.value);
  if (m && typeof m.supports_tools === "boolean") return m.supports_tools;
  return selectedModel.value === "deepseek-chat";
});
const previewVisible = computed({
  get: () => !!previewLog.value,
  set: (v: boolean) => {
    if (!v) previewLog.value = null;
  },
});

function renderMarkdown(text: string) {
  return DOMPurify.sanitize(md.render(text || ""));
}

function applyConvSettings(conv?: ChatConversation | null) {
  if (!conv) return;
  conversationTitle.value = conv.title || "";
  if (conv.model) selectedModel.value = conv.model;
  if (conv.max_tokens != null) maxTokens.value = conv.max_tokens;
  if (conv.temperature != null) temperature.value = Number(conv.temperature);
  systemPrompt.value = conv.system_prompt || "";
  streamEnabled.value = conv.stream_enabled !== false;
  markdownEnabled.value = conv.markdown_enabled !== false;
}

async function persistTitle() {
  if (!activeId.value) return;
  const title = conversationTitle.value.trim() || "新对话";
  conversationTitle.value = title;
  try {
    await ChatAPI.updateConversation(activeId.value, { title });
    await loadConversations();
  } catch (e: any) {
    ElMessage.error(e?.message || "重命名失败");
  }
}

async function handleRename(item: ChatConversation) {
  try {
    const { value } = await ElMessageBox.prompt("请输入会话名称", "重命名会话", {
      confirmButtonText: "保存",
      cancelButtonText: "取消",
      inputValue: item.title || "",
      inputPattern: /\S+/,
      inputErrorMessage: "名称不能为空",
      inputValidator: (val) => {
        const t = (val || "").trim();
        if (!t) return "名称不能为空";
        if (t.length > 200) return "最多 200 字";
        return true;
      },
    });
    const title = String(value || "").trim() || "新对话";
    await ChatAPI.updateConversation(item.id, { title });
    if (activeId.value === item.id) conversationTitle.value = title;
    await loadConversations();
    ElMessage.success("已重命名");
  } catch (e: any) {
    if (e === "cancel" || e === "close") return;
    ElMessage.error(e?.message || "重命名失败");
  }
}

async function renameActive() {
  if (!activeId.value) {
    ElMessage.info("请先新建或选择会话");
    return;
  }
  const item = conversations.value.find((c) => c.id === activeId.value);
  if (item) await handleRename(item);
}

async function persistModel(model: string) {
  selectedModel.value = model;
  localStorage.setItem("sms_chat_model", model);
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
    ElMessage.info("请先新建或选择会话");
    return;
  }
  paramsVisible.value = true;
}

async function openMemory() {
  memoryVisible.value = true;
  try {
    const data = await ChatAPI.getMemory();
    pinnedList.value = data?.pinned || [];
    memoryMaxPinned.value = data?.max_pinned || 5;
  } catch (e: any) {
    ElMessage.error(e?.message || "加载记忆失败");
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
    if (memoryVisible.value) {
      const data = await ChatAPI.getMemory();
      pinnedList.value = data?.pinned || [];
      memoryMaxPinned.value = data?.max_pinned || 5;
    }
    ElMessage.success(next ? "已加入跨会话记忆" : "已取消记忆");
  } catch (e: any) {
    ElMessage.error(e?.message || "操作失败");
  }
}

async function openLogs() {
  logsVisible.value = true;
  logsPage.value = 1;
  await loadLogs();
}

async function loadLogs() {
  logsLoading.value = true;
  try {
    const data = await ChatAPI.listLlmLogs({
      conversation_id: activeId.value || undefined,
      page_num: logsPage.value,
      page_size: logsPageSize,
    });
    logs.value = data.list || [];
    logsTotal.value = data.total || 0;
  } finally {
    logsLoading.value = false;
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
  applyConvSettings(conv);
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
  statusHint.value = "";
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制");
  } catch {
    ElMessage.error("复制失败");
  }
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
    await handleNewChat();
  }

  messages.value.push({ role: "user", content: text });
  inputText.value = "";
  messages.value.push({ role: "assistant", content: "" });
  const assistantIdx = messages.value.length - 1;
  const patchAssistant = ( partial: Partial<ChatMessage>) => {
    const cur = messages.value[assistantIdx];
    if (!cur) return;
    messages.value[assistantIdx] = { ...cur, ...partial };
  };
  isGenerating.value = true;
  statusHint.value = "";
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
          onContent: (chunk) => {
            const cur = messages.value[assistantIdx];
            patchAssistant({ content: (cur?.content || "") + chunk });
            scrollToBottom();
          },
          onStatus: (text) => {
            statusHint.value = text;
          },
          onDataQueries: (queries: DataQuerySummary[]) => {
            patchAssistant({ data_queries: queries });
          },
          onUsage: (usage) => {
            patchAssistant({
              prompt_tokens: usage.prompt_tokens,
              completion_tokens: usage.completion_tokens,
              total_tokens: usage.total_tokens,
            });
          },
        },
        abortController.signal
      );
    } else {
      statusHint.value = "正在查询数据…";
      const data = await ChatAPI.completeChat(payload, abortController.signal);
      patchAssistant({
        content: data.content || "",
        prompt_tokens: data.usage?.prompt_tokens,
        completion_tokens: data.usage?.completion_tokens,
        total_tokens: data.usage?.total_tokens,
        data_queries: data.data_queries || null,
      });
    }
    await loadConversations();
    const cur = conversations.value.find((c) => c.id === activeId.value);
    if (cur) conversationTitle.value = cur.title || "";
  } catch (e: any) {
    if (e?.name !== "AbortError") {
      ElMessage.error(e?.message || "生成失败");
      if (!messages.value[assistantIdx]?.content) messages.value.pop();
    }
  } finally {
    isGenerating.value = false;
    statusHint.value = "";
    abortController = null;
  }
}

watch(logsVisible, (v) => {
  if (v) loadLogs();
});

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
.conv-id {
  color: var(--el-text-color-secondary);
  margin-right: 4px;
  font-size: 12px;
}
.conv-meta {
  margin-top: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.conv-actions {
  display: flex;
  align-items: center;
  gap: 2px;
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
  .title-editable {
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    max-width: 50vw;
    &:hover .title-edit-hint {
      opacity: 1;
    }
  }
  .title-edit-hint {
    font-size: 12px;
    font-weight: 400;
    color: var(--el-color-primary);
    opacity: 0.55;
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
.md-body {
  white-space: normal;
  :deep(pre) {
    overflow: auto;
    padding: 8px;
    background: #1e1e1e;
    color: #eee;
    border-radius: 6px;
  }
  :deep(code) {
    font-family: Consolas, monospace;
  }
  :deep(p) {
    margin: 0 0 8px;
  }
}
.streaming-hint {
  color: var(--el-text-color-secondary);
  font-style: italic;
}
.token-line {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.data-query-panel {
  margin-top: 8px;
}
.dq-item {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 6px 8px;
  margin-top: 4px;
}
.dq-item summary {
  cursor: pointer;
  user-select: none;
}
.dq-bad {
  color: var(--el-color-danger);
  margin-left: 4px;
}
.dq-q,
.dq-note,
.dq-err {
  margin: 6px 0 0;
  line-height: 1.4;
}
.dq-err {
  color: var(--el-color-danger);
}
.dq-table-wrap {
  margin-top: 6px;
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background: var(--el-bg-color);
}
.dq-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  color: var(--el-text-color-primary);
}
.dq-table th,
.dq-table td {
  padding: 4px 8px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  text-align: left;
  white-space: nowrap;
}
.dq-table th {
  position: sticky;
  top: 0;
  background: var(--el-fill-color-light);
  font-weight: 600;
}
.dq-sql {
  margin: 6px 0 0;
  padding: 8px;
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--el-bg-color);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--el-text-color-primary);
}
.dq-actions {
  margin-top: 4px;
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
.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.param-form {
  display: grid;
  gap: 16px;
}
.param-row {
  display: grid;
  gap: 8px;
}
.param-row--inline {
  grid-template-columns: 120px 1fr;
  align-items: center;
}
.param-label {
  width: 120px;
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 32px;
}
.param-row--inline .param-label {
  width: auto;
}
.logs-pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.preview-box {
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>
