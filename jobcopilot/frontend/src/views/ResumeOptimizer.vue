<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { matchResume, tailorResume, getJDAnalyses, getResumeOptimizations, getActiveResume, saveActiveResume, uploadResume, submitFullPipeline, getTaskStatus, getResumeHistory, updateResumeHistory, deleteResumeHistory } from '@/api'
import RadarChart from '@/components/RadarChart.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'

const resumeText = ref('')
const jdAnalysisText = ref('')
const loading = ref(false)
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

// 一键全流程
const pipelineRunning = ref(false)
const pipelineTaskId = ref('')
const pipelineStatus = ref('')
const pipelineProgress = ref(0)
const pipelineStep = ref('')
const pipelineError = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null
let pollFailCount = 0
let pollTimeoutTimer: ReturnType<typeof setTimeout> | null = null
const PIPELINE_STEPS = [
  { key: 'ANALYZING_JD', label: '分析JD' },
  { key: 'MATCHING', label: '匹配简历' },
  { key: 'TAILORING', label: '定制简历' },
  { key: 'WRITING_LETTER', label: '生成求职信' },
]
const currentStepIndex = computed(() => {
  const idx = PIPELINE_STEPS.findIndex(s => s.key === pipelineStatus.value)
  return idx >= 0 ? idx : (pipelineStatus.value === 'SUCCESS' ? 4 : 0)
})

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

// ---- 一键全流程 ----
async function handleFullPipeline() {
  if (!resumeText.value.trim() || !jdAnalysisText.value.trim()) {
    error.value = '请先上传简历并选择JD分析结果'
    return
  }
  pipelineRunning.value = true
  pipelineError.value = ''
  pipelineProgress.value = 0
  pipelineStep.value = ''
  pipelineStatus.value = ''
  pollFailCount = 0
  try {
    const res: any = await submitFullPipeline({
      resume_text: resumeText.value,
      jd_text: jdAnalysisText.value,
      jd_analysis_id: selectedJdId.value || undefined,
      style: 'professional',
    })
    pipelineTaskId.value = res.task_id
    pipelineStatus.value = 'PENDING'
    startPolling()
  } catch (e: any) {
    pipelineError.value = e?.response?.data?.detail || e.message || '提交失败'
    pipelineRunning.value = false
  }
}

function startPolling() {
  stopPolling()
  // 5 分钟超时保护
  pollTimeoutTimer = setTimeout(() => {
    stopPolling()
    pipelineRunning.value = false
    pipelineError.value = '全流程超时（5分钟），请检查后端服务'
  }, 5 * 60 * 1000)
  pollTimer = setInterval(async () => {
    try {
      const res: any = await getTaskStatus(pipelineTaskId.value)
      pipelineStatus.value = res.status
      pipelineProgress.value = res.progress || pipelineProgress.value
      pipelineStep.value = res.step || pipelineStep.value
      pollFailCount = 0
      if (res.status === 'SUCCESS') {
        stopPolling()
        pipelineRunning.value = false
        if (res.result) {
          if (res.result.dimension_scores) {
            matchResult.value = {
              overall_score: res.result.output,
              match_score: Object.values(res.result.dimension_scores as Record<string, number>).reduce((a: number, b: number) => a + b, 0) / 4,
              dimension_scores: res.result.dimension_scores,
              contradictions: res.result.contradictions,
            }
          }
          if (res.result.output) {
            tailoredResult.value = typeof res.result.output === 'string' ? res.result.output : JSON.stringify(res.result.output, null, 2)
          }
        }
        loadHistory()
      } else if (res.status === 'FAILURE') {
        stopPolling()
        pipelineRunning.value = false
        pipelineError.value = res.error || '全流程执行失败'
      }
    } catch {
      pollFailCount++
      if (pollFailCount >= 3) {
        stopPolling()
        pipelineRunning.value = false
        pipelineError.value = '轮询任务状态失败，请检查服务状态'
      }
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (pollTimeoutTimer) { clearTimeout(pollTimeoutTimer); pollTimeoutTimer = null }
}

onUnmounted(() => stopPolling())

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
    if (res.opt_id) currentOptId.value = res.opt_id
    try { await saveActiveResume(resumeText.value) } catch { /* ignore */ }
    loadHistory()
  } catch (e: any) { error.value = e.message || '匹配分析失败' }
  finally { loading.value = false }
}

async function handleTailor() {
  if (!matchResult.value) { error.value = '请先完成匹配度分析'; return }
  loading.value = true; error.value = ''; tailoredResult.value = ''
  try {
    const res: any = await tailorResume(
      resumeText.value, jdAnalysisText.value,
      JSON.stringify(matchResult.value), currentOptId.value || undefined, showAnnotations.value,
    )
    tailoredResult.value = res.result
    if (res.opt_id) currentOptId.value = res.opt_id
    activeTab.value = 'tailored'
    loadHistory()
  } catch (e: any) { error.value = e.message || '简历优化失败' }
  finally { loading.value = false }
}

function getScoreColor(score: number) {
  if (score >= 80) return 'var(--color-success)'
  if (score >= 60) return 'var(--accent)'
  return 'var(--color-danger)'
}

// 各维度满分权重（与后端 prompt 定义一致，用于归一化雷达图）
const DIMENSION_WEIGHTS: Record<string, number> = {
  '技能匹配': 40,
  '经验匹配': 25,
  '学历匹配': 10,
  '综合素质': 15,
  '加分项': 10,
}

const radarData = computed(() => {
  if (!matchResult.value?.score_breakdown) return {}
  const breakdown = matchResult.value.score_breakdown
  return Object.fromEntries(
    Object.entries(breakdown).map(([k, v]) => {
      const num = Number(v)
      const weight = DIMENSION_WEIGHTS[k] || 100
      // 归一化为 0-100 百分比，让各维度按各自满分计算实际占比
      return [k, Math.min(100, Math.round((num / weight) * 100))]
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
    return { label: k, percent: Math.min(100, Math.round((num / weight) * 100)), raw: num, weight }
  })
})
</script>

<template>
  <div class="resume-page">
    <h2 class="page-title">简历智能优化</h2>
    <p class="page-sub">上传简历 + 选择历史JD分析，AI 评估匹配度并定向优化（RAG 检索增强）</p>

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
            <el-button type="primary" :loading="loading" @click="handleMatch" :disabled="!selectedJdId" class="action-btn">
              {{ loading && !matchResult ? '分析中...' : '开始匹配分析' }}
            </el-button>
            <el-button type="success" :loading="pipelineRunning" @click="handleFullPipeline" :disabled="!selectedJdId || !resumeText.trim()" class="action-btn">
              一键全流程
            </el-button>
          </div>

          <!-- Pipeline 进度 -->
          <div v-if="pipelineRunning || pipelineError" class="pipeline-progress-card">
            <div v-if="pipelineRunning" class="pipeline-status">
              <el-steps :active="currentStepIndex" align-center finish-status="success" process-status="process">
                <el-step v-for="s in PIPELINE_STEPS" :key="s.key" :title="s.label" />
              </el-steps>
              <el-progress :percentage="pipelineProgress" :stroke-width="6" style="margin-top: 12px" />
              <p v-if="pipelineStep" class="pipeline-step-text">{{ pipelineStep }}</p>
            </div>
            <el-alert v-if="pipelineError" :title="pipelineError" type="error" show-icon closable @close="pipelineError = ''" style="margin-top: 8px" />
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

          <el-button type="primary" :loading="loading" @click="handleTailor" style="width: 100%; margin-top: 20px">
            {{ loading && tailoredResult ? '正在生成优化简历（约20秒）...' : (tailoredResult ? '重新生成优化简历' : '根据匹配结果优化简历') }}
          </el-button>
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

/* Pipeline */
.pipeline-progress-card {
  margin-top: 12px; padding: 16px;
  background: var(--bg-deepest); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
}
.pipeline-status { text-align: center; }
.pipeline-step-text { margin: 8px 0 0; font-size: 13px; color: var(--text-muted); }
</style>
