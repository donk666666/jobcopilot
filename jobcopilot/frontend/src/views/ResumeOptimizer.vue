<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { matchResume, tailorResume, getJDAnalyses, getResumeOptimizations, getActiveResume, saveActiveResume } from '@/api'
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

onMounted(async () => {
  await loadHistory()
  try {
    const res: any = await getActiveResume()
    if (res?.content) resumeText.value = res.content
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

const radarData = computed(() => {
  if (!matchResult.value?.score_breakdown) return {}
  return Object.fromEntries(
    Object.entries(matchResult.value.score_breakdown).map(([k, v]) => [k, Number(v)])
  )
})

const radarReady = computed(() => Object.keys(radarData.value).length >= 3)
</script>

<template>
  <div class="resume-page">
    <h2 class="page-title">简历智能优化</h2>
    <p class="page-sub">上传简历 + 选择历史JD分析，AI 评估匹配度并定向优化（RAG 检索增强）</p>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="7">
        <div class="input-card">
          <h4 class="card-header">简历文本</h4>
          <el-input v-model="resumeText" type="textarea" :rows="8" placeholder="粘贴你的简历全文..." />
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
          <el-button type="primary" :loading="loading" @click="handleMatch" style="width: 100%; margin-top: 12px" :disabled="!selectedJdId">
            开始匹配分析
          </el-button>
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
          <div v-if="matchResult?.score_breakdown" class="breakdown-list">
            <div v-for="(score, label) in matchResult.score_breakdown" :key="label" class="breakdown-row">
              <span class="breakdown-label">{{ label }}</span>
              <el-progress
                :percentage="score"
                :color="getScoreColor(score)"
                style="flex: 1; margin: 0 12px"
              />
              <span class="breakdown-val">{{ score }}</span>
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
            {{ tailoredResult ? '重新生成优化简历' : '根据匹配结果优化简历' }}
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

.empty-hint { color: var(--text-muted); padding: 12px 0; font-size: 13px; }

.jd-list { max-height: 260px; overflow-y: auto; }
.jd-item {
  padding: 8px 10px; margin-bottom: 6px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--border-input); transition: all var(--t-fast) ease-out;
}
.jd-item:hover { border-color: var(--accent); }
.jd-item.selected { border-color: var(--accent); background: var(--accent-subtle); }
.jd-item-title { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.jd-item-preview { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

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
</style>
