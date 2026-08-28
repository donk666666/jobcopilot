<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTrackerStats, healthCheck, analyzeJD, submitFullPipeline, getTaskStatus, tailorResume, listApplications, uploadResume } from '@/api'

const router = useRouter()
const stats = ref({ total: 0, by_status: {} as Record<string, number>, avg_match_score: 0 })
const userName = ref('萧仁科')

// 顶部数据（后端有数据走 stats，没有时显示占位）
const todayJobTarget = 3
const totalCount = computed(() => stats.value.total ?? null)
const matchAvg = computed(() => {
  const v = stats.value.avg_match_score
  return v && v > 0 ? Math.round(v) : null
})
const pendingCount = computed(() => stats.value.by_status?.['待投递'] || 0)
const fmt = (v: number | null) => v === null ? '—' : String(v)

onMounted(async () => {
  try {
    await healthCheck()
    const data: any = await getTrackerStats()
    stats.value = data
  } catch { /* offline ok */ }
})

const greeting = () => {
  const h = new Date().getHours()
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
}
const today = () => {
  const d = new Date()
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

// ===== 任务3：智能匹配分析 =====
const jdInput = ref('')
const jdActive = ref(false)
const jdLoading = ref(false)
const jdResult = ref<any>(null)
const jdError = ref('')

async function runAnalyze() {
  if (!jdInput.value.trim() || jdLoading.value) return
  jdLoading.value = true
  jdError.value = ''
  jdResult.value = null
  try {
    const res: any = await analyzeJD(jdInput.value)
    if (res?.result) {
      jdResult.value = res.result
      jdInput.value = ''
    } else {
      jdError.value = res?.error || '分析失败，请重试'
    }
  } catch (e: any) {
    jdError.value = e?.response?.data?.detail || e?.message || '网络错误'
  } finally {
    jdLoading.value = false
  }
}
function goOptimize() {
  router.push({ path: '/resume', query: jdResult.value?.id ? { jd_id: jdResult.value.id } : {} })
}
function resetJd() { jdResult.value = null; jdInput.value = ''; jdError.value = '' }
const skillsFound = computed<string[]>(() =>
  (jdResult.value?.hard_skills || jdResult.value?.skills || []) as string[]
)
const positionTitle = computed(() =>
  jdResult.value?.position_title || jdResult.value?.title || '该职位'
)

// ===== 任务4：一键全流程 =====
const pipelineActive = ref(false)
const pipelineResume = ref('')
const pipelineJd = ref('')
const pipelineRunning = ref(false)
const pipelineError = ref('')
const pipelineTaskId = ref('')
const pipelineUploading = ref(false)
const pipelineUploadedName = ref('')
const pipelineSteps = [
  { key: 'ANALYZING_JD', label: '分析JD' },
  { key: 'MATCHING', label: '匹配简历' },
  { key: 'TAILORING', label: '改写简历' },
  { key: 'WRITING_LETTER', label: '生成求职信' },
]

async function handlePipelineFile(file: { raw: File }) {
  pipelineUploading.value = true
  pipelineError.value = ''
  try {
    const res: any = await uploadResume(file.raw)
    pipelineResume.value = res.text
    pipelineUploadedName.value = res.filename
  } catch (e: any) {
    pipelineError.value = e?.response?.data?.detail || e?.message || '文件解析失败'
  } finally {
    pipelineUploading.value = false
  }
}

function beforePipelineUpload(file: File) {
  const validExt = ['.docx', '.pdf']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!validExt.includes(ext)) {
    pipelineError.value = '仅支持 .docx 和 .pdf 文件'
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    pipelineError.value = '文件大小不能超过 5MB'
    return false
  }
  return true
}
const pipelineStatus = ref('')
const pipelineProgress = ref(0)
let pollTimer: ReturnType<typeof setInterval> | null = null

const currentStepIndex = computed(() => {
  const map: Record<string, number> = {
    ANALYZING_JD: 0, MATCHING: 1, TAILORING: 2, WRITING_LETTER: 3, SUCCESS: 4,
  }
  return map[pipelineStatus.value] ?? 0
})

async function runPipeline() {
  if (!pipelineResume.value.trim() || !pipelineJd.value.trim() || pipelineRunning.value) return
  pipelineRunning.value = true
  pipelineError.value = ''
  pipelineProgress.value = 5
  pipelineStatus.value = 'PENDING'
  try {
    const res: any = await submitFullPipeline({
      resume_text: pipelineResume.value,
      jd_text: pipelineJd.value,
    })
    pipelineTaskId.value = res.task_id
    pipelineStatus.value = 'STARTED'
    startPolling()
  } catch (e: any) {
    pipelineError.value = e?.response?.data?.detail || e?.message || '提交失败'
    pipelineRunning.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!pipelineTaskId.value) return
    try {
      const res: any = await getTaskStatus(pipelineTaskId.value)
      pipelineStatus.value = res.status || pipelineStatus.value
      pipelineProgress.value = res.progress || pipelineProgress.value
      if (res.status === 'SUCCESS') { stopPolling(); pipelineRunning.value = false }
      else if (res.status === 'FAILURE') {
        stopPolling(); pipelineRunning.value = false
        pipelineError.value = res.error || '任务执行失败'
      }
    } catch { /* 单次失败忽略 */ }
  }, 1500)
}
function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }
onUnmounted(stopPolling)

// ===== 任务5：优化简历（SECTION 03 卡片，可展开做改写对比） =====
const tailorActive = ref(false)
const tailorResumeText = ref('')
const tailorJdText = ref('')
const tailorLoading = ref(false)
const tailorError = ref('')
const tailorResult = ref<any>(null)
const showDiff = ref(true)

async function runTailor() {
  if (!tailorResumeText.value.trim() || !tailorJdText.value.trim() || tailorLoading.value) return
  tailorLoading.value = true
  tailorError.value = ''
  tailorResult.value = null
  try {
    const res: any = await tailorResume(
      tailorResumeText.value,
      tailorJdText.value,
      '',  // matchResult 空串，后端照样跑
      undefined,
      true,  // showAnnotations = true 带改动说明
    )
    if (res?.result) {
      tailorResult.value = res
    } else {
      tailorError.value = res?.error || '改写失败，请重试'
    }
  } catch (e: any) {
    tailorError.value = e?.response?.data?.detail || e?.message || '网络错误'
  } finally {
    tailorLoading.value = false
  }
}
function resetTailor() {
  tailorResult.value = null
  tailorResumeText.value = ''
  tailorJdText.value = ''
  tailorError.value = ''
}
function useFromJobMatch() {
  // 如果用户刚在 SECTION 01 分析过 JD，把 jd_text 填过来（智能衔接）
  if (jdResult.value) {
    tailorJdText.value = jdResult.value.position_title
      ? JSON.stringify(jdResult.value)
      : (jdResult.value.jd_text || jdResult.value.raw || '')
  }
}

// ===== 任务6：数据看板（最近7天 / 状态分布 / 匹配分分布） =====
const applications = ref<any[]>([])
async function loadApplications() {
  try {
    const data: any = await listApplications()
    applications.value = data || []
  } catch { /* offline ok */ }
}

onMounted(async () => {
  try {
    await healthCheck()
    const data: any = await getTrackerStats()
    stats.value = data
    loadApplications()  // 顺便拉列表
  } catch { /* offline ok */ }
})
onUnmounted(() => {
  stopPolling()
})

// 最近 7 天每天的投递数
const weekTrend = computed(() => {
  const counts: { day: string; count: number; isToday: boolean }[] = []
  const now = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const key = `${d.getMonth() + 1}/${d.getDate()}`
    const startOfDay = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
    const endOfDay = startOfDay + 86400000
    const count = applications.value.filter(a => {
      const ts = new Date(a.created_at || a.updated_at).getTime()
      return ts >= startOfDay && ts < endOfDay
    }).length
    counts.push({ day: key, count, isToday: i === 0 })
  }
  return counts
})
const maxTrend = computed(() => Math.max(1, ...weekTrend.value.map(d => d.count)))

// 状态分布
const statusBreakdown = computed(() => {
  const order = ['待投递', '已投递', '初筛中', '面试中', '已发Offer', '已拒绝']
  const map: Record<string, number> = {}
  applications.value.forEach(a => { map[a.status] = (map[a.status] || 0) + 1 })
  return order.map(s => ({ status: s, count: map[s] || 0 }))
})
const totalApps = computed(() => applications.value.length)

// 匹配分分布
const scoreBuckets = computed(() => {
  const buckets = [
    { label: '0-59', min: 0, max: 59, count: 0 },
    { label: '60-69', min: 60, max: 69, count: 0 },
    { label: '70-79', min: 70, max: 79, count: 0 },
    { label: '80-89', min: 80, max: 89, count: 0 },
    { label: '90+', min: 90, max: 100, count: 0 },
  ]
  applications.value.forEach(a => {
    if (a.match_score == null) return
    const b = buckets.find(b => a.match_score >= b.min && a.match_score <= b.max)
    if (b) b.count++
  })
  return buckets
})
const maxScoreBucket = computed(() => Math.max(1, ...scoreBuckets.value.map(b => b.count)))

// ===== 欢迎条智能建议 =====
interface Advice {
  icon: string  // Element Plus icon name
  iconColor: string
  title: string
  desc: string
  cta: string
  ctaRoute: string
  priority: number
}

const todayAdvice = computed<Advice[]>(() => {
  const list: Advice[] = []
  const pending = pendingCount.value
  const interviewing = statusBreakdown.value.find((s: any) => s.status === '面试中')?.count || 0
  const offer = statusBreakdown.value.find((s: any) => s.status === '已发Offer')?.count || 0
  const match = matchAvg.value
  const total = totalCount.value
  const h = new Date().getHours()

  // 1. 待投递：最高优先级
  if (pending >= 3) {
    list.push({
      icon: 'Promotion', iconColor: '#f59e0b',
      title: `有 ${pending} 份简历待投递`,
      desc: '一键全流程让 AI 自动生成求职信和打招呼语',
      cta: '打开一键全流程',
      ctaRoute: '/',
      priority: 1,
    })
  } else if (pending > 0) {
    list.push({
      icon: 'EditPen', iconColor: '#3b82f6',
      title: `${pending} 份简历待打磨`,
      desc: '用 AI 针对目标 JD 改写，提升匹配分',
      cta: '去简历优化',
      ctaRoute: '/resume',
      priority: 1,
    })
  }

  // 2. ���试中
  if (interviewing > 0) {
    list.push({
      icon: 'Headset', iconColor: '#10b981',
      title: `${interviewing} 个面试进行中`,
      desc: '针对性打磨自我介绍，复盘高频追问',
      cta: 'JD 分析',
      ctaRoute: '/jd',
      priority: 2,
    })
  }

  // 3. 已发 Offer
  if (offer > 0) {
    list.push({
      icon: 'Trophy', iconColor: '#f59e0b',
      title: `${offer} 个 Offer 拿到手！`,
      desc: '生成一封得体的求职信作为回信',
      cta: '去求职信',
      ctaRoute: '/cover-letter',
      priority: 3,
    })
  }

  // 4. 匹配分偏低
  if (match !== null && match < 70 && total > 0) {
    list.push({
      icon: 'TrendCharts', iconColor: '#ef4444',
      title: `平均匹配分 ${match}，偏低`,
      desc: '先优化一份简历，匹配分能拉到 85+',
      cta: '快速改写',
      ctaRoute: '/resume',
      priority: 2,
    })
  }

  // 5. 全新用户（0 投递）
  if (total === 0 && pending === 0) {
    if (h < 12) {
      list.push({
        icon: 'Sunny', iconColor: '#f59e0b',
        title: '早上好，开始第一次求职吧',
        desc: '上传简历 → 选择 JD → AI 一键生成求职信',
        cta: '开始一键全流程',
        ctaRoute: '/',
        priority: 1,
      })
    } else if (h < 18) {
      list.push({
        icon: 'Sunny', iconColor: '#f59e0b',
        title: '下午好，上传简历开始 AI 辅助',
        desc: '从「简历优化」开始，5 分钟拿到定制版简历',
        cta: '上传简历',
        ctaRoute: '/resume',
        priority: 1,
      })
    } else {
      list.push({
        icon: 'Moon', iconColor: '#6366f1',
        title: '晚上好，准备一份定制简历',
        desc: 'AI 5 秒分析 JD 关键词，简历改写保留原事实',
        cta: '开始分析',
        ctaRoute: '/jd',
        priority: 1,
      })
    }
  }

  // 6. 兜底
  if (list.length === 0) {
    list.push({
      icon: 'Star', iconColor: '#3b82f6',
      title: '求职进展不错',
      desc: '可继续打磨简历迎战下一波机会',
      cta: '继续打磨',
      ctaRoute: '/resume',
      priority: 3,
    })
  }

  return list.sort((a, b) => a.priority - b.priority).slice(0, 2)
})

function goAdvice(route: string) {
  router.push(route)
}
</script>

<template>
  <div class="dash">
    <!-- ===== 顶部欢迎条 ===== -->
    <el-card class="welcome-card" shadow="never">
      <div class="welcome-row">
        <div class="welcome-text">
          <div class="welcome-greet">
            <el-icon class="welcome-icon"><Sunny /></el-icon>
            <span>{{ greeting() }}，</span>
            <span class="welcome-name">{{ userName }}</span>
          </div>
          <div class="welcome-tip">今天 {{ today() }}，目标搞定 {{ todayJobTarget }} 份投递</div>
        </div>
        <div class="welcome-stats">
          <div class="stat-item">
            <div class="stat-num">{{ fmt(totalCount) }}</div>
            <div class="stat-lbl">累计投递</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num stat-num--accent">{{ fmt(matchAvg) }}</div>
            <div class="stat-lbl">平均匹配分</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-num stat-num--gold">{{ fmt(pendingCount) }}</div>
            <div class="stat-lbl">待投递</div>
          </div>
        </div>
      </div>

      <!-- 智能建议条 — 填满空白区 -->
      <div class="advice-strip">
        <div
          v-for="(a, i) in todayAdvice"
          :key="i"
          class="advice-card"
          :class="{ primary: a.priority === 1 }"
          @click="goAdvice(a.ctaRoute)"
        >
          <div class="advice-icon" :style="{ background: a.iconColor + '18', color: a.iconColor }">
            <el-icon :size="22"><component :is="a.icon" /></el-icon>
          </div>
          <div class="advice-body">
            <div class="advice-title">{{ a.title }}</div>
            <div class="advice-desc">{{ a.desc }}</div>
          </div>
          <div class="advice-cta" :style="{ color: a.iconColor }">
            {{ a.cta }}
            <el-icon class="advice-arrow"><Right /></el-icon>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ===== 三大功能 ===== -->
    <div class="section-title">
      <span class="section-en">QUICK START</span>
      <span class="section-cn">快速开始</span>
    </div>

    <el-row :gutter="16">
      <!-- SECTION 01：智能匹配分析 -->
      <el-col :xs="24" :md="14">
        <el-card class="feat-card" shadow="never" :body-style="{ padding: '20px' }">
          <div class="feat-head">
            <div class="feat-num">01</div>
            <div>
              <div class="feat-title">智能匹配分析</div>
              <div class="feat-sub">把 JD 贴进来 → AI 输出匹配度 / 关键技能 / 改写建议</div>
            </div>
          </div>

          <!-- 关闭态 -->
          <template v-if="!jdActive && !jdResult">
            <div class="feat-quote">
              <el-icon><ChatLineRound /></el-icon>
              <span>粘贴一份目标职位的 JD，AI 在 ~8s 内输出：</span>
              <ul class="quote-list">
                <li>职位核心要求（硬技能、经验、学历）</li>
                <li>你的简历可能缺失的关键词</li>
                <li>针对性的改写建议</li>
              </ul>
            </div>
            <div class="feat-action">
              <el-button type="primary" @click="jdActive = true" plain>
                开始分析 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>

          <!-- 展开态：输入 -->
          <template v-else-if="jdActive && !jdResult">
            <el-input
              v-model="jdInput"
              type="textarea"
              :rows="7"
              placeholder="把职位描述粘到这里。例如：&#10;招聘 Python 后端开发工程师，3年经验，熟悉 FastAPI/MySQL/Redis..."
              :disabled="jdLoading"
            />
            <div class="feat-action">
              <el-button @click="jdActive = false; jdInput = ''">取消</el-button>
              <el-button
                type="primary"
                :loading="jdLoading"
                :disabled="!jdInput.trim()"
                @click="runAnalyze"
              >
                {{ jdLoading ? 'AI 分析中…' : '开始分析' }}
              </el-button>
            </div>
            <el-alert v-if="jdError" :title="jdError" type="error" show-icon :closable="false" style="margin-top: 12px" />
          </template>

          <!-- 结果态 -->
          <template v-else>
            <div class="result-head">
              <div class="result-position">
                <el-icon class="result-icon"><Position /></el-icon>
                <span>{{ positionTitle }}</span>
              </div>
              <el-button link type="primary" @click="resetJd" size="small">重新分析</el-button>
            </div>
            <div v-if="skillsFound.length" class="result-skills">
              <span v-for="s in skillsFound.slice(0, 12)" :key="s" class="skill-chip">{{ s }}</span>
            </div>
            <div v-else class="result-empty">未提取到关键技能</div>
            <div v-if="jdResult.responsibilities || jdResult.core_responsibilities" class="result-block">
              <div class="block-kicker">核心职责</div>
              <div class="block-text">{{ jdResult.responsibilities || jdResult.core_responsibilities }}</div>
            </div>
            <div class="feat-action">
              <el-button type="primary" @click="goOptimize">
                带着分析去优化简历 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>
        </el-card>
      </el-col>

      <!-- SECTION 02：一键全流程 -->
      <el-col :xs="24" :md="10">
        <el-card class="feat-card feat-card--highlight" shadow="never" :body-style="{ padding: '20px' }">
          <div class="feat-head">
            <div class="feat-num feat-num--accent">02</div>
            <div>
              <div class="feat-title">一键全流程</div>
              <div class="feat-sub">分析 + 改写 + 求职信，AI 全跑通</div>
            </div>
          </div>

          <template v-if="!pipelineActive && pipelineStatus !== 'SUCCESS'">
            <div class="feat-quote feat-quote--sm">
              <span class="meta-row">
                <el-icon><Clock /></el-icon>
                <span>约 90 秒</span>
                <el-divider direction="vertical" />
                <el-icon><MagicStick /></el-icon>
                <span>4 个 Agent 协同</span>
              </span>
            </div>
            <div class="feat-action">
              <el-button type="primary" @click="pipelineActive = true" class="cta-big">
                开始全流程
                <el-icon class="el-icon--right"><Promotion /></el-icon>
              </el-button>
            </div>
          </template>

          <template v-else-if="pipelineActive && !pipelineRunning && pipelineStatus !== 'SUCCESS'">
            <div class="upload-row">
              <el-upload
                :auto-upload="true"
                :before-upload="beforePipelineUpload"
                :on-change="handlePipelineFile"
                :show-file-list="false"
                accept=".docx,.pdf"
                class="pipeline-upload"
              >
                <el-button :loading="pipelineUploading" plain size="small">
                  <el-icon><UploadFilled /></el-icon>
                  {{ pipelineUploading ? '解析中…' : '上传简历文件' }}
                </el-button>
              </el-upload>
              <span v-if="pipelineUploadedName" class="upload-hint">
                <el-icon color="var(--color-success)"><CircleCheck /></el-icon>
                {{ pipelineUploadedName }} 已填入下方
              </span>
              <span v-else class="upload-hint upload-hint--muted">支持 .docx / .pdf，≤5MB</span>
            </div>
            <el-form label-position="top" size="default" style="margin-top: 12px">
              <el-form-item label="简历全文">
                <el-input v-model="pipelineResume" type="textarea" :rows="4" placeholder="把你的完整简历粘到这里，或点击上方按钮上传文件自动填充" />
              </el-form-item>
              <el-form-item label="目标 JD">
                <el-input v-model="pipelineJd" type="textarea" :rows="3" placeholder="把要投递的职位描述粘到这里" />
              </el-form-item>
            </el-form>
            <div class="feat-action">
              <el-button @click="pipelineActive = false; pipelineResume=''; pipelineJd=''; pipelineUploadedName=''">取消</el-button>
              <el-button
                type="primary"
                :disabled="!pipelineResume.trim() || !pipelineJd.trim()"
                @click="runPipeline"
              >
                开始全流程
                <el-icon class="el-icon--right"><Promotion /></el-icon>
              </el-button>
            </div>
            <el-alert v-if="pipelineError" :title="pipelineError" type="error" show-icon :closable="false" style="margin-top: 12px" />
          </template>

          <template v-else-if="pipelineRunning">
            <el-steps :active="currentStepIndex" finish-status="success" direction="vertical">
              <el-step v-for="s in pipelineSteps" :key="s.key" :title="s.label" />
            </el-steps>
            <el-progress :percentage="pipelineProgress" :stroke-width="6" style="margin: 16px 0 8px" />
            <div class="progress-meta">
              <span>AI 正在跑，已完成 {{ pipelineProgress }}%</span>
            </div>
          </template>

          <template v-else>
            <el-result icon="success" title="全流程完成" sub-title="已生成 JD 分析 / 简历改写 / 求职信">
              <template #extra>
                <el-button type="primary" @click="router.push('/resume')">查看改写结果</el-button>
                <el-button @click="router.push('/cover-letter')">查看求职信</el-button>
                <el-button link @click="pipelineActive = false; pipelineStatus = ''; pipelineResume = ''; pipelineJd = ''; pipelineTaskId = ''; pipelineError = ''; pipelineProgress = 0">再跑一次</el-button>
              </template>
            </el-result>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== SECTION 03：优化简历（任务5，可展开做改写对比） ===== -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card class="feat-card" shadow="never" :body-style="{ padding: '20px' }">
          <div class="feat-head feat-head--inline">
            <div class="feat-num feat-num--muted">03</div>
            <div>
              <div class="feat-title">优化简历</div>
              <div class="feat-sub">基于匹配诊断，针对性改写简历，保留原事实</div>
            </div>
            <div style="margin-left: auto">
              <el-button v-if="!tailorActive && !tailorResult" type="primary" plain @click="tailorActive = true">
                快速改写 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
              <el-button v-else-if="!tailorActive && tailorResult" link type="primary" @click="tailorActive = true">
                再写一次
              </el-button>
            </div>
          </div>

          <!-- 展开态：输入 -->
          <template v-if="tailorActive && !tailorResult">
            <el-row :gutter="16">
              <el-col :span="12">
                <div class="form-label">简历全文</div>
                <el-input
                  v-model="tailorResumeText"
                  type="textarea"
                  :rows="6"
                  placeholder="把你的简历粘到这里"
                  :disabled="tailorLoading"
                />
              </el-col>
              <el-col :span="12">
                <div class="form-label">
                  目标 JD
                  <el-link v-if="jdResult" type="primary" :underline="false" @click="useFromJobMatch" style="margin-left: 8px">
                    从上方分析填充
                  </el-link>
                </div>
                <el-input
                  v-model="tailorJdText"
                  type="textarea"
                  :rows="6"
                  placeholder="把要改写针对的 JD 粘到这里"
                  :disabled="tailorLoading"
                />
              </el-col>
            </el-row>
            <div class="feat-action">
              <el-button @click="tailorActive = false; tailorResumeText=''; tailorJdText=''">取消</el-button>
              <el-button type="primary" :loading="tailorLoading" :disabled="!tailorResumeText.trim() || !tailorJdText.trim()" @click="runTailor">
                {{ tailorLoading ? 'AI 改写中…' : '开始改写' }}
              </el-button>
            </div>
            <el-alert v-if="tailorError" :title="tailorError" type="error" show-icon :closable="false" style="margin-top: 12px" />
          </template>

          <!-- 结果态：原 vs 改写对比 -->
          <template v-if="tailorResult">
            <div class="diff-head">
              <el-radio-group v-model="showDiff" size="small">
                <el-radio-button :value="true">对比</el-radio-button>
                <el-radio-button :value="false">仅改写</el-radio-button>
              </el-radio-group>
              <el-button link type="primary" size="small" @click="resetTailor">重新改写</el-button>
            </div>

            <div v-if="showDiff" class="diff-grid">
              <div class="diff-col">
                <div class="diff-col-title">原简历</div>
                <div class="diff-content">{{ tailorResumeText }}</div>
              </div>
              <div class="diff-arrow">
                <el-icon><Right /></el-icon>
              </div>
              <div class="diff-col">
                <div class="diff-col-title diff-col-title--accent">改写后</div>
                <div class="diff-content diff-content--accent">{{ tailorResult.result }}</div>
              </div>
            </div>
            <div v-else class="diff-single">
              <div class="diff-col-title diff-col-title--accent">改写后简历</div>
              <div class="diff-content diff-content--accent">{{ tailorResult.result }}</div>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 任务6：数据看板 ===== -->
    <div v-if="totalApps > 0" class="board">
      <div class="board-title">
        <span class="board-en">DASHBOARD</span>
        <span class="board-cn">求职进度 · 共 {{ totalApps }} 条投递记录</span>
      </div>
      <el-row :gutter="16">
        <!-- 最近 7 天 -->
        <el-col :xs="24" :md="14">
          <el-card class="board-card" shadow="never">
            <div class="board-kicker">最近 7 天 · LAST 7 DAYS</div>
            <div class="bar-chart">
              <div v-for="d in weekTrend" :key="d.day" class="bar-col">
                <div class="bar-num" :class="{ 'bar-num--today': d.isToday }">{{ d.count }}</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ height: (d.count / maxTrend * 100) + '%' }"
                       :class="{ 'bar-fill--today': d.isToday }"></div>
                </div>
                <div class="bar-day" :class="{ 'bar-day--today': d.isToday }">{{ d.day }}</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 状态分布 + 匹配分 -->
        <el-col :xs="24" :md="10">
          <el-card class="board-card" shadow="never">
            <div class="board-kicker">状态分布 · BY STATUS</div>
            <div v-for="s in statusBreakdown" :key="s.status" class="status-row">
              <span class="status-name">{{ s.status }}</span>
              <div class="status-track">
                <div class="status-fill"
                     :style="{ width: totalApps ? (s.count / totalApps * 100) + '%' : '0%' }"></div>
              </div>
              <span class="status-count">{{ s.count }}</span>
            </div>
            <div class="board-kicker" style="margin-top: 16px">匹配分分布 · SCORE</div>
            <div v-for="b in scoreBuckets" :key="b.label" class="score-row">
              <span class="score-label">{{ b.label }}</span>
              <div class="score-track">
                <div class="score-fill" :style="{ width: (b.count / maxScoreBucket * 100) + '%' }"></div>
              </div>
              <span class="score-count">{{ b.count }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    <div v-else class="board-empty">
      <el-icon><DataAnalysis /></el-icon>
      <span>暂无投递记录。开始一次"一键全流程"或到 <el-link type="primary" :underline="false" @click="router.push('/cover-letter')">求职信</el-link> 页面添加吧。</span>
    </div>
  </div>
</template>

<style scoped>
/* ===== Dashboard 顶部 ===== */
.dash { padding: 0; max-width: 1200px; margin: 0 auto; }

.welcome-card {
  background: linear-gradient(135deg, var(--accent), var(--accent-hover));
  color: #fff;
  border: 0 !important;
  margin-bottom: 24px;
}
.welcome-card :deep(.el-card__body) { padding: 24px 28px; }
.welcome-row {
  display: flex; justify-content: space-between; align-items: center;
  gap: 24px;
}
.welcome-text { flex: 1; }
.welcome-greet {
  display: flex; align-items: center; gap: 8px;
  font-size: 18px; font-weight: 600;
  margin-bottom: 4px;
}
.welcome-icon { font-size: 18px; }
.welcome-name {
  background: rgba(255,255,255,0.15);
  padding: 2px 10px;
  border-radius: 4px;
  font-weight: 700;
}
.welcome-tip { font-size: 13px; opacity: 0.85; }

.welcome-stats { display: flex; align-items: center; gap: 24px; }
.stat-item { text-align: center; min-width: 56px; }
.stat-num {
  font-size: 24px; font-weight: 700; line-height: 1.2;
  color: #fff;
  font-variant-numeric: tabular-nums;
}
.stat-num--accent { color: #fef3c7; }
.stat-num--gold { color: #fde68a; }
.stat-lbl {
  font-size: 11px; opacity: 0.85;
  margin-top: 2px;
  letter-spacing: 0.05em;
}
.stat-divider {
  width: 1px; height: 32px;
  background: rgba(255,255,255,0.25);
}

/* ===== 区块标题 ===== */
.section-title {
  display: flex; align-items: baseline; gap: 10px;
  margin: 8px 0 16px;
}
.section-en {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--accent);
}
.section-cn {
  font-size: 16px; font-weight: 600; color: var(--text-primary);
}

/* ===== 功能卡 ===== */
.feat-card { border-radius: 10px !important; }
.feat-card--highlight { border: 1px solid var(--accent) !important; }
.feat-head {
  display: flex; gap: 14px; align-items: center;
  margin-bottom: 16px;
}
.feat-head--inline { margin-bottom: 0; }
.feat-num {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-deepest);
  color: var(--text-primary);
  border-radius: 8px;
  font-size: 14px; font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0;
}
.feat-num--accent { background: var(--accent); color: #fff; }
.feat-num--muted { background: var(--bg-deepest); color: var(--text-muted); }
.feat-title {
  font-size: 17px; font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}
.feat-sub {
  font-size: 12px; color: var(--text-muted);
  margin-top: 2px;
  line-height: 1.4;
}

/* ===== 引用/说明区 ===== */
.feat-quote {
  background: var(--bg-deepest);
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  display: flex; flex-direction: column; gap: 6px;
}
.feat-quote--sm { flex-direction: row; align-items: center; }
.feat-quote .el-icon { color: var(--accent); vertical-align: middle; }
.quote-list {
  margin: 4px 0 0; padding-left: 20px;
  color: var(--text-muted);
  font-size: 12px;
}
.quote-list li { margin: 2px 0; }
.meta-row {
  display: flex; align-items: center; gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}
.meta-row .el-divider--vertical { margin: 0 4px; }

/* ===== 按钮区 ===== */
.feat-action {
  margin-top: 14px;
  display: flex; gap: 8px; justify-content: flex-end;
}
.cta-big {
  padding: 10px 20px !important;
  font-weight: 600 !important;
}

/* 一键全流程 - 上传文件行 */
.upload-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  background: var(--bg-deepest);
  border: 1px dashed var(--border-input);
  border-radius: 8px;
}
.upload-hint {
  font-size: 12px; color: var(--text-secondary);
  display: inline-flex; align-items: center; gap: 4px;
}
.upload-hint--muted { color: var(--text-muted); }
.pipeline-upload { display: inline-block; }

/* ===== 结果区 ===== */
.result-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.result-position {
  display: flex; align-items: center; gap: 8px;
  font-size: 15px; font-weight: 600; color: var(--text-primary);
}
.result-icon { color: var(--accent); font-size: 18px; }
.result-skills {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-bottom: 12px;
}
.skill-chip {
  font-size: 12px; padding: 3px 10px;
  background: var(--accent-subtle);
  color: var(--accent);
  border-radius: 4px;
}
.result-empty { color: var(--text-muted); font-size: 12px; margin-bottom: 12px; }
.result-block {
  background: var(--bg-deepest);
  border-left: 3px solid var(--accent);
  padding: 10px 14px;
  border-radius: 0 4px 4px 0;
  margin-bottom: 12px;
}
.block-kicker {
  font-size: 10px; font-weight: 700; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--accent);
  margin-bottom: 4px;
}
.block-text { font-size: 13px; line-height: 1.6; color: var(--text-primary); }

/* ===== 任务5：改写对比 ===== */
.diff-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.diff-grid {
  display: grid; grid-template-columns: 1fr 32px 1fr; gap: 12px;
  align-items: stretch;
}
.diff-col {
  background: var(--bg-deepest);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex; flex-direction: column;
  max-height: 400px; overflow: hidden;
}
.diff-col-title {
  font-size: 11px; font-weight: 700; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--text-muted);
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle, #e2e8f0);
}
.diff-col-title--accent { color: var(--accent); }
.diff-content {
  flex: 1; overflow: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word;
  color: var(--text-primary);
  margin: 0;
}
.diff-content--accent { background: var(--accent-subtle); padding: 12px; border-radius: 6px; }
.diff-arrow {
  display: flex; align-items: center; justify-content: center;
  color: var(--accent); font-size: 20px;
}
.diff-single { background: var(--bg-deepest); border-radius: 8px; padding: 16px; }

/* ===== 进度 ===== */
.progress-meta { font-size: 12px; color: var(--text-muted); text-align: right; }

/* ===== 任务6：数据看板 ===== */
.board { margin-top: 24px; }
.board-title {
  display: flex; align-items: baseline; gap: 12px;
  margin: 8px 0 12px;
}
.board-en {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--accent);
}
.board-cn { font-size: 14px; color: var(--text-primary); font-weight: 600; }
.board-card {
  border-radius: 10px !important;
  background: var(--bg-card) !important;
}
.board-kicker {
  font-size: 10px; font-weight: 700; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--text-muted);
  margin-bottom: 14px;
}

/* 7 天条形图 */
.bar-chart {
  display: flex; align-items: flex-end; gap: 8px;
  height: 180px; padding: 0 4px;
}
.bar-col {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; gap: 4px;
  height: 100%;
}
.bar-num {
  font-size: 11px; font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-secondary);
}
.bar-num--today { color: var(--accent); }
.bar-track {
  flex: 1; width: 100%;
  background: var(--bg-deepest);
  border-radius: 4px 4px 0 0;
  display: flex; align-items: flex-end;
  overflow: hidden;
}
.bar-fill {
  width: 100%; min-height: 2px;
  background: var(--text-muted);
  transition: height 0.4s;
}
.bar-fill--today { background: var(--accent); }
.bar-day {
  font-size: 11px; color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}
.bar-day--today { color: var(--accent); font-weight: 700; }

/* 状态行 + 分数行 */
.status-row, .score-row {
  display: grid;
  grid-template-columns: 56px 1fr 32px;
  align-items: center; gap: 8px;
  margin-bottom: 6px;
}
.status-name, .score-label {
  font-size: 11px; color: var(--text-secondary);
}
.score-label { font-family: 'JetBrains Mono', monospace; }
.status-track, .score-track {
  height: 8px; background: var(--bg-deepest);
  border-radius: 4px; overflow: hidden;
}
.status-fill, .score-fill {
  height: 100%; background: var(--accent);
  border-radius: 4px;
  transition: width 0.4s;
}
.status-count, .score-count {
  font-size: 11px; font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  text-align: right; color: var(--text-primary);
}

/* 空状态 */
.board-empty {
  margin-top: 32px;
  padding: 48px 24px;
  text-align: center;
  background: var(--bg-deepest);
  border-radius: 10px;
  color: var(--text-muted);
  font-size: 14px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.board-empty .el-icon { font-size: 20px; }
</style>
