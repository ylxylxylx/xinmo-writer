<script setup>
import { ref, onMounted, computed } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost, apiPut, apiDelete } from "../api/index.js"

const props = defineProps({ book: Object })
const route = useRoute()
const config = ref({ api_key: "", base_url: "https://api.deepseek.com", model: "deepseek-chat" })
const defaultStyle = ref(null)
const styleForm = ref(getDefaultStyleForm())
const loadingStyle = ref(false)
const defaultWriterId = ref("")

// ── 写手相关 ──
const allWriters = ref([])
const builtinIds = ref(new Set())
const dialogVisible = ref(false)
const editingWriter = ref(null)
const writerForm = ref(getDefaultWriterForm())

function getDefaultStyleForm() {
  return {
    min_words: 1900, max_words: 2400,
    min_title_words: 10, max_title_words: 20,
    prohibited_words: "", writing_rules: "", behavior_locks: "",
    advanced: {
      natural_dialogue: true, no_useless_details: true,
      max_env_sentences: 3, max_inner_sentences: 3,
    },
  }
}

function getDefaultWriterForm() {
  return {
    name: "", avatar: "✏️", style: "", description: "",
    genres: "", writing_rules: "", behavior_locks: "", prohibited_words: "",
    style_example: "",
    template_author: "",
    natural_dialogue: true, no_useless_details: true,
    max_env_sentences: 3, max_inner_sentences: 3,
  }
}

onMounted(async () => {
  try { config.value = await apiGet("/config") }
  catch { config.value = { api_key: "", base_url: "https://api.deepseek.com", model: "deepseek-chat" } }
  await loadDefaultStyle()
  try {
    const dw = await apiGet("/config/default-writer")
    defaultWriterId.value = dw.writer_id || ""
  } catch {}
  await loadWriters()
})

async function loadWriters() {
  try {
    const list = await apiGet("/writers")
    // 内置写手：从第一个无 custom- 前缀的列表推断
    // 更准确的方式：前端本地 writers.js 的 id 列表硬编码判断
    const builtinPrefixes = ["xiong-mo", "shui-yue", "po-feng", "qiu-shui", "yun-fei", "long-ling", "su-qing", "ye-feng"]
    builtinIds.value = new Set(builtinPrefixes)
    allWriters.value = list
  } catch { allWriters.value = [] }
}

function isBuiltin(w) {
  return builtinIds.value.has(w.id)
}

async function loadDefaultStyle() {
  loadingStyle.value = true
  try {
    const res = await apiGet("/writing-style/default")
    if (res && Object.keys(res).length > 0) {
      defaultStyle.value = res
      styleForm.value = {
        min_words: res.min_words ?? 1900,
        max_words: res.max_words ?? 2400,
        min_title_words: res.min_title_words ?? 10,
        max_title_words: res.max_title_words ?? 20,
        prohibited_words: res.prohibited_words || "",
        writing_rules: res.writing_rules || "",
        behavior_locks: res.behavior_locks || "",
        advanced: {
          natural_dialogue: res.advanced?.natural_dialogue ?? true,
          no_useless_details: res.advanced?.no_useless_details ?? true,
          max_env_sentences: res.advanced?.max_env_sentences ?? 3,
          max_inner_sentences: res.advanced?.max_inner_sentences ?? 3,
        },
      }
    }
  } catch { /* use defaults */ }
  loadingStyle.value = false
}

async function saveConfig() {
  try {
    await apiPost("/config", config.value)
    ElMessage.success("配置保存成功！")
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
}

async function saveDefaultWriter() {
  try {
    await apiPost("/config/default-writer", { writer_id: defaultWriterId.value })
    ElMessage.success("默认写手已保存")
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
}

async function saveDefaultStyle() {
  try {
    await apiPost("/writing-style/default", {
      config: JSON.stringify(styleForm.value),
    })
    ElMessage.success("默认写作风格已保存")
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
}

async function onDefaultWriterChange() {
  if (defaultWriterId.value) {
    const w = allWriters.value.find(w => w.id === defaultWriterId.value)
    if (w) {
      try {
        await ElMessageBox.confirm(`应用写手「${w.name}」的风格到默认写作风格？\n这会覆盖当前的默认写作风格设置。`, "确认", { type: "info" })
      } catch { return }
      styleForm.value = {
        ...styleForm.value,
        writing_rules: styleForm.value.writing_rules
          ? styleForm.value.writing_rules + "\n" + w.config.writing_rules
          : w.config.writing_rules,
        behavior_locks: styleForm.value.behavior_locks
          ? styleForm.value.behavior_locks + "\n" + w.config.behavior_locks
          : w.config.behavior_locks,
        prohibited_words: [styleForm.value.prohibited_words, w.config.prohibited_words].filter(Boolean).join(","),
        advanced: { ...styleForm.value.advanced, ...w.config.advanced },
      }
    }
  }
}

// ── 写手 CRUD ──

function openCreateWriter() {
  editingWriter.value = null
  writerForm.value = getDefaultWriterForm()
  dialogVisible.value = true
}

function openEditWriter(w) {
  editingWriter.value = w
  writerForm.value = {
    name: w.name || "",
    avatar: w.avatar || "✏️",
    style: w.style || "",
    description: w.description || "",
    genres: (w.genres || []).join(", "),
    writing_rules: w.config?.writing_rules || "",
    behavior_locks: w.config?.behavior_locks || "",
    prohibited_words: w.config?.prohibited_words || "",
    style_example: w.style_example || "",
    template_author: w.template_author || "",
    natural_dialogue: w.config?.advanced?.natural_dialogue ?? true,
    no_useless_details: w.config?.advanced?.no_useless_details ?? true,
    max_env_sentences: w.config?.advanced?.max_env_sentences ?? 3,
    max_inner_sentences: w.config?.advanced?.max_inner_sentences ?? 3,
  }
  dialogVisible.value = true
}

function closeDialog() {
  dialogVisible.value = false
  editingWriter.value = null
}

async function saveWriter() {
  const f = writerForm.value
  if (!f.name.trim()) {
    ElMessage.error("请填写写手名称")
    return
  }
  const payload = {
    name: f.name,
    avatar: f.avatar,
    style: f.style,
    description: f.description,
    genres: f.genres,
    writing_rules: f.writing_rules,
    behavior_locks: f.behavior_locks,
    prohibited_words: f.prohibited_words,
    style_example: f.style_example,
    template_author: f.template_author,
    natural_dialogue: String(f.natural_dialogue),
    no_useless_details: String(f.no_useless_details),
    max_env_sentences: f.max_env_sentences,
    max_inner_sentences: f.max_inner_sentences,
  }
  try {
    if (editingWriter.value) {
      await apiPut(`/writers/${editingWriter.value.id}`, payload)
      ElMessage.success("写手已更新")
    } else {
      await apiPost("/writers", payload)
      ElMessage.success("写手已创建")
    }
    closeDialog()
    await loadWriters()
  } catch (e) {
    ElMessage.error("保存失败: " + e.message)
  }
}

async function deleteWriter(w) {
  if (isBuiltin(w)) {
    ElMessage.warning("内置写手不能删除")
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除写手「${w.name}」？此操作不可撤销。`, "删除确认", { type: "warning" })
  } catch { return }
  try {
    await apiDelete(`/writers/${w.id}`)
    ElMessage.success("已删除")
    await loadWriters()
  } catch (e) {
    ElMessage.error("删除失败: " + e.message)
  }
}
</script>

<template>
  <div class="page-header"><h2>设置</h2></div>

  <el-tabs model-value="api" class="settings-tabs">
    <!-- Tab 1: API 配置 -->
    <el-tab-pane label="API 配置" name="api">
      <div class="card">
        <div class="card-header"><h3>LLM API 配置</h3></div>
        <p style="color:var(--text-secondary);margin-bottom:16px;">配置 AI 写作引擎的 API 连接。支持任何 OpenAI 兼容的 API。</p>
        <div class="form-group"><label>API Key *</label><el-input v-model="config.api_key" type="password" placeholder="sk-..." /></div>
        <div class="form-group"><label>API 地址</label><el-input v-model="config.base_url" placeholder="https://api.deepseek.com" /></div>
        <div class="form-group"><label>模型</label><el-input v-model="config.model" placeholder="deepseek-chat" /></div>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </div>

      <div class="card">
        <div class="card-header"><h3>使用说明</h3></div>
        <ol style="padding-left:20px;color:var(--text-secondary);line-height:2;">
          <li>先在<strong>创作蓝图</strong>中填写故事简介、创作意图、世界观</li>
          <li>前往<strong>角色体系</strong>设定主要角色</li>
          <li>规划<strong>分卷大纲</strong>确定故事结构</li>
          <li>在<strong>整文细纲</strong>中逐章规划要写的内容</li>
          <li>可在<strong>设置</strong>中自定义写作风格和管理写手</li>
          <li>最后到<strong>全书正文</strong>点击"写下一章"生成正文</li>
        </ol>
      </div>
    </el-tab-pane>

    <!-- Tab 2: 写作风格设置 -->
    <el-tab-pane label="写作风格设置" name="style">
      <div class="card">
        <div class="card-header"><h3>默认写作风格</h3></div>
        <p style="color:var(--text-secondary);margin-bottom:16px;">所有新书和未自定义的书籍将使用此默认配置。</p>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          <div class="form-group"><label>正文字数下限</label><el-input-number v-model="styleForm.min_words" :min="500" :step="100" /></div>
          <div class="form-group"><label>正文字数上限</label><el-input-number v-model="styleForm.max_words" :min="1000" :step="100" /></div>
          <div class="form-group"><label>标题最少字数</label><el-input-number v-model="styleForm.min_title_words" :min="1" /></div>
          <div class="form-group"><label>标题最多字数</label><el-input-number v-model="styleForm.max_title_words" :min="1" /></div>
        </div>
        <div class="form-group" style="width:100%;max-width:none;">
          <label>禁用词（逗号分隔）</label>
          <el-input v-model="styleForm.prohibited_words" type="textarea" :rows="3" placeholder="仿佛,眼中闪过,嘴角勾起" />
        </div>
        <div class="form-group" style="width:100%;max-width:none;">
          <label>写作规则（每行一条）</label>
          <el-input v-model="styleForm.writing_rules" type="textarea" :rows="8" placeholder="破折号——每章不超过2个..." />
        </div>
        <div class="form-group" style="width:100%;max-width:none;">
          <label>行为锁（每行一条，格式：角色名/约束）</label>
          <el-input v-model="styleForm.behavior_locks" type="textarea" :rows="6" placeholder="主角/不圣母心泛滥" />
        </div>
        <div class="form-group" style="width:100%;max-width:none;">
          <label>高级设置</label>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; padding: 8px 0;">
            <div style="display:flex;flex-direction:column;gap:8px;">
              <el-checkbox v-model="styleForm.advanced.natural_dialogue">自然对话模式</el-checkbox>
              <el-checkbox v-model="styleForm.advanced.no_useless_details">禁用无用细节</el-checkbox>
            </div>
            <div>
              <div class="form-group"><label>环境描写上限</label><el-input-number v-model="styleForm.advanced.max_env_sentences" :min="0" :max="20" size="small" /></div>
              <div class="form-group"><label>内心戏上限</label><el-input-number v-model="styleForm.advanced.max_inner_sentences" :min="0" :max="20" size="small" /></div>
            </div>
          </div>
        </div>
        <el-button type="primary" @click="saveDefaultStyle">保存默认风格</el-button>
      </div>
    </el-tab-pane>

    <!-- Tab 3: 写手设置 -->
    <el-tab-pane label="写手设置" name="writers">
      <div style="margin-bottom:16px;">
        <el-button type="primary" @click="openCreateWriter">+ 新增写手</el-button>
      </div>

      <div class="writer-grid">
        <div
          v-for="w in allWriters"
          :key="w.id"
          class="writer-card"
        >
          <div class="writer-card-actions">
            <el-button size="small" @click="openEditWriter(w)">编辑</el-button>
            <el-button v-if="!isBuiltin(w)" size="small" type="danger" @click="deleteWriter(w)">删除</el-button>
            <el-tag v-else size="small" type="info">内置</el-tag>
          </div>
          <div class="writer-avatar">{{ w.avatar }}</div>
          <div class="writer-info">
            <div class="writer-name">{{ w.name }}</div>
            <div class="writer-style-tag">{{ w.style }}</div>
            <div class="writer-desc">{{ w.description }}</div>
            <div class="writer-genres">
              <el-tag v-for="g in w.genres" :key="g" size="small" type="success" style="font-size:11px;">{{ g }}</el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-tab-pane>
  </el-tabs>

  <!-- 写手编辑弹窗 -->
  <el-dialog
    v-model="dialogVisible"
    :title="editingWriter ? '编辑写手' : '新增写手'"
    width="600px"
    :close-on-click-modal="false"
  >
    <div class="form-group">
      <label>写手名称</label>
      <el-input v-model="writerForm.name" placeholder="如：墨寒" />
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:0 0 120px;">
        <label>头像 emoji</label>
        <el-input v-model="writerForm.avatar" placeholder="🐺" />
      </div>
      <div class="form-group" style="flex:1;">
        <label>风格标签</label>
        <el-input v-model="writerForm.style" placeholder="如：冷峻硬核" />
      </div>
    </div>
    <div class="form-group">
      <label>描述</label>
      <el-input v-model="writerForm.description" type="textarea" :rows="2" placeholder="一句话描述写手的风格特点..." />
    </div>
    <div class="form-group">
      <label>风格范例（正文生成时作为文风参考）</label>
      <el-input v-model="writerForm.style_example" type="textarea" :rows="5" placeholder="一段体现写手文风的示例文字..." />
    </div>
    <div class="form-group">
      <label>参考作家（可选，提示 AI 模仿其文风）</label>
      <el-input v-model="writerForm.template_author" placeholder="如：余华、刘慈欣" />
    </div>
    <div class="form-group">
      <label>擅长题材（逗号分隔）</label>
      <el-input v-model="writerForm.genres" placeholder="末日,废土,科幻,生存" />
    </div>
    <div class="form-group">
      <label>写作规则（每行一条，追加到默认规则之上）</label>
      <el-input v-model="writerForm.writing_rules" type="textarea" :rows="4" placeholder="文风冷峻克制，禁止无意义抒情..." />
    </div>
    <div class="form-group">
      <label>行为锁（每行一条）</label>
      <el-input v-model="writerForm.behavior_locks" type="textarea" :rows="3" placeholder="所有角色/不煽情不矫情" />
    </div>
    <div class="form-group">
      <label>禁用词（逗号分隔）</label>
      <el-input v-model="writerForm.prohibited_words" placeholder="仿佛,眼中闪过" />
    </div>
    <div class="form-group">
      <label>高级设置</label>
      <div style="display:flex;flex-direction:column;gap:8px;padding:8px 0;">
        <el-checkbox v-model="writerForm.natural_dialogue">自然对话模式</el-checkbox>
        <el-checkbox v-model="writerForm.no_useless_details">禁用无用细节</el-checkbox>
        <div style="display:flex;gap:16px;align-items:center;">
          <span style="font-size:13px;color:var(--text-secondary);">环境描写上限</span>
          <el-input-number v-model="writerForm.max_env_sentences" :min="0" :max="20" size="small" />
        </div>
        <div style="display:flex;gap:16px;align-items:center;">
          <span style="font-size:13px;color:var(--text-secondary);">内心戏上限</span>
          <el-input-number v-model="writerForm.max_inner_sentences" :min="0" :max="20" size="small" />
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="closeDialog">取消</el-button>
      <el-button type="primary" @click="saveWriter">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.settings-tabs {
  width: 100%;
}

.settings-tabs :deep(.el-tabs__content) {
  width: 100%;
  padding: 0;
}

.settings-tabs :deep(.el-tab-pane) {
  width: 100%;
}

.settings-tabs .card {
  width: 100%;
  max-width: none;
}

.settings-tabs .form-group {
  width: 100%;
}

.writer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  width: 100%;
}

.writer-card {
  background: var(--bg-card);
  border: 2px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  position: relative;
}

.writer-card:hover {
  border-color: var(--gold-dim);
  background: var(--bg-card-hover);
  transform: translateY(-2px);
}

.writer-card-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
}

.writer-avatar {
  font-size: 48px;
  margin-bottom: 12px;
  line-height: 1;
}

.writer-name {
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  color: var(--gold-text);
  margin-bottom: 6px;
}

.writer-style-tag {
  display: inline-block;
  font-size: 12px;
  color: var(--gold);
  background: var(--gold-glow);
  border: 1px solid var(--gold-dim);
  border-radius: 4px;
  padding: 2px 10px;
  margin-bottom: 10px;
}

.writer-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin-bottom: 12px;
}

.writer-genres {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}
</style>
