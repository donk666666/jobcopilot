<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTrackerStats, healthCheck, analyzeJD, tailorResume, listApplications } from '@/api'

const router = useRouter()
const stats = ref({ total: 0, by_status: {} as Record<string, number>, avg_match_score: 0 })
const userName = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    return u.nickname || u.username || '求职者'
  } catch { return '求职者' }
})

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

const todayDate = () => {
  const d = new Date()
  const weekdays = ['周日','周一','周二','周三','周四','周五','周六']
  return `${d.getMonth() + 1}月${d.getDate()}日 · ${weekdays[d.getDay()]}`
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
const salaryText = computed(() => {
  const s = jdResult.value?.salary
  if (!s) return null
  if (typeof s === 'string') return s
  if (s.range) return s.range
  return null
})

// ===== 任务5：优化简历 =====
const tailorActive = ref(false)
const tailorResumeText = ref('')
const tailorJdText = ref('')
const tailorLoading = ref(false)
const tailorError = ref('')
const tailorResult = ref<any>(null)

async function runTailor() {
  if (!tailorResumeText.value.trim() || !tailorJdText.value.trim() || tailorLoading.value) return
  tailorLoading.value = true
  tailorError.value = ''
  tailorResult.value = null
  try {
    const res: any = await tailorResume(
      tailorResumeText.value,
      tailorJdText.value,
      '',
      undefined,
      true,
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
  if (jdResult.value) {
    tailorJdText.value = jdResult.value.position_title
      ? JSON.stringify(jdResult.value)
      : (jdResult.value.jd_text || jdResult.value.raw || '')
  }
}

// ===== 任务6：数据看板 =====
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
    loadApplications()
  } catch { /* offline ok */ }
})
onUnmounted(() => { /* 旧的 stopPolling 已删除 */ })

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

const statusBreakdown = computed(() => {
  const order = ['待投递', '已投递', '初筛中', '面试中', '已发Offer', '已拒绝']
  const map: Record<string, number> = {}
  applications.value.forEach(a => { map[a.status] = (map[a.status] || 0) + 1 })
  return order.map(s => ({ status: s, count: map[s] || 0 }))
})
const totalApps = computed(() => applications.value.length)

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

// ===== 顶部工作台快捷入口（去掉"ReAct Agent"字眼） =====
interface QuickEntry {
  key: string
  label: string
  sub: string
  icon: string
  badge?: string
  to: string
}
const quickEntries = computed<QuickEntry[]>(() => [
  {
    key: 'jd',
    label: '在线沟通',
    sub: '解析 JD 关键词，匹配度评估',
    icon: 'ChatDotRound',
    badge: pendingCount.value > 0 ? `${pendingCount.value} 待处理` : undefined,
    to: '/jd',
  },
  {
    key: 'resume',
    label: '简历评估',
    sub: '针对性改写，保留原事实，5 维雷达图评分',
    icon: 'EditPen',
    to: '/resume',
  },
  {
    key: 'tracker',
    label: '投递管理',
    sub: '状态机跟踪，记录每一次沟通反馈',
    icon: 'List',
    to: '/tracker',
  },
])
function goEntry(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="dash">
    <!-- ===== 顶部工作台（招聘网站风）===== -->
    <div class="workspace">
      <div class="ws-top">
        <div class="ws-greet">
          <div class="ws-hi">{{ greeting() }}，{{ userName }}</div>
          <div class="ws-date">{{ todayDate() }}</div>
        </div>
        <div class="ws-searchbar">
          <el-icon class="ws-search-icon"><Search /></el-icon>
          <input placeholder="搜索职位 / 公司 / JD 关键词" class="ws-search-input" />
          <button class="ws-search-btn">搜 索</button>
        </div>
        <div class="ws-actions">
          <button class="ws-action" @click="router.push('/jd')">
            <el-icon><ChatDotRound /></el-icon>
            <span>在线沟通</span>
          </button>
        </div>
      </div>

      <div class="ws-stats">
        <div class="ws-stat">
          <div class="ws-stat-label">累计投递</div>
          <div class="ws-stat-val">{{ fmt(totalCount) }}</div>
        </div>
        <div class="ws-stat">
          <div class="ws-stat-label">待投递</div>
          <div class="ws-stat-val ws-stat-val--warm">{{ fmt(pendingCount) }}</div>
        </div>
        <div class="ws-stat">
          <div class="ws-stat-label">平均匹配分</div>
          <div class="ws-stat-val ws-stat-val--gold">{{ fmt(matchAvg) }}<span v-if="matchAvg !== null" class="ws-stat-unit">分</span></div>
        </div>
        <div class="ws-stat ws-stat--cta">
          <button class="ws-publish" @click="router.push('/tracker')">
            <el-icon><Plus /></el-icon>
            <span>记录一次新投递</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ===== 快捷入口（4 卡片紧凑列表，Boss 风）===== -->
    <div class="quick">
      <div class="quick-head">
        <span class="quick-title">找工作 · 快捷入口</span>
        <span class="quick-sub">从职位投递到简历打磨，每一步都有 AI 帮忙</span>
      </div>
      <div class="quick-grid">
        <div
          v-for="q in quickEntries"
          :key="q.key"
          class="quick-card"
          @click="goEntry(q.to)"
        >
          <div class="quick-icon">
            <el-icon :size="22"><component :is="q.icon" /></el-icon>
          </div>
          <div class="quick-body">
            <div class="quick-label">
              {{ q.label }}
              <span v-if="q.badge" class="quick-badge">{{ q.badge }}</span>
            </div>
            <div class="quick-sub-text">{{ q.sub }}</div>
          </div>
          <el-icon class="quick-arrow"><Right /></el-icon>
        </div>
      </div>
    </div>

    <!-- ===== 功能模块：JD 分析 + 简历改写（双栏任务卡）===== -->
    <div class="modules">
      <!-- 左侧：JD 分析 -->
      <div class="module-card">
        <div class="module-head">
          <div class="module-icon module-icon--green">
            <el-icon :size="22"><Document /></el-icon>
          </div>
          <div class="module-head-text">
            <div class="module-title">JD 分析</div>
            <div class="module-sub">粘贴目标岗位描述，AI 自动提取核心要求</div>
          </div>
        </div>

        <div v-if="!jdActive && !jdResult" class="module-body">
          <ul class="feature-list">
            <li><el-icon><Check /></el-icon>职位核心要求（硬技能、经验、学历）</li>
            <li><el-icon><Check /></el-icon>简历可能缺失的关键词</li>
            <li><el-icon><Check /></el-icon>针对性的改写建议</li>
          </ul>
          <div class="module-cta">
            <button class="module-btn module-btn--primary" @click="jdActive = true">
              开始分析
              <el-icon><ArrowRight /></el-icon>
            </button>
            <span class="module-hint">约 8 秒</span>
          </div>
        </div>

        <div v-else-if="jdActive && !jdResult" class="module-body">
          <textarea
            v-model="jdInput"
            class="module-textarea"
            placeholder="把职位描述粘到这里。例如：&#10;招聘 Python 后端开发工程师，3年经验，熟悉 FastAPI/MySQL/Redis..."
            rows="8"
          ></textarea>
          <div class="module-cta">
            <button class="module-btn module-btn--ghost" @click="jdActive = false; jdInput = ''">取消</button>
            <button class="module-btn module-btn--primary" :disabled="!jdInput.trim() || jdLoading" @click="runAnalyze">
              {{ jdLoading ? 'AI 分析中…' : '开始分析' }}
            </button>
          </div>
          <div v-if="jdError" class="module-error">
            <el-icon><Warning /></el-icon>
            {{ jdError }}
          </div>
        </div>

        <div v-else class="module-body module-body--result">
          <div class="result-card">
            <div class="result-card-head">
              <h4 class="result-card-title">{{ positionTitle }}</h4>
              <span v-if="salaryText" class="result-card-salary">{{ salaryText }}</span>
            </div>
            <div v-if="jdResult.company_name || jdResult.location" class="result-meta">
              <span v-if="jdResult.company_name">{{ jdResult.company_name }}</span>
              <span v-if="jdResult.location">{{ jdResult.location }}</span>
              <span v-if="jdResult.experience">{{ jdResult.experience }}</span>
              <span v-if="jdResult.education">{{ jdResult.education }}</span>
            </div>
            <div v-if="skillsFound.length" class="result-tags">
              <span v-for="s in skillsFound.slice(0, 10)" :key="s" class="result-tag">{{ s }}</span>
            </div>
            <div v-if="jdResult.responsibilities || jdResult.core_responsibilities" class="result-desc">
              <div class="result-desc-label">岗位职责</div>
              <div class="result-desc-text">{{ jdResult.responsibilities || jdResult.core_responsibilities }}</div>
            </div>
          </div>
          <div class="module-cta">
            <button class="module-btn module-btn--ghost" @click="resetJd">重新分析</button>
            <button class="module-btn module-btn--primary" @click="goOptimize">
              带着分析去优化简历
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧：简历优化 -->
      <div class="module-card">
        <div class="module-head">
          <div class="module-icon module-icon--blue">
            <el-icon :size="22"><EditPen /></el-icon>
          </div>
          <div class="module-head-text">
            <div class="module-title">简历优化</div>
            <div class="module-sub">独立改写：贴简历 + JD，AI 输出针对性版本</div>
          </div>
        </div>

        <div v-if="!tailorActive && !tailorResult" class="module-body">
          <ul class="feature-list">
            <li><el-icon><Check /></el-icon>保留简历原事实，不会"编造"经历</li>
            <li><el-icon><Check /></el-icon>带改动注释，看清每处调整原因</li>
            <li><el-icon><Check /></el-icon>约 9 秒生成 1500 字内简历</li>
          </ul>
          <div class="module-cta">
            <button class="module-btn module-btn--primary" @click="tailorActive = true">
              快速改写
              <el-icon><ArrowRight /></el-icon>
            </button>
            <span class="module-hint">需简历+JD</span>
          </div>
        </div>

        <div v-else-if="tailorResult" class="module-body module-body--result">
          <div class="result-card">
            <div class="result-card-head">
              <h4 class="result-card-title">改写完成</h4>
              <span class="result-card-salary result-card-salary--ok">已完成</span>
            </div>
            <div class="result-desc">
              <div class="result-desc-label">改写预览</div>
              <div class="result-desc-text">{{ tailorResult.result.slice(0, 240) }}{{ tailorResult.result.length > 240 ? '...' : '' }}</div>
            </div>
          </div>
          <div class="module-cta">
            <button class="module-btn module-btn--ghost" @click="tailorActive = true">再写一次</button>
            <button class="module-btn module-btn--primary" @click="router.push('/resume')">
              查看完整结果
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
        </div>

        <div v-else class="module-body">
          <div class="form-grid">
            <div class="form-field">
              <label class="form-label">简历全文</label>
              <textarea v-model="tailorResumeText" class="module-textarea" rows="6" placeholder="把你的简历粘到这里"></textarea>
            </div>
            <div class="form-field">
              <label class="form-label">
                目标 JD
                <el-link v-if="jdResult" type="primary" :underline="false" @click="useFromJobMatch" class="link-fill">从上方分析填充</el-link>
              </label>
              <textarea v-model="tailorJdText" class="module-textarea" rows="6" placeholder="把要改写针对的 JD 粘到这里"></textarea>
            </div>
          </div>
          <div class="module-cta">
            <button class="module-btn module-btn--ghost" @click="tailorActive = false; tailorResumeText=''; tailorJdText=''">取消</button>
            <button class="module-btn module-btn--primary" :disabled="!tailorResumeText.trim() || !tailorJdText.trim() || tailorLoading" @click="runTailor">
              {{ tailorLoading ? 'AI 改写中…' : '开始改写' }}
            </button>
          </div>
          <div v-if="tailorError" class="module-error">
            <el-icon><Warning /></el-icon>
            {{ tailorError }}
          </div>
        </div>
      </div>
    </div>
    <div v-if="totalApps > 0" class="board">
      <div class="board-head">
        <span class="board-title">求职数据 · 共 {{ totalApps }} 条投递记录</span>
        <button class="module-btn module-btn--ghost" @click="router.push('/tracker')">
          全部投递
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </button>
      </div>
      <div class="board-grid">
        <div class="board-card">
          <div class="board-kicker">最近 7 天</div>
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
        </div>

        <div class="board-card">
          <div class="board-kicker">状态分布</div>
          <div v-for="s in statusBreakdown" :key="s.status" class="status-row">
            <span class="status-name">{{ s.status }}</span>
            <div class="status-track">
              <div class="status-fill" :style="{ width: totalApps ? (s.count / totalApps * 100) + '%' : '0%' }"></div>
            </div>
            <span class="status-count">{{ s.count }}</span>
          </div>
        </div>

        <div class="board-card">
          <div class="board-kicker">匹配分分布</div>
          <div v-for="b in scoreBuckets" :key="b.label" class="status-row">
            <span class="status-name status-name--mono">{{ b.label }}</span>
            <div class="status-track">
              <div class="status-fill status-fill--gold" :style="{ width: (b.count / maxScoreBucket * 100) + '%' }"></div>
            </div>
            <span class="status-count">{{ b.count }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="board-empty">
      <el-icon><DataAnalysis /></el-icon>
      <span>暂无投递记录。</span>
      <el-link type="primary" :underline="false" @click="router.push('/cover-letter')">去求职信页面添加</el-link>
    </div>
  </div>
</template>

<style scoped>
/* ============================================================
   Dashboard — Boss 直聘 / 58同城 招聘网站风
   - 暖灰底 (#F5F6F7)，白卡，6px 圆角，硬阴影
   - 招聘绿 (#00B574) 主色，橙红 (#FF6F00) 强调
   - 高信息密度，紧凑间距
   ============================================================ */

.dash {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
}

/* ===== 顶部工作台 ===== */
.workspace {
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  margin-bottom: var(--gap-lg);
  overflow: hidden;
}
.ws-top {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: #fff;
}
.ws-greet { min-width: 200px; }
.ws-hi {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}
.ws-date {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}
.ws-searchbar {
  flex: 1;
  max-width: 480px;
  display: flex;
  align-items: center;
  height: 36px;
  border: 2px solid var(--border-input);
  border-radius: var(--radius-input);
  overflow: hidden;
  transition: border-color var(--t-fast);
}
.ws-searchbar:focus-within {
  border-color: var(--accent);
}
.ws-search-icon {
  padding: 0 10px;
  color: var(--text-muted);
  font-size: 14px;
}
.ws-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-primary);
  font-family: inherit;
}
.ws-search-input::placeholder {
  color: var(--text-muted);
}
.ws-search-btn {
  height: 100%;
  padding: 0 18px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--t-fast);
}
.ws-search-btn:hover { background: var(--accent-hover); }

.ws-actions {
  margin-left: auto;
  display: flex;
  gap: var(--gap-sm);
}
.ws-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  background: var(--accent-subtle);
  border: none;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-input);
  cursor: pointer;
  font-family: inherit;
}
.ws-action:hover {
  background: var(--accent);
  color: #fff;
}

/* 工作台统计条 */
.ws-stats {
  display: flex;
  align-items: stretch;
  background: #fafbfc;
  border-top: 1px solid var(--border-subtle);
}
.ws-stat {
  flex: 1;
  padding: 12px 20px;
  border-right: 1px solid var(--border-subtle);
}
.ws-stat:last-child { border-right: 0; }
.ws-stat--cta { background: transparent; flex: 0 0 auto; padding: 0; display: flex; align-items: center; }
.ws-stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.ws-stat-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.ws-stat-val--accent { color: var(--accent); }
.ws-stat-val--warm   { color: var(--accent-warm); }
.ws-stat-val--gold   { color: var(--accent-gold); }
.ws-stat-unit {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 2px;
}
.ws-publish {
  height: 100%;
  padding: 0 22px;
  border: none;
  background: var(--accent-warm);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background var(--t-fast);
}
.ws-publish:hover { background: #e55f00; }

/* ===== 快捷入口 ===== */
.quick {
  margin-bottom: var(--gap-lg);
}
.quick-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 4px 10px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 12px;
}
.quick-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}
.quick-sub {
  font-size: 12px;
  color: var(--text-muted);
}
.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
@media (max-width: 900px) {
  .quick-grid { grid-template-columns: repeat(2, 1fr); }
}
.quick-card {
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all var(--t-fast);
}
.quick-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 8px var(--accent-glow);
  transform: translateY(-1px);
}
.quick-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-input);
  background: var(--accent-subtle);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.quick-body { flex: 1; min-width: 0; }
.quick-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}
.quick-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  background: var(--accent-warm-subtle);
  color: var(--accent-warm);
  border-radius: 2px;
}
.quick-sub-text {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.quick-arrow {
  color: var(--text-muted);
  font-size: 14px;
  flex-shrink: 0;
  transition: transform var(--t-fast);
}
.quick-card:hover .quick-arrow {
  color: var(--accent);
  transform: translateX(2px);
}

.modules {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 4px;
}
@media (max-width: 900px) {
  .modules { grid-template-columns: 1fr; }
}

.module-card {
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 200ms ease;
}
.module-card:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.module-head {
  display: flex;
  align-items: center;
  gap: 14px;
}
.module-icon {
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 10px;
  color: #fff;
  flex-shrink: 0;
}
.module-icon--green { background: linear-gradient(135deg, #00b574, #00a366); }
.module-icon--blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.module-head-text { flex: 1; min-width: 0; }
.module-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.module-sub {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.module-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.feature-list li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}
.feature-list li .el-icon {
  color: var(--accent);
  font-size: 14px;
  margin-top: 4px;
  flex-shrink: 0;
}

.module-cta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}
.module-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.module-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 34px; padding: 0 16px;
  border: none; border-radius: 6px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  font-family: inherit; transition: all 150ms ease;
}
.module-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.module-btn--primary { background: var(--accent); color: #fff; }
.module-btn--primary:hover:not(:disabled) { background: var(--accent-hover); }
.module-btn--ghost {
  background: #fff; color: var(--text-secondary);
  border: 1px solid var(--border-input);
}
.module-btn--ghost:hover:not(:disabled) {
  border-color: var(--accent); color: var(--accent);
}

.module-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-input);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-primary);
  background: #fff;
  resize: vertical;
  outline: none;
  transition: border-color 150ms ease;
  line-height: 1.6;
  box-sizing: border-box;
}
.module-textarea:focus { border-color: var(--accent); }
.module-textarea::placeholder { color: var(--text-muted); }

.module-error {
  padding: 10px 12px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  color: #d4380d;
  font-size: 13px;
  display: flex; align-items: center; gap: 6px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 700px) {
  .form-grid { grid-template-columns: 1fr; }
}
.form-field {
  display: flex; flex-direction: column; gap: 6px;
}
.form-label {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px; font-weight: 600; color: var(--text-secondary);
}
.link-fill {
  font-size: 11px; font-weight: normal;
}

/* 结果卡片 */
.module-body--result {
  gap: 14px;
}
.result-card {
  background: var(--bg-deepest);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 10px;
}
.result-card-head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.result-card-title {
  font-size: 15px; font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.result-card-salary {
  font-size: 14px; font-weight: 700;
  color: var(--accent-warm);
  font-variant-numeric: tabular-nums;
}
.result-card-salary--ok { font-size: 12px; color: var(--color-success); }
.result-meta {
  display: flex; flex-wrap: wrap; gap: 12px;
  font-size: 12px; color: var(--text-secondary);
}
.result-tags {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.result-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--accent-subtle);
  color: var(--accent);
  border-radius: 3px;
}
.result-desc {
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 10px 12px;
}
.result-desc-label {
  font-size: 11px; font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.result-desc-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.board-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}
.board-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 12px;
}
@media (max-width: 900px) {
  .board-grid { grid-template-columns: 1fr; }
}
.board-card {
  background: #fafbfc;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-input);
  padding: 14px 16px;
}
.board-kicker {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 14px;
}

/* 7 天条形图 */
.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 160px;
}
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  height: 100%;
}
.bar-num {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}
.bar-num--today { color: var(--accent); }
.bar-track {
  flex: 1;
  width: 100%;
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 2px 2px 0 0;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.bar-fill {
  width: 100%;
  min-height: 2px;
  background: var(--text-muted);
  transition: height 0.4s;
}
.bar-fill--today { background: var(--accent); }
.bar-day {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.bar-day--today { color: var(--accent); font-weight: 700; }

/* 状态行 + 分数行 */
.status-row {
  display: grid;
  grid-template-columns: 56px 1fr 28px;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.status-name {
  font-size: 12px;
  color: var(--text-secondary);
}
.status-name--mono { font-family: var(--font-mono); }
.status-track {
  height: 6px;
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 3px;
  overflow: hidden;
}
.status-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.4s;
}
.status-fill--gold { background: var(--accent-gold); }
.status-count {
  font-size: 12px;
  font-weight: 700;
  font-family: var(--font-mono);
  text-align: right;
  color: var(--text-primary);
}

.board-empty {
  margin-top: 16px;
  padding: 36px 24px;
  text-align: center;
  background: #fff;
  border: 1px dashed var(--border-input);
  border-radius: var(--radius-card);
  color: var(--text-muted);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.board-empty .el-icon { font-size: 18px; }
</style>