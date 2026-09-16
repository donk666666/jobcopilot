<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { generateCoverLetter, getCoverLetterHistory, deleteCoverLetter, listResumeMaterials, listJDMaterials, getActiveResume } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

// 从 localStorage 取用户ID（与简历优化页一致）
function getUserId() {
  try { return localStorage.getItem('userId') || 'anonymous' } catch { return 'anonymous' }
}

// ===== 持久化（与 ChatView 一致：切页面不丢） =====
const COVER_KEYS = {
  jd: 'coverJd',
  resume: 'coverResume',
  candidateName: 'coverCandidateName',
  companyName: 'coverCompanyName',
  positionTitle: 'coverPositionTitle',
  style: 'coverStyle',
  recipient: 'coverRecipient',
}
function loadFromStorage(key: string): string {
  try { return localStorage.getItem(key) || '' } catch { return '' }
}
function saveToStorage(key: string, val: string) {
  try { localStorage.setItem(key, val) } catch {}
}

const jdText = ref(loadFromStorage(COVER_KEYS.jd))
const resumeText = ref(loadFromStorage(COVER_KEYS.resume))
const candidateName = ref(loadFromStorage(COVER_KEYS.candidateName))
const companyName = ref(loadFromStorage(COVER_KEYS.companyName))
const positionTitle = ref(loadFromStorage(COVER_KEYS.positionTitle))
const style = ref(loadFromStorage(COVER_KEYS.style) || 'formal')
const recipient = ref(loadFromStorage(COVER_KEYS.recipient) || '招聘负责人')
const loading = ref(false)
const result = ref('')
const error = ref('')
const step = ref(1)

// 简历优化页面 → 求职信页 跨页面共享 last_result
const lastMatchResult = ref<any>(null)
const lastTailored = ref('')

// 自动持久化（用户每改一次就保存）
watch(jdText, v => saveToStorage(COVER_KEYS.jd, v))
watch(resumeText, v => saveToStorage(COVER_KEYS.resume, v))
watch(candidateName, v => saveToStorage(COVER_KEYS.candidateName, v))
watch(companyName, v => saveToStorage(COVER_KEYS.companyName, v))
watch(positionTitle, v => saveToStorage(COVER_KEYS.positionTitle, v))
watch(style, v => saveToStorage(COVER_KEYS.style, v))
watch(recipient, v => saveToStorage(COVER_KEYS.recipient, v))

// 求职信历史
const history = ref<any[]>([])
const historyLoading = ref(false)
const userId = getUserId()

// ===== 素材库弹窗 =====
const materialPicker = ref(false)
const materialType = ref<'resume' | 'jd'>('resume')
const materialList = ref<any[]>([])
const materialLoading = ref(false)

async function openMaterialPicker(type: 'resume' | 'jd') {
  materialType.value = type
  materialPicker.value = true
  materialLoading.value = true
  try {
    if (type === 'resume') {
      materialList.value = ((await listResumeMaterials()) as unknown as any[]) || []
    } else {
      materialList.value = ((await listJDMaterials()) as unknown as any[]) || []
    }
  } catch {
    ElMessage.error('加载素材失败')
  } finally {
    materialLoading.value = false
  }
}

function pickMaterial(m: any) {
  if (materialType.value === 'resume') {
    resumeText.value = m.content
  } else {
    jdText.value = m.content
  }
  materialPicker.value = false
  ElMessage.success(`已填入：${m.title}`)
}

const styleOptions = [
  {
    value: 'formal', label: '专业正式',
    desc: '适合传统企业、金融、咨询，措辞严谨',
    preview: '尊敬的招聘负责人：\n\n感谢您在百忙之中审阅我的求职信...',
    color: '#60a5fa',
  },
  {
    value: 'casual', label: '亲和自然',
    desc: '适合互联网创业公司、创意行业，自然有温度',
    preview: '您好！\n\n看到贵公司的招聘信息，我感到非常激动...',
    color: '#34d399',
  },
  {
    value: 'tech', label: '技术极客',
    desc: '适合纯技术岗位，直击核心能力',
    preview: '申请职位：高级AI工程师\n\n核心竞争力：\n- 5年AI研发经验\n- RAG/Agent落地',
    color: '#f0b90b',
  },
]

function nextStep() {
  if (step.value === 1) {
    if (!jdText.value.trim()) { error.value = '请填写JD文本'; return }
    if (!resumeText.value.trim()) { error.value = '请填写简历'; return }
    step.value = 2; error.value = '';
  }
}

function prevStep() { if (step.value > 1) step.value--; }

function selectStyle(s: string) { style.value = s; }

async function handleGenerate() {
  if (!jdText.value.trim() || !resumeText.value.trim()) {
    error.value = '请填写JD文本和简历'; return
  }
  loading.value = true; error.value = ''; step.value = 3
  try {
    const res: any = await generateCoverLetter({
      jd_text: jdText.value, resume_text: resumeText.value,
      candidate_name: candidateName.value || '求职者',
      style: style.value, recipient: recipient.value,
      user_id: userId,
      company_name: companyName.value || undefined,
      position_title: positionTitle.value || undefined,
    })
    result.value = res.result; step.value = 4
    ElMessage.success(`求职信已生成并保存到历史（#${res.id}）`)
    loadHistory()  // 刷新历史列表
  } catch (e: any) {
    error.value = e.message || '生成失败'; step.value = 4
  }
  finally { loading.value = false }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res: any = await getCoverLetterHistory(userId)
    history.value = res || []
  } catch (e) {
    console.error('加载历史失败:', e)
  } finally {
    historyLoading.value = false
  }
}

async function loadFromHistory(item: any) {
  // 加载到编辑器（可重新生成或编辑）
  candidateName.value = item.candidate_name || ''
  recipient.value = item.recipient || '招聘负责人'
  style.value = item.style || 'formal'
  result.value = item.content
  step.value = 4
  ElMessage.success(`已加载历史记录 #${item.id}`)
}

async function removeHistory(item: any, e?: Event) {
  e?.stopPropagation()
  try {
    await ElMessageBox.confirm(`确定删除 #${item.id} 这份求职信历史？`, '确认删除', { type: 'warning' })
    await deleteCoverLetter(item.id)
    ElMessage.success('已删除')
    loadHistory()
  } catch {}
}

onMounted(() => {
  loadHistory()
  // 读取简历优化页的 A-H 评估结果（如果用户刚跑过）
  try {
    const raw = localStorage.getItem('last_match_result')
    if (raw) lastMatchResult.value = JSON.parse(raw)
    const tailored = localStorage.getItem('last_tailored_resume')
    if (tailored) lastTailored.value = tailored
  } catch {}
  // 如果有上次的简历优化结果，提示用户导入
  if (lastMatchResult.value || lastTailored.value) {
    ElMessage.info('检测到刚才简历优化页的结果，可点"导入上次评估"快速填入')
  }
})

function importLastEval() {
  if (lastMatchResult.value) {
    // block_a_role_summary 是 JD 摘要，可以填到 jdText（如果还没填）
    if (!jdText.value.trim() && lastMatchResult.value.block_a_role_summary) {
      jdText.value = `【岗位摘要】${lastMatchResult.value.block_a_role_summary}\n\n【JD 关键要求】\n` +
        (lastMatchResult.value.block_b_requirements || [])
          .map((r: any) => `- ${r.requirement}（重要性: ${r.importance}）`).join('\n')
      ElMessage.success('已导入 JD 摘要 + Block B 要求列表')
    }
  }
  if (lastTailored.value && !resumeText.value.trim()) {
    resumeText.value = lastTailored.value
    ElMessage.success('已导入上次改写的简历')
  }
  if (!lastMatchResult.value && !lastTailored.value) {
    ElMessage.warning('没有找到上次的评估结果，请先去"简历优化"页跑一次')
  }
}

async function loadFromActiveResume() {
  try {
    const r: any = await getActiveResume()
    if (r?.content) {
      resumeText.value = r.content
      ElMessage.success(`已加载激活简历：${r.name || '默认'}`)
    } else {
      ElMessage.warning('暂未设置激活简历，请先去"简历优化"页保存一份')
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + (e?.message || ''))
  }
}

function copyResult() {
  navigator.clipboard.writeText(result.value)
    .then(() => ElMessage.success('已复制到剪贴板'))
    .catch(() => ElMessage.error('复制失败'))
}

function reset() { step.value = 1; result.value = ''; error.value = ''; }
</script>

<template>
  <div class="cover-page">
    <h2 class="page-title">求职信生成</h2>
    <p class="page-sub">Chain-of-Thought 链式 Prompt：公司需求分析 → 经历匹配 → 求职信生成 · 支持 3 种风格</p>

    <el-row :gutter="20">
      <el-col :span="16">
        <!-- Steps -->
        <div class="steps-bar">
      <div class="step-item">
        <div class="step-dot" :class="{ active: step >= 1, done: step > 1 }">1</div>
        <span class="step-label" :class="{ active: step === 1 }">填写信息</span>
      </div>
      <div class="step-item-center" style="flex: 1"><div class="step-line" :class="{ active: step > 1 }"></div></div>
      <div class="step-item">
        <div class="step-dot" :class="{ active: step >= 2, done: step > 2 }">2</div>
        <span class="step-label" :class="{ active: step === 2 }">选择风格</span>
      </div>
      <div class="step-item-center" style="flex: 1"><div class="step-line" :class="{ active: step > 2 }"></div></div>
      <div class="step-item">
        <div class="step-dot" :class="{ active: step >= 3, done: step > 3 }">3</div>
        <span class="step-label" :class="{ active: step >= 3 }">生成结果</span>
      </div>
    </div>

    <!-- Step 1: Input -->
    <div v-if="step === 1" class="step-content">
      <!-- 跨页面导入 -->
      <div class="import-bar">
        <el-alert
          v-if="lastMatchResult || lastTailored"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        >
          <template #title>
            检测到简历优化页的 A-H 评估结果，可一键导入 JD 摘要 + 改写后的简历
            <el-button type="primary" size="small" link @click="importLastEval" style="margin-left: 12px">
              <el-icon><Download /></el-icon> 导入上次评估
            </el-button>
          </template>
        </el-alert>

        <div class="quick-actions">
          <el-button size="small" plain @click="openMaterialPicker('jd')">
            <el-icon><Files /></el-icon> 从素材库选 JD
          </el-button>
          <el-button size="small" plain @click="openMaterialPicker('resume')">
            <el-icon><Files /></el-icon> 从素材库选简历
          </el-button>
          <el-button size="small" plain @click="loadFromActiveResume">
            <el-icon><Document /></el-icon> 加载当前激活简历
          </el-button>
        </div>
      </div>

      <div class="input-cards">
        <div class="cv-input-card">
          <h4>职位描述 <span class="field-hint">（必填）</span></h4>
          <el-input v-model="jdText" type="textarea" :rows="6" placeholder="粘贴目标职位 JD 文本…" />
        </div>
        <div class="cv-input-card">
          <h4>你的简历 <span class="field-hint">（必填）</span></h4>
          <el-input v-model="resumeText" type="textarea" :rows="8" placeholder="粘贴你的简历文本…" />
        </div>
        <div class="cv-input-card">
          <h4>补充信息（可选）</h4>
          <el-input v-model="candidateName" placeholder="你的姓名" style="margin-bottom: 12px" />
          <el-input v-model="companyName" placeholder="公司名称（让求职信更针对）" style="margin-bottom: 12px" />
          <el-input v-model="positionTitle" placeholder="岗位名称（JD 里的职位名）" style="margin-bottom: 12px" />
          <el-input v-model="recipient" placeholder="收信人称呼" />
        </div>
      </div>
      <div class="step-footer">
        <el-button type="primary" size="large" @click="nextStep">
          下一步：选择风格 <el-icon><Right /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- Step 2: Style -->
    <div v-if="step === 2" class="step-content">
      <div class="tone-cards">
        <div
          v-for="opt in styleOptions" :key="opt.value"
          class="tone-card"
          :class="{ selected: style === opt.value }"
          :style="{ '--strip-color': opt.color }"
          @click="selectStyle(opt.value)"
        >
          <div class="tone-strip"></div>
          <div class="tone-body">
            <h3 class="tone-label">{{ opt.label }}</h3>
            <p class="tone-desc">{{ opt.desc }}</p>
            <pre class="tone-preview">{{ opt.preview }}</pre>
          </div>
          <div v-if="style === opt.value" class="tone-check">
            <el-icon :size="20" color="var(--accent)"><Check /></el-icon>
          </div>
        </div>
      </div>
      <div class="step-footer">
        <el-button size="large" @click="prevStep"><el-icon><Left /></el-icon> 返回修改</el-button>
        <el-button type="primary" size="large" @click="handleGenerate" :loading="loading" class="generate-btn">
          <el-icon><MagicStick /></el-icon> 生成求职信
        </el-button>
      </div>
    </div>

    <!-- Step 3: Generating -->
    <div v-if="step === 3" class="step-content">
      <div class="generating-card">
        <div class="gen-dots">
          <span class="gen-dot" style="animation-delay: 0s"></span>
          <span class="gen-dot" style="animation-delay: 0.2s"></span>
          <span class="gen-dot" style="animation-delay: 0.4s"></span>
        </div>
        <h3>AI 正在为你撰写求职信...</h3>
        <p style="color: var(--text-muted); font-size: 13px">分析公司需求 → 匹配个人经历 → 生成个性化内容</p>
      </div>
    </div>

    <!-- Step 4: Result -->
    <div v-if="step === 4" class="step-content">
      <div v-if="result" class="result-area">
        <div class="letter-paper"><pre>{{ result }}</pre></div>
        <div class="result-toolbar">
          <el-button type="primary" plain @click="copyResult"><el-icon><CopyDocument /></el-icon> 复制全文</el-button>
          <el-button @click="reset"><el-icon><RefreshLeft /></el-icon> 重新生成</el-button>
        </div>
      </div>
      <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
    </div>
    </el-col>

      <el-col :span="8">
          <div class="history-sidebar">
            <div class="history-header">
              <h4>求职信历史 <el-tag size="small" type="info">{{ history.length }}</el-tag></h4>
              <el-button size="small" text @click="loadHistory" :loading="historyLoading">刷新</el-button>
            </div>
            <div v-if="historyLoading && history.length === 0" class="history-empty">加载中...</div>
            <div v-else-if="history.length === 0" class="history-empty">暂无历史，每次生成的求职信都会自动保存到这里</div>
            <div v-else class="history-list">
              <div
                v-for="item in history"
                :key="item.id"
                class="history-item"
                @click="loadFromHistory(item)"
              >
                <div class="hi-top">
                  <span class="hi-id">#{{ item.id }}</span>
                  <span class="hi-style" :class="item.style">{{ item.style }}</span>
                  <span class="hi-del" @click="removeHistory(item, $event)" title="删除">×</span>
                </div>
                <div class="hi-title">
                  <span v-if="item.company_name || item.position_title">
                    {{ item.company_name }}{{ item.company_name && item.position_title ? ' · ' : '' }}{{ item.position_title }}
                  </span>
                  <span v-else style="color: var(--text-muted)">无公司/职位</span>
                </div>
                <div class="hi-meta">
                  <span>{{ item.candidate_name }}</span>
                  <span>{{ item.created_at?.slice(0, 16) }}</span>
                </div>
                <div class="hi-preview">{{ item.content?.slice(0, 60) }}...</div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

    <!-- 素材库选择弹窗 -->
    <el-dialog v-model="materialPicker" :title="materialType === 'resume' ? '选择简历素材' : '选择 JD 素材'" width="640px">
      <div v-if="materialLoading" class="picker-loading">加载中…</div>
      <div v-else-if="!materialList.length" class="picker-empty">素材库是空的，先去素材库添加吧</div>
      <div v-else class="picker-list">
        <div v-for="m in materialList" :key="m.id" class="picker-item" @click="pickMaterial(m)">
          <el-icon :size="20" style="color: var(--accent)">
            <component :is="materialType === 'resume' ? 'Document' : 'Files'" />
          </el-icon>
          <div class="picker-body">
            <div class="picker-title">
              {{ m.title }}
              <span v-if="materialType === 'resume' && m.is_active" class="picker-tag">激活</span>
              <span v-if="materialType === 'jd' && m.company_name" class="picker-tag">{{ m.company_name }}</span>
            </div>
            <div class="picker-preview">{{ m.content.slice(0, 80) }}{{ m.content.length > 80 ? '…' : '' }}</div>
          </div>
          <el-icon class="picker-arrow"><Right /></el-icon>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.cover-page { max-width: 640px; margin: 0 auto; }
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

/* Steps */
.steps-bar { display: flex; align-items: flex-start; justify-content: space-between; margin: 28px 0 32px; min-height: 60px; }
.step-item { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.step-item-center { flex: 1; display: flex; align-items: center; justify-content: center; padding-top: 18px; }
.step-line { width: 100%; height: 2px; background: var(--border-input); transition: background var(--t-normal) ease; }
.step-line.active { background: var(--accent); }
.step-dot {
  width: 36px; height: 36px; border-radius: 50%; border: 2px solid var(--border-input);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: var(--text-muted);
  background: var(--bg-deepest); flex-shrink: 0; transition: all var(--t-normal) ease;
}
.step-dot.active { border-color: var(--accent); color: var(--accent); }
.step-dot.done { background: var(--accent); border-color: var(--accent); color: #ffffff; }
.step-label { font-size: 12px; color: var(--text-muted); white-space: nowrap; transition: color var(--t-fast) ease; }
.step-label.active { color: var(--accent); }

.step-content { animation: fade-slide-enter 0.3s ease-out; }
@keyframes fade-slide-enter { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.step-footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }

.input-cards { display: flex; flex-direction: column; gap: 16px; }
.cv-input-card { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-card); padding: 20px; }
.cv-input-card h4 { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: var(--text-primary); }

/* Tone */
.tone-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.tone-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); overflow: hidden; cursor: pointer;
  transition: all var(--t-fast) ease-out; position: relative;
}
.tone-card:hover { border-color: var(--text-muted); transform: translateY(-2px); }
.tone-card.selected { border-color: var(--accent); box-shadow: 0 0 16px rgba(240, 185, 11, 0.1); }
.tone-strip { height: 4px; background: var(--strip-color, var(--border-input)); transition: height var(--t-fast) ease; }
.tone-card.selected .tone-strip { height: 6px; }
.tone-body { padding: 16px; }
.tone-label { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0 0 6px; }
.tone-desc { font-size: 12px; color: var(--text-muted); margin: 0 0 12px; }
.tone-preview {
  background: var(--bg-deepest); border-radius: 8px; padding: 10px;
  font-size: 11px; color: var(--text-secondary); line-height: 1.5;
  white-space: pre-wrap; font-family: var(--font-sans); margin: 0;
}
.tone-check {
  position: absolute; top: 12px; right: 12px;
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--accent-subtle); display: flex; align-items: center; justify-content: center;
}

/* Generating */
.generating-card { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-card); padding: 60px 24px; text-align: center; }
.gen-dots { display: flex; justify-content: center; gap: 8px; margin-bottom: 20px; }
.gen-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); animation: pulse-dot 1.2s ease-in-out infinite; }
@keyframes pulse-dot { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.2); } }

/* Result */
.result-area { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-card); padding: 24px; }
.letter-paper {
  background: var(--bg-deepest); border: 1px solid var(--border-input);
  border-radius: var(--radius-card); padding: 28px; margin-bottom: 16px;
}
.letter-paper pre {
  white-space: pre-wrap; font-size: 14px; line-height: 1.8;
  color: var(--text-primary); margin: 0; font-family: var(--font-sans);
}
.result-toolbar { display: flex; gap: 8px; }

.generate-btn {
  background: linear-gradient(135deg, var(--accent), #1d4ed8) !important;
  border: none !important; color: #ffffff !important; font-weight: 600;
}

/* 求职信历史侧栏 */
.history-sidebar { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-card); padding: 16px; max-height: 700px; overflow-y: auto; position: sticky; top: 16px; }
.history-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.history-header h4 { margin: 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.history-empty { text-align: center; color: var(--text-muted); padding: 24px 0; font-size: 13px; }
.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-item { background: var(--bg-deepest); border: 1px solid var(--border-input); border-radius: 8px; padding: 10px 12px; cursor: pointer; transition: all var(--t-fast) ease-out; }
.history-item:hover { border-color: var(--accent); background: var(--accent-subtle); }
.hi-top { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-muted); }
.hi-id { font-weight: 600; color: var(--text-primary); }
.hi-style { padding: 0 6px; border-radius: 3px; background: var(--bg-card); font-size: 10px; }
.hi-style.formal { color: #60a5fa; }
.hi-style.casual { color: #34d399; }
.hi-style.tech { color: #f0b90b; }
.hi-del { margin-left: auto; cursor: pointer; font-size: 16px; line-height: 1; color: var(--text-muted); padding: 0 4px; }
.hi-del:hover { color: var(--color-danger); }
.hi-title { font-size: 13px; font-weight: 500; color: var(--text-primary); margin: 4px 0 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hi-meta { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
.hi-preview { font-size: 12px; color: var(--text-secondary); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 跨页面导入栏 */
.import-bar { margin-bottom: 16px; }
.quick-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.field-hint { font-size: 12px; font-weight: normal; color: var(--text-muted); margin-left: 6px; }

/* 素材库弹窗（与 ChatView 共享样式） */
.picker-loading, .picker-empty { padding: 40px 20px; text-align: center; color: var(--text-muted); font-size: 13px; }
.picker-list { display: flex; flex-direction: column; gap: 8px; max-height: 480px; overflow-y: auto; }
.picker-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-input, 4px);
  cursor: pointer;
  transition: all var(--t-fast, 0.15s);
}
.picker-item:hover { border-color: var(--accent, #00b574); background: rgba(0, 181, 116, 0.04); }
.picker-body { flex: 1; min-width: 0; }
.picker-title {
  font-size: 14px; font-weight: 700; color: var(--text-primary, #1f2937);
  display: flex; align-items: center; gap: 6px;
}
.picker-tag { font-size: 10px; padding: 1px 6px; background: var(--accent, #00b574); color: #fff; border-radius: 2px; }
.picker-preview { font-size: 12px; color: var(--text-secondary, #6b7280); margin-top: 2px; line-height: 1.4; }
.picker-arrow { color: var(--text-muted, #9ca3af); }

@media (max-width: 768px) { .tone-cards { grid-template-columns: 1fr; } }
</style>
