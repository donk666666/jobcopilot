<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { matchResume, tailorResume, getJDAnalyses, getResumeOptimizations, getActiveResume, saveActiveResume, uploadResume, getResumeHistory, updateResumeHistory, deleteResumeHistory, exportResumeDocx } from '@/api'
import RadarChart from '@/components/RadarChart.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'

const resumeText = ref('')
const jdAnalysisText = ref('')
const loading = ref(false)
const tailorLoading = ref(false)
const downloadingDocx = ref(false)
const matchResult = ref<any>(null)
const tailoredResult = ref('')
const error = ref('')
const activeTab = ref('match')
const currentOptId = ref<number | null>(null)

const jdHistory = ref<any[]>([])
const selectedJdId = ref<number | null>(null)
const historyLoading = ref(false)

const optHistory = ref<any[]>([])
const showAnnotations = ref(true)

const lastMatchedForTailor = ref('')

// 历史简历
const resumeHistory = ref<any[]>([])
const resumeHistoryLoading = ref(false)
const editingResumeId = ref<number | null>(null)
const editingName = ref('')

// 文件上传
const uploadLoading = ref(false)
const uploadedFile = ref<{ name: string; char_count: number } | null>(null)
const uploadRef = ref<any>(null)

// ---- 文件上传处理 ----
async function handleFileChange(file: any) {
  uploadLoading.value = true
  error.value = ''
  uploadedFile.value = null
  try {
    const res: any = await uploadResume(file.raw)
    resumeText.value = res.text
    uploadedFile.value = { name: res.filename, char_count: res.char_count }
    try { await saveActiveResume(res.text) } catch { /* ignore */ }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e.message || '文件解析失败'
  } finally {
    uploadLoading.value = false
    uploadRef.value?.clearFiles()
  }
}

function beforeUpload(file: any) {
  const valid = ['.docx', '.pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!valid.includes(file.type) && !valid.includes(ext)) {
    error.value = '仅支持 .docx 和 .pdf 格式文件'
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    error.value = '文件大小不能超过 5MB'
    return false
  }
  return true
}

// 文件上传 / 匹配 / 改写 之间的轮询清理代码已删除

async function loadHistory() {
  historyLoading.value = true
  try {
    const [jds, opts]: any[] = await Promise.all([getJDAnalyses(), getResumeOptimizations()])
    jdHistory.value = jds || []
    optHistory.value = opts || []
  } catch { /* ignore */ }
  finally { historyLoading.value = false }
}

function selectJd(item: any) {
  selectedJdId.value = item.id
  jdAnalysisText.value = JSON.stringify(item.analysis, null, 2)
}

function loadOpt(opt: any) {
  currentOptId.value = opt.id
  selectedJdId.value = opt.jd_analysis_id
  resumeText.value = opt.resume_text || ''
  if (opt.jd_analysis_json) jdAnalysisText.value = opt.jd_analysis_json
  if (opt.match_detail) {
    matchResult.value = opt.match_detail
    lastMatchedForTailor.value = JSON.stringify(opt.match_detail)
    activeTab.value = 'match'
  }
  if (opt.tailored_resume) {
    tailoredResult.value = opt.tailored_resume
    showAnnotations.value = !!opt.annotations_enabled
  }
}

watch(showAnnotations, async (val) => {
  if (!tailoredResult.value || !matchResult.value || loading.value) return
  loading.value = true; error.value = ''
  try {
    const res: any = await tailorResume(
      resumeText.value, jdAnalysisText.value,
      JSON.stringify(matchResult.value), currentOptId.value || undefined, val,
    )
    tailoredResult.value = res.result
    // 跨页面共享给求职信页
    try { localStorage.setItem('last_tailored_resume', res.result) } catch {}
    if (res.opt_id) currentOptId.value = res.opt_id
    loadHistory()
  } catch (e: any) { error.value = e.message || '重新生成失败' }
  finally { loading.value = false }
})

async function loadResumeHistory() {
  resumeHistoryLoading.value = true
  try {
    const res: any = await getResumeHistory()
    resumeHistory.value = res || []
  } catch { /* ignore */ }
  finally { resumeHistoryLoading.value = false }
}

function selectResumeHistory(item: any) {
  resumeText.value = item.content
  editingResumeId.value = item.id
  editingName.value = item.name
}

function startEditName() {
  editingResumeId.value = resumeHistory.value.find(r => r.is_active)?.id ?? null
}

async function saveEditedResume() {
  if (editingResumeId.value === null) return
  try {
    await updateResumeHistory(editingResumeId.value, resumeText.value, editingName.value)
    await saveActiveResume(resumeText.value)
    editingResumeId.value = null
    await loadResumeHistory()
  } catch (e: any) { error.value = e.message || '保存失败' }
}

async function deleteResumeHistoryItem(id: number) {
  try {
    await deleteResumeHistory(id)
    await loadResumeHistory()
  } catch (e: any) { error.value = e.message || '删除失败' }
}

function newResumeText() {
  resumeText.value = ''
  editingResumeId.value = null
  editingName.value = '默认简历'
}

onMounted(async () => {
  await loadHistory()
  await loadResumeHistory()
  try {
    const res: any = await getActiveResume()
    if (res?.content) resumeText.value = res.content
    if (res?.name) editingName.value = res.name
    if (res?.id) editingResumeId.value = res.id
  } catch { /* ignore */ }
})

async function handleMatch() {
  if (!resumeText.value.trim() || !jdAnalysisText.value.trim()) {
    error.value = '请填写简历并选择JD分析结果'; return
  }
  loading.value = true; error.value = ''; matchResult.value = null; tailoredResult.value = ''
  activeTab.value = 'match'
  try {
    const res: any = await matchResume(resumeText.value, jdAnalysisText.value, selectedJdId.value || undefined)
    matchResult.value = res.result
    lastMatchedForTailor.value = JSON.stringify(res.result)
    // 跨页面共享给求职信页（last_match_result / last_tailored_resume）
    try { localStorage.setItem('last_match_result', JSON.stringify(res.result)) } catch {}
    if (res.opt_id) currentOptId.value = res.opt_id
    try { await saveActiveResume(resumeText.value) } catch { /* ignore */ }
    loadHistory()
  } catch (e: any) { error.value = e.message || '匹配分析失败' }
  finally { loading.value = false }
}

async function handleTailor() {
  if (!matchResult.value) { error.value = '请先完成匹配度分析'; return }
  tailorLoading.value = true; error.value = ''; tailoredResult.value = ''
  try {
    const res: any = await tailorResume(
      resumeText.value, jdAnalysisText.value,
      JSON.stringify(matchResult.value), currentOptId.value || undefined, showAnnotations.value,
    )
    tailoredResult.value = res.result
    // 跨页面共享给求职信页
    try { localStorage.setItem('last_tailored_resume', res.result) } catch {}
    if (res.opt_id) currentOptId.value = res.opt_id
    activeTab.value = 'tailored'
    loadHistory()
  } catch (e: any) { error.value = e.message || '简历优化失败' }
  finally { tailorLoading.value = false }
}

// 下载改写后简历为 Word
async function downloadTailoredAsDocx() {
  if (!tailoredResult.value) return
  downloadingDocx.value = true
  try {
    const blob = (await exportResumeDocx({
      title: '改写后简历',
      content: tailoredResult.value,
    })) as unknown as Blob
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `改写简历_${new Date().toISOString().slice(0, 10)}.docx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已下载 Word')
  } catch (e: any) {
    ElMessage.error('下载失败：' + (e?.message || ''))
  } finally {
    downloadingDocx.value = false
  }
}

// 复制到剪贴板
async function copyTailored() {
  if (!tailoredResult.value) return
  try {
    await navigator.clipboard.writeText(tailoredResult.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择文本')
  }
}

function getScoreColor(score: number) {
  if (score >= 80) return 'var(--color-success)'
  if (score >= 60) return 'var(--accent)'
  return 'var(--color-danger)'
}

// 各维度满分权重（与后端 prompts/parallel_agents.py 的 AGENT_PROMPTS key 一致）
// 后端分项权重（与 backend/prompts/resume_tailor.py 一致）
// 每维度满分不同，分项分数加和应等于 match_score
const DIMENSION_WEIGHTS: Record<string, number> = {
  '技能匹配': 40,
  '经验匹配': 25,
  '学历匹配': 10,
  '综合素质': 15,
  '加分项': 10,
}

// 维度 key → 中文显示名（前端 UI 用）
const DIMENSION_LABELS: Record<string, string> = {
  '技能匹配': '技能匹配',
  '经验匹配': '经验匹配',
  '学历匹配': '学历匹配',
  '综合素质': '综合素质',
  '加分项': '加分项',
}

const radarData = computed(() => {
  if (!matchResult.value?.score_breakdown) return {}
  const breakdown = matchResult.value.score_breakdown
  return Object.fromEntries(
    Object.entries(breakdown).map(([k, v]) => {
      const num = Number(v)
      const weight = DIMENSION_WEIGHTS[k] || 100
      // 归一化为 0-100 百分比，让各维度按各自满分计算实际占比
      const label = DIMENSION_LABELS[k] || k
      return [label, Math.min(100, Math.round((num / weight) * 100))]
    })
  )
})

const radarReady = computed(() => Object.keys(radarData.value).length >= 3)

// 归一化后的明细进度条（各维度按各自满分换算成百分比）
const breakdownData = computed(() => {
  if (!matchResult.value?.score_breakdown) return []
  return Object.entries(matchResult.value.score_breakdown).map(([k, v]) => {
    const num = Number(v)
    const weight = DIMENSION_WEIGHTS[k] || 100
    const label = DIMENSION_LABELS[k] || k
    return { label, percent: Math.min(100, Math.round((num / weight) * 100)), raw: num, weight }
  })
})

// ===== A-H 8 段式评估 =====
const hasAhEval = computed(() => {
  const m = matchResult.value
  if (!m) return false
  return !!(m.block_a_role_summary || m.block_b_requirements || m.block_c_level_strategy
    || m.block_d_compensation || m.block_e_personalization?.length || m.block_f_interview_prep?.length
    || m.block_g_legitimacy)
})

function importanceIcon(imp: string): string {
  return { high: '🔴', medium: '🟡', low: '⚪' }[imp] || '·'
}
function matchIcon(m: string): string {
  return { matched: '✅', partial: '🟡', missing: '❌' }[m] || '·'
}
function weightSourceShort(ws: string): string {
  return { jd_explicit: 'JD原文', jd_structure: 'JD结构', estimated: 'AI估算' }[ws] || ws
}
function weightSourceLabel(ws: string): string {
  return {
    jd_explicit: 'JD 自己明确写出的要求',
    jd_structure: '从 JD 结构推断',
    estimated: 'AI 基于岗位通用要求估算（不可信）',
  }[ws] || ws
}
function levelGapLabel(g: string): string {
  return { 'under-qualified': '⚠️ 偏低', 'match': '✅ 匹配', 'over-qualified': '💪 偏高' }[g] || g
}
function compFitLabel(f: string): string {
  return {
    'below_market': '🟢 低于市场（好）',
    'market': '🟡 正常',
    'above_market': '🔴 高于市场（警惕）',
    'unknown': '⚪ 不确定',
  }[f] || f
}
function interviewTypeIcon(t: string): string {
  return { behavioral: '🗣️', technical: '💻', company: '🏢' }[t] || '·'
}
function interviewTypeLabel(t: string): string {
  return { behavioral: '行为', technical: '技术', company: '公司' }[t] || t
}
function trustLabel(t: string): string {
  return { high: '🟢 高', medium: '🟡 中', low: '🔴 低' }[t] || t
}
</script>

<template>
  <div class="resume-page">
    <h2 class="page-title">岗位匹配 & 简历优化</h2>
    <p class="page-sub">两阶段流程：① 选历史 JD 分析 → AI 按 A-H 8 段框架评估匹配度（Block A-H，含 weight_source 重要性、weight 来源、资历策略、薪资评估、防骗红旗）→ ② 根据匹配诊断定向改写简历</p>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="7">
        <div class="input-card">
          <h4 class="card-header">简历文本</h4>
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :before-upload="beforeUpload"
            :on-change="handleFileChange"
            :show-file-list="false"
            accept=".docx,.pdf"
            style="margin-bottom: 12px"
          >
            <div class="upload-area" :class="{ uploading: uploadLoading }">
              <el-icon v-if="!uploadLoading" class="el-icon--upload"><i class="fa fa-cloud-upload" style="font-size: 28px; color: var(--text-muted)" /></el-icon>
              <el-icon v-else class="is-loading"><i class="fa fa-spinner fa-pulse" style="font-size: 28px; color: var(--accent)" /></el-icon>
              <div class="el-upload__text">
                <template v-if="!uploadLoading">
                  拖拽文件到此处，或 <em>点击选择</em>
                </template>
                <template v-else>
                  正在解析文件...
                </template>
              </div>
              <div class="el-upload__tip">支持 .docx / .pdf，最大 5MB</div>
            </div>
          </el-upload>
          <div v-if="uploadedFile" class="upload-success">
            <i class="fa fa-check-circle" style="color: var(--color-success)" /> {{ uploadedFile.name }} ({{ uploadedFile.char_count }} 字)
          </div>
          <el-input v-model="resumeText" type="textarea" :rows="8" placeholder="粘贴你的简历全文，或上传文件自动填充..." />
          <div class="resume-actions">
            <el-button size="small" type="primary" plain @click="saveEditedResume" :disabled="editingResumeId === null">
              保存修改
            </el-button>
            <el-button size="small" text @click="newResumeText">新建简历</el-button>
          </div>
          <el-input v-model="editingName" size="small" placeholder="简历名称" style="margin-top: 6px" />
        </div>

        <!-- 历史简历列表 -->
        <div class="input-card">
          <div class="card-header-row">
            <h4 class="card-header">历史简历</h4>
            <el-button size="small" text @click="loadResumeHistory" :loading="resumeHistoryLoading">刷新</el-button>
          </div>
          <div v-if="resumeHistory.length === 0" class="empty-hint">暂无历史简历，上传或保存后这里会记录。</div>
          <div v-else class="resume-history-list">
            <div
              v-for="item in resumeHistory"
              :key="item.id"
              class="resume-history-item"
              :class="{ active: item.is_active }"
              @click="selectResumeHistory(item)"
            >
              <div class="rh-item-top">
                <span class="rh-name" :title="item.name">{{ item.name }}</span>
                <span v-if="item.is_active" class="rh-active-tag">当前</span>
                <span class="rh-del" @click.stop="deleteResumeHistoryItem(item.id)" title="删除">✕</span>
              </div>
              <div class="rh-preview">{{ item.content?.slice(0, 40) }}</div>
              <div class="rh-time">{{ item.updated_at?.slice(0, 16) }}</div>
            </div>
          </div>
        </div>

        <div class="input-card">
          <div class="card-header-row">
            <h4 class="card-header">选择JD分析结果</h4>
            <el-button size="small" text @click="loadHistory" :loading="historyLoading">刷新</el-button>
          </div>
          <div v-if="jdHistory.length === 0" class="empty-hint">暂无历史，请先去「JD智能分析」页面分析职位。</div>
          <div v-else class="jd-list">
            <div
              v-for="item in jdHistory" :key="item.id"
              class="jd-item"
              :class="{ selected: selectedJdId === item.id }"
              @click="selectJd(item)"
            >
              <div class="jd-item-title">{{ item.position_title }}</div>
              <div class="jd-item-preview">{{ item.jd_preview }}</div>
            </div>
          </div>
          <div class="action-row">
            <el-tag :type="matchResult ? 'success' : 'warning'" size="default" effect="dark" round style="margin-right: 8px">
              Step 1
            </el-tag>
            <el-button type="primary" :loading="loading" @click="handleMatch" :disabled="!selectedJdId" class="action-btn">
              {{ loading && !matchResult ? '分析中...' : (matchResult ? '重新匹配分析' : '① 开始匹配分析') }}
            </el-button>
            <el-tag v-if="matchResult" :type="tailoredResult ? 'success' : 'warning'" size="default" effect="dark" round style="margin: 0 8px 0 16px">
              Step 2
            </el-tag>
            <el-button v-if="matchResult" type="success" :loading="tailorLoading" @click="handleTailor" :disabled="!matchResult" class="action-btn">
              {{ tailorLoading ? '改写中...' : (tailoredResult ? '② 重新改写简历' : '② 根据匹配结果改写简历') }}
            </el-button>
          </div>
        </div>

        <div v-if="optHistory.length > 0" class="history-card">
          <h4 class="card-header">优化历史</h4>
          <div class="history-list">
            <div
              v-for="opt in optHistory" :key="opt.id"
              class="history-item"
              :class="{ selected: currentOptId === opt.id }"
              @click="loadOpt(opt)"
            >
              <span v-if="opt.match_score" class="history-badge" :style="{ background: getScoreColor(opt.match_score) }">
                {{ opt.match_score }}
              </span>
              {{ opt.resume_preview }}
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="17">
        <LoadingSkeleton v-if="loading && !matchResult" :lines="5" />

        <div v-else-if="matchResult" class="result-card">
          <!-- Score + Radar -->
          <el-row :gutter="20" style="margin-bottom: 20px">
            <el-col :span="6">
              <div class="score-card">
                <div class="score-number" :style="{ color: getScoreColor(matchResult.match_score) }">
                  {{ matchResult.match_score }}
                </div>
                <div class="score-unit">匹配度评分</div>
              </div>
            </el-col>
            <el-col :span="18">
              <div class="radar-card">
                <RadarChart v-if="radarReady" :data="radarData" :size="280" />
                <span v-else style="color: var(--text-muted)">维度数据不足</span>
              </div>
            </el-col>
          </el-row>

          <!-- Score breakdown -->
          <div v-if="breakdownData.length" class="breakdown-list">
            <div v-for="bd in breakdownData" :key="bd.label" class="breakdown-row">
              <span class="breakdown-label">{{ bd.label }}</span>
              <el-progress
                :percentage="bd.percent"
                :color="getScoreColor(bd.percent)"
                style="flex: 1; margin: 0 12px"
              />
              <span class="breakdown-val">{{ bd.raw }}/{{ bd.weight }}</span>
            </div>
          </div>

          <!-- A-H 8 段式评估（A 角色摘要 / B 要求匹配 / C 资历策略 / D 薪资 / E 个性化 / F 面试准备 / G 防骗 / H 表单答案）-->
          <div v-if="hasAhEval" class="ah-eval-section">
            <!-- A. 角色摘要 -->
            <div v-if="matchResult.block_a_role_summary" class="ah-block ah-block-a">
              <h4 class="section-label">📌 A. 角色摘要</h4>
              <p class="ah-quote">{{ matchResult.block_a_role_summary }}</p>
            </div>

            <!-- B. 要求匹配 -->
            <div v-if="matchResult.block_b_requirements?.length" class="ah-block ah-block-b">
              <div class="ah-block-header">
                <h4 class="section-label">📋 B. 要求匹配</h4>
                <span v-if="matchResult.block_b_score !== undefined" class="ah-block-score">
                  Block B 得分：<b>{{ matchResult.block_b_score }}</b> / 40
                </span>
              </div>
              <div v-for="(r, idx) in matchResult.block_b_requirements" :key="idx" class="ah-req-item">
                <div class="ah-req-top">
                  <span class="ah-req-imp" :class="`imp-${r.importance}`">
                    {{ importanceIcon(r.importance) }}
                  </span>
                  <span class="ah-req-match" :class="`match-${r.resume_match}`">
                    {{ matchIcon(r.resume_match) }}
                  </span>
                  <span class="ah-req-text">{{ r.requirement }}</span>
                  <span v-if="r.weight_source" class="ah-req-src" :title="weightSourceLabel(r.weight_source)">
                    {{ weightSourceShort(r.weight_source) }}
                  </span>
                </div>
                <div v-if="r.evidence && r.evidence !== '无'" class="ah-req-evidence">
                  → 简历证据：{{ r.evidence }}
                </div>
              </div>
            </div>

            <!-- C. 资历策略 -->
            <div v-if="matchResult.block_c_level_strategy" class="ah-block ah-block-c">
              <h4 class="section-label">🎯 C. 资历策略</h4>
              <div class="ah-level-row">
                <span class="ah-level-item">
                  <span class="ah-level-label">JD 要求</span>
                  <span class="ah-level-val">{{ matchResult.block_c_level_strategy.jd_required_level || '?' }}</span>
                </span>
                <span class="ah-level-arrow">→</span>
                <span class="ah-level-item">
                  <span class="ah-level-label">你的实际</span>
                  <span class="ah-level-val">{{ matchResult.block_c_level_strategy.resume_actual_level || '?' }}</span>
                </span>
                <span class="ah-level-gap" :class="`gap-${matchResult.block_c_level_strategy.gap}`">
                  {{ levelGapLabel(matchResult.block_c_level_strategy.gap) }}
                </span>
              </div>
              <p v-if="matchResult.block_c_level_strategy.suggestion" class="ah-suggestion">
                💡 {{ matchResult.block_c_level_strategy.suggestion }}
              </p>
            </div>

            <!-- D. 薪资 -->
            <div v-if="matchResult.block_d_compensation" class="ah-block ah-block-d">
              <h4 class="section-label">💰 D. 薪资评估</h4>
              <div class="ah-comp-row">
                <div class="ah-comp-item">
                  <span class="ah-comp-label">JD 范围</span>
                  <span class="ah-comp-val">{{ matchResult.block_d_compensation.jd_salary_range || '未明确' }}</span>
                </div>
                <div class="ah-comp-item">
                  <span class="ah-comp-label">市场参考</span>
                  <span class="ah-comp-val">{{ matchResult.block_d_compensation.market_range || '?' }}</span>
                </div>
                <div class="ah-comp-fit" :class="`fit-${matchResult.block_d_compensation.fit}`">
                  {{ compFitLabel(matchResult.block_d_compensation.fit) }}
                </div>
              </div>
              <p v-if="matchResult.block_d_compensation.note" class="ah-comp-note">
                {{ matchResult.block_d_compensation.note }}
              </p>
            </div>

            <!-- E. 个性化切入点 -->
            <div v-if="matchResult.block_e_personalization?.length" class="ah-block ah-block-e">
              <h4 class="section-label">✨ E. 个性化切入点</h4>
              <ul class="ah-list">
                <li v-for="(p, i) in matchResult.block_e_personalization" :key="i">{{ p }}</li>
              </ul>
            </div>

            <!-- F. 面试准备 -->
            <div v-if="matchResult.block_f_interview_prep?.length" class="ah-block ah-block-f">
              <h4 class="section-label">🎤 F. 面试准备</h4>
              <div v-for="(q, idx) in matchResult.block_f_interview_prep" :key="idx" class="ah-interview-item">
                <div class="ah-interview-q">
                  <span class="ah-interview-type" :class="`type-${q.question_type}`">
                    {{ interviewTypeIcon(q.question_type) }} {{ interviewTypeLabel(q.question_type) }}
                  </span>
                  <span class="ah-interview-text">{{ q.question }}</span>
                </div>
                <div v-if="q.answer_direction" class="ah-interview-direction">
                  → 回答方向：{{ q.answer_direction }}
                </div>
              </div>
            </div>

            <!-- G. 防骗 / 防僵尸 JD -->
            <div v-if="matchResult.block_g_legitimacy" class="ah-block ah-block-g">
              <h4 class="section-label">🛡️ G. 防骗检测</h4>
              <div class="ah-trust-row">
                <span class="ah-trust-label">可信度</span>
                <span class="ah-trust-val" :class="`trust-${matchResult.block_g_legitimacy.overall_trust}`">
                  {{ trustLabel(matchResult.block_g_legitimacy.overall_trust) }}
                </span>
              </div>
              <div v-if="matchResult.block_g_legitimacy.red_flags?.length" class="ah-flags">
                <div v-for="(f, i) in matchResult.block_g_legitimacy.red_flags" :key="i" class="ah-flag-item">
                  ⚠️ {{ f }}
                </div>
              </div>
              <div v-else class="ah-no-flags">✅ 无明显红旗</div>
            </div>
          </div>

          <!-- Matched points -->
          <div v-if="matchResult?.matched_points?.length" class="tag-section">
            <h4 class="section-label">匹配点</h4>
            <div class="tag-row">
              <span v-for="(point, i) in matchResult.matched_points" :key="i" class="skill-tag match">{{ point }}</span>
            </div>
          </div>

          <!-- Gap points -->
          <div v-if="matchResult?.gap_points?.length" class="tag-section">
            <h4 class="section-label">差距点</h4>
            <div class="tag-row">
              <span v-for="(point, i) in matchResult.gap_points" :key="i" class="skill-tag gap">{{ point }}</span>
            </div>
          </div>

          <!-- Overall assessment -->
          <div v-if="matchResult?.overall_assessment" class="assessment-section">
            <h4 class="section-label">整体评价</h4>
            <p class="assessment-text">{{ matchResult.overall_assessment }}</p>
          </div>
        </div>

        <!-- 改写后简历展示区 -->
        <div v-if="tailoredResult" class="result-card" style="margin-top: 16px">
          <div class="tailor-header">
            <h3 class="section-label">📝 改写后简历</h3>
            <div class="tailor-actions">
              <el-button size="small" plain @click="downloadTailoredAsDocx" :disabled="downloadingDocx">
                <el-icon><Download /></el-icon>
                下载 Word
              </el-button>
              <el-button size="small" plain @click="copyTailored">
                <el-icon><DocumentCopy /></el-icon>
                复制
              </el-button>
            </div>
          </div>
          <pre class="tailor-content">{{ tailoredResult }}</pre>
        </div>

        <div v-else class="empty-result">
          <el-empty description="等待匹配分析" />
        </div>
      </el-col>
    </el-row>

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
  </div>
</template>

<style scoped>
.resume-page {}
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

.input-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
  margin-bottom: 16px;
}

.card-header { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: var(--text-primary); }
.card-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }

.action-row { display: flex; gap: 8px; margin-top: 12px; }
.action-row .el-button.action-btn { flex: 1; margin: 0; }

.empty-hint { color: var(--text-muted); padding: 12px 0; font-size: 13px; }

.resume-actions { display: flex; gap: 8px; margin-top: 10px; }

.resume-history-list { max-height: 240px; overflow-y: auto; }
.resume-history-item {
  padding: 8px 10px; margin-bottom: 6px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--border-input); transition: all var(--t-fast) ease-out;
}
.resume-history-item:hover { border-color: var(--accent); }
.resume-history-item.active { border-color: var(--accent); background: var(--accent-subtle); }
.rh-item-top { display: flex; align-items: center; gap: 6px; }
.rh-name { font-weight: 600; font-size: 13px; color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rh-active-tag { font-size: 11px; color: var(--accent); border: 1px solid var(--accent); border-radius: 4px; padding: 0 4px; flex-shrink: 0; }
.rh-del { color: var(--text-muted); cursor: pointer; flex-shrink: 0; }
.rh-del:hover { color: var(--color-danger); }
.rh-preview { font-size: 12px; color: var(--text-muted); margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rh-time { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

.jd-list { max-height: 260px; overflow-y: auto; }
.jd-item {
  padding: 8px 10px; margin-bottom: 6px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--border-input); transition: all var(--t-fast) ease-out;
  overflow: hidden;
}
.jd-item:hover { border-color: var(--accent); }
.jd-item.selected { border-color: var(--accent); background: var(--accent-subtle); }
.jd-item-title { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.jd-item-preview {
  font-size: 12px; color: var(--text-muted); margin-top: 2px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); padding: 16px;
}
.history-list { max-height: 200px; overflow-y: auto; }
.history-item {
  padding: 6px 8px; margin-bottom: 4px; border-radius: 4px; cursor: pointer;
  font-size: 13px; border: 1px solid var(--border-input); transition: all var(--t-fast) ease-out;
  color: var(--text-secondary);
}
.history-item:hover { border-color: var(--accent); }
.history-item.selected { border-color: var(--accent); background: var(--accent-subtle); }
.history-badge {
  display: inline-block; width: 28px; height: 20px; line-height: 20px; text-align: center;
  border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 6px; color: #fff;
}

/* Result */
.result-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); padding: 24px; min-height: 400px;
}

.score-card {
  background: var(--bg-deepest); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); padding: 24px; text-align: center;
}
.score-number { font-size: 56px; font-weight: 800; line-height: 1; margin-bottom: 8px; }
.score-unit { font-size: 13px; color: var(--text-muted); }

.radar-card {
  background: var(--bg-deepest); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); padding: 20px; display: flex;
  align-items: center; justify-content: center; min-height: 280px;
}

.breakdown-list { margin-bottom: 16px; }
.breakdown-row { display: flex; align-items: center; margin-bottom: 12px; }
.breakdown-label { width: 80px; flex-shrink: 0; font-size: 13px; color: var(--text-secondary); }
.breakdown-val { width: 40px; text-align: right; font-size: 13px; color: var(--text-primary); font-weight: 600; }

.tag-section { margin-bottom: 16px; }
.section-label { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0 0 10px; }
.tag-row { display: flex; flex-wrap: wrap; gap: 8px; }

.skill-tag { padding: 4px 12px; border-radius: var(--radius-tag); font-size: 12px; font-weight: 500; }
.skill-tag.match { background: rgba(52, 211, 153, 0.15); color: var(--color-success); }
.skill-tag.gap { background: rgba(248, 113, 113, 0.15); color: var(--color-danger); }

.assessment-section { margin-bottom: 16px; }
.assessment-text { color: var(--text-secondary); line-height: 1.6; font-size: 14px; }

.empty-result {
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); min-height: 400px;
  display: flex; align-items: center; justify-content: center;
}

/* Upload */
.upload-area { padding: 8px 0; }
.upload-area.uploading { opacity: 0.7; }
.upload-success { font-size: 13px; padding: 6px 0; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; }

.tailor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.tailor-actions { display: flex; gap: 8px; }
.tailor-content {
  background: var(--bg-deepest, #f5f6f7);
  border: 1px solid var(--border-subtle, #e5e7eb);
  border-radius: 6px;
  padding: 16px;
  max-height: 600px;
  overflow-y: auto;
  font-family: var(--font-mono, Consolas, monospace);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-primary);
  margin: 0;
}

/* ===== A-H 8 段式评估 ===== */
.ah-eval-section {
  margin-top: 16px;
  border-top: 1px dashed var(--border-subtle, #e5e7eb);
  padding-top: 16px;
}
.ah-block {
  margin-bottom: 16px;
  padding: 12px 14px;
  background: var(--bg-deepest, #f8f9fa);
  border-radius: var(--radius-card, 8px);
  border-left: 3px solid var(--accent, #00b574);
}
.ah-block .section-label {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 700;
  color: var(--accent, #00b574);
}
.ah-quote {
  margin: 0;
  padding: 8px 12px;
  background: rgba(0, 181, 116, 0.08);
  border-left: 2px solid var(--accent, #00b574);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
}
.ah-block-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
}
.ah-block-score {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
}
.ah-block-score b {
  color: var(--accent, #00b574);
  font-size: 14px;
}

/* Block B 要求列表 */
.ah-req-item {
  padding: 8px 10px;
  margin-bottom: 6px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid var(--border-subtle, #e5e7eb);
}
.ah-req-top {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.ah-req-imp, .ah-req-match {
  font-size: 12px;
  flex-shrink: 0;
}
.ah-req-text {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #1f2937);
  min-width: 0;
}
.ah-req-src {
  font-size: 10px;
  padding: 1px 6px;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border-radius: 3px;
  font-weight: 600;
  flex-shrink: 0;
}
.ah-req-evidence {
  margin-top: 4px;
  margin-left: 24px;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.5;
}

/* Block C 资历策略 */
.ah-level-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.ah-level-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ah-level-label {
  font-size: 11px;
  color: var(--text-muted, #6b7280);
}
.ah-level-val {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}
.ah-level-arrow {
  color: var(--text-muted, #9ca3af);
  font-size: 18px;
}
.ah-level-gap {
  margin-left: auto;
  padding: 4px 10px;
  background: #fff;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.ah-level-gap.gap-match { color: var(--color-success, #16a34a); }
.ah-level-gap.gap-under-qualified { color: var(--color-warning, #f59e0b); }
.ah-level-gap.gap-over-qualified { color: var(--accent, #00b574); }
.ah-suggestion {
  margin: 6px 0 0;
  padding: 8px 10px;
  background: rgba(245, 158, 11, 0.08);
  border-left: 2px solid #f59e0b;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary, #1f2937);
  line-height: 1.5;
}

/* Block D 薪资 */
.ah-comp-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.ah-comp-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ah-comp-label {
  font-size: 11px;
  color: var(--text-muted, #6b7280);
}
.ah-comp-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}
.ah-comp-fit {
  margin-left: auto;
  padding: 4px 10px;
  background: #fff;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.ah-comp-fit.fit-below_market { color: var(--color-success, #16a34a); }
.ah-comp-fit.fit-market { color: var(--color-warning, #f59e0b); }
.ah-comp-fit.fit-above_market { color: var(--color-danger, #dc2626); }
.ah-comp-fit.fit-unknown { color: var(--text-muted, #9ca3af); }
.ah-comp-note {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.5;
}

/* Block E 列表 */
.ah-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--text-primary, #1f2937);
  line-height: 1.7;
}
.ah-list li { margin-bottom: 4px; }

/* Block F 面试准备 */
.ah-interview-item {
  padding: 8px 10px;
  margin-bottom: 6px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid var(--border-subtle, #e5e7eb);
}
.ah-interview-q {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.ah-interview-type {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 3px;
  font-weight: 600;
  flex-shrink: 0;
}
.ah-interview-type.type-technical {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}
.ah-interview-type.type-behavioral {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}
.ah-interview-type.type-company {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}
.ah-interview-text {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #1f2937);
  min-width: 0;
}
.ah-interview-direction {
  margin-top: 4px;
  margin-left: 4px;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.5;
}

/* Block G 防骗 */
.ah-trust-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ah-trust-label {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
}
.ah-trust-val {
  font-size: 13px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 4px;
  background: #fff;
}
.ah-trust-val.trust-high { color: var(--color-success, #16a34a); }
.ah-trust-val.trust-medium { color: var(--color-warning, #f59e0b); }
.ah-trust-val.trust-low { color: var(--color-danger, #dc2626); }
.ah-flag-item {
  padding: 6px 10px;
  margin-bottom: 4px;
  background: rgba(220, 38, 38, 0.08);
  border-left: 2px solid var(--color-danger, #dc2626);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-primary, #1f2937);
  line-height: 1.5;
}
.ah-no-flags {
  padding: 6px 10px;
  background: rgba(16, 185, 129, 0.08);
  border-left: 2px solid var(--color-success, #16a34a);
  border-radius: 4px;
  font-size: 12px;
  color: var(--color-success, #16a34a);
}
</style>
