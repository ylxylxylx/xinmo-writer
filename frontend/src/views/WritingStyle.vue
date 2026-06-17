<script setup>
import { ref, onMounted, computed } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const props = defineProps({ bookId: String })
const route = useRoute()

const bookId = computed(() => props.bookId || route.params.bookId)
const isCustom = ref(false)
const defaultConfig = ref({})
const form = ref(getDefaultForm())
const loading = ref(true)

function getDefaultForm() {
  return {
    min_words: 1900,
    max_words: 2400,
    min_title_words: 10,
    max_title_words: 20,
    prohibited_words: "",
    writing_rules: "",
    behavior_locks: "",
    advanced: {
      natural_dialogue: true,
      no_useless_details: true,
      max_env_sentences: 3,
      max_inner_sentences: 3,
    },
  }
}

async function load() {
  loading.value = true
  try {
    const res = await apiGet(`/books/${bookId.value}/writing-style`)
    defaultConfig.value = res.default_config || {}
    isCustom.value = res.is_custom
    const merged = res.merged || {}
    form.value = {
      min_words: merged.min_words ?? 1900,
      max_words: merged.max_words ?? 2400,
      min_title_words: merged.min_title_words ?? 10,
      max_title_words: merged.max_title_words ?? 20,
      prohibited_words: merged.prohibited_words || "",
      writing_rules: merged.writing_rules || "",
      behavior_locks: merged.behavior_locks || "",
      advanced: {
        natural_dialogue: merged.advanced?.natural_dialogue ?? true,
        no_useless_details: merged.advanced?.no_useless_details ?? true,
        max_env_sentences: merged.advanced?.max_env_sentences ?? 3,
        max_inner_sentences: merged.advanced?.max_inner_sentences ?? 3,
      },
    }
  } catch (e) {
    ElMessage.error("加载失败: " + e.message)
  }
  loading.value = false
}

onMounted(load)

async function save() {
  try {
    await apiPost(`/books/${bookId.value}/writing-style`, {
      config: JSON.stringify(form.value),
    })
    isCustom.value = true
    ElMessage.success("写作风格已保存")
  } catch (e) {
    ElMessage.error("保存失败: " + e.message)
  }
}

async function resetToDefault() {
  try {
    await ElMessageBox.confirm("确定恢复为全局默认配置？当前自定义设置将丢失。", "提示", { type: "warning" })
  } catch { return }
  try {
    await apiPost(`/books/${bookId.value}/writing-style/reset`)
    await load()
    ElMessage.success("已恢复全局默认")
  } catch (e) {
    ElMessage.error("重置失败: " + e.message)
  }
}
</script>

<template>
  <div class="page-header">
    <h2>写作风格</h2>
    <div style="display:flex;gap:8px;align-items:center;">
      <el-tag :type="isCustom ? 'success' : 'info'">{{ isCustom ? '已自定义' : '全局默认' }}</el-tag>
    </div>
  </div>

  <div v-if="loading" class="empty-state"><p>加载中...</p></div>

  <template v-else>
    <!-- 区块 1：字数 & 基础约束 -->
    <div class="card">
      <div class="card-header"><h3>字数与基础约束</h3></div>
      <div class="form-row">
        <div class="form-group">
          <label>正文字数下限</label>
          <el-input-number v-model="form.min_words" :min="500" :step="100" />
        </div>
        <div class="form-group">
          <label>正文字数上限</label>
          <el-input-number v-model="form.max_words" :min="1000" :step="100" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>标题最少字数</label>
          <el-input-number v-model="form.min_title_words" :min="1" />
        </div>
        <div class="form-group">
          <label>标题最多字数</label>
          <el-input-number v-model="form.max_title_words" :min="1" />
        </div>
      </div>
    </div>

    <!-- 区块 2：禁用词 -->
    <div class="card">
      <div class="card-header"><h3>禁用词</h3></div>
      <div class="form-group" style="margin-bottom:0;">
        <el-input
          v-model="form.prohibited_words"
          type="textarea"
          :rows="3"
          placeholder="仿佛,眼中闪过,嘴角勾起,不由自主"
        />
        <p class="form-hint">逗号分隔。AI 正文中出现这些词会被标记。</p>
      </div>
    </div>

    <!-- 区块 3：写作规则 -->
    <div class="card">
      <div class="card-header"><h3>写作规则</h3></div>
      <div class="form-group" style="margin-bottom:0;">
        <el-input
          v-model="form.writing_rules"
          type="textarea"
          :rows="6"
          placeholder="破折号——每章不超过2个，普通连接用逗号&#10;这是小说不是剧本，对话后必须穿插动作/环境/心理描写&#10;段落不要过碎，相关动作合为一段"
        />
        <p class="form-hint">每行一条规则，注入 AI 的 system prompt。</p>
      </div>
    </div>

    <!-- 区块 4：行为锁 -->
    <div class="card">
      <div class="card-header"><h3>行为锁</h3></div>
      <div class="form-group" style="margin-bottom:0;">
        <el-input
          v-model="form.behavior_locks"
          type="textarea"
          :rows="5"
          placeholder="主角/不圣母心泛滥，不无底线原谅伤害过自己的人&#10;反派/不突然降智，不强行洗白&#10;所有角色/不讲大道理不说教"
        />
        <p class="form-hint">每行一条，格式：角色名/绝对不能做的事。违反 = OOC，注入 AI prompt 作为硬约束。</p>
      </div>
    </div>

    <!-- 区块 5：高级控制 -->
    <div class="card">
      <div class="card-header"><h3>高级控制</h3></div>
      <div class="checkbox-group">
        <label class="checkbox-label">
          <el-switch v-model="form.advanced.natural_dialogue" />
          <span class="checkbox-text">
            <strong>自然对话</strong>
            <span class="checkbox-desc">口语化，每人不同毛边</span>
          </span>
        </label>
        <label class="checkbox-label">
          <el-switch v-model="form.advanced.no_useless_details" />
          <span class="checkbox-text">
            <strong>禁无用细节</strong>
            <span class="checkbox-desc">环境描写服务情节，不要装饰性描写</span>
          </span>
        </label>
      </div>
      <div class="form-row" style="margin-top:12px;">
        <div class="form-group">
          <label>连续环境描写上限（句）</label>
          <el-input-number v-model="form.advanced.max_env_sentences" :min="1" :max="10" />
        </div>
        <div class="form-group">
          <label>内心戏每页上限（句）</label>
          <el-input-number v-model="form.advanced.max_inner_sentences" :min="1" :max="10" />
        </div>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div style="display:flex;gap:8px;margin-top:20px;">
      <el-button type="primary" @click="save">保存风格设置</el-button>
      <el-button v-if="isCustom" @click="resetToDefault">恢复全局默认</el-button>
    </div>
  </template>
</template>

<style scoped>
.form-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.5;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: border-color 0.15s;
}

.checkbox-label:hover {
  border-color: var(--border-light);
}

.checkbox-label input[type="checkbox"] {
  margin-top: 2px;
  accent-color: var(--gold);
  width: 16px;
  height: 16px;
}

.checkbox-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.checkbox-text strong {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}

.checkbox-desc {
  font-size: 12px;
  color: var(--text-dim);
}
</style>
