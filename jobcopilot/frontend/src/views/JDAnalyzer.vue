<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { analyzeJD, getJDAnalyses, deleteJDAnalysis } from '@/api'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const jdText = ref('')
const loading = ref(false)
const result = ref<any>(null)
const error = ref('')
const showExamples = ref(false)

// 历史记录
const history = ref<any[]>([])
const historyLoading = ref(false)
const currentJdId = ref<number | null>(null)
const selectedId = ref<number | null>(null)

const examples = [
  {
    title: '字节跳动 — AI产品经理',
    text: `职位名称：AI产品经理（大模型方向）
公司：字节跳动
级别：中级（3-5年经验）
学历要求：本科及以上

必备技能：
- 熟悉大模型技术栈（LLM、RAG、Prompt Engineering）
- 有AI产品从0到1的落地经验
- 数据分析能力，熟练使用SQL和Python
- 优秀的跨团队沟通和项目推动能力

核心职责：
- 负责AI产品的需求分析和产品设计
- 与算法团队协作推进���型迭代
- 制定产品路线图并推动落地`,
  },
  {
    title: '腾讯 — AI应用开发工程师',
    text: `岗位：AI应用开发工程师（Agent方向）
公司：腾讯
经验：2-4年

技术要求：
- 精通Python，熟悉FastAPI/Django等Web框架
- 了解LangChain、Agent开发、RAG技术
- 使用过向量数据库（ChromaDB/Milvus等）
- 有前端开发经验（Vue/React）优先

工作内容：
- 基于大模型API开发AI应用工具
- 设计和实现Agent工作流
- 优化Prompt和RAG检索质量`,
  },
]

function useExample(ex: { title: string; text: string }) {
  jdText.value = ex.text
  showExamples.value = false
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res: any = await getJDAnalyses()
    history.value = res || []
  } catch (e) {
    console.error('加载历史失败:', e)
  } finally {
    historyLoading.value = false
  }
}

async function loadFromHistory(item: any) {
  selectedId.value = item.id
  currentJdId.value = item.id
  jdText.value = item.jd_preview || ''
  if (item.analysis) {
    result.value = item.analysis
    ElMessage.success(`已加载历史记录 #${item.id}（${item.position_title}）`)
  }
}

async function removeHistory(item: any, e?: Event) {
  e?.stopPropagation()
  try {
    await ElMessageBox.confirm(
      `确定删除 #${item.id}（${item.position_title || '该 JD'}）的分析记录？`,
      '确认删除',
      { type: 'warning' }
    )
    await deleteJDAnalysis(item.id)
    ElMessage.success('已删除')
    if (selectedId.value === item.id) {
      selectedId.value = null
      currentJdId.value = null
      if (result.value && result.value.position_title === item.position_title) {
        result.value = null
      }
    }
    loadHistory()
  } catch {}
}

async function handleAnalyze() {
  if (!jdText.value.trim()) { error.value = '请输入JD文本'; return }
  loading.value = true; error.value = ''; result.value = null
  try {
    const res: any = await analyzeJD(jdText.value)
    if (res.success) {
      result.value = res.result
      currentJdId.value = res.id || null
      if (res.result?.position_title) {
        localStorage.setItem('last_jd_title', res.result.position_title)
      }
      loadHistory()  // 刷新历史列表
      ElMessage.success(`分析完成，已保存到历史${res.id ? ' #' + res.id : ''}`)
    } else {
      error.value = res.error || '分析失败'
      if (res.raw) result.value = res.raw
    }
  } catch (e: any) { error.value = e.message || '分析失败' }
  finally { loading.value = false }
}

async function copyResult() {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(result.value, null, 2))
    ElMessage.success('已复制到剪贴板')
  } catch { ElMessage.error('复制失败') }
}

function goToResume() {
  router.push('/resume')
}

// 工具：null/空 渲染
const showVal = (v: any): boolean => v !== null && v !== undefined && v !== ''
const formatExperience = (v: any): string => {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return `${v.min || 0}-${v.max || 0}年`
  return `${v}年`
}

// 经验分布
const experienceBadgeColor = computed(() => {
  const exp = result.value?.experience_years
  if (typeof exp === 'number') {
    if (exp <= 1) return 'var(--color-success)'
    if (exp <= 3) return 'var(--accent)'
    if (exp <= 5) return 'var(--color-warning)'
    return 'var(--color-danger)'
  }
  return 'var(--text-muted)'
})

onMounted(loadHistory)
</script>

<template>
  <div class="jd-page">
    <h2 class="page-title">JD 智能分析</h2>
    <p class="page-sub">粘贴职位描述，AI 自动提取技能要求、薪资、面试重点等关键信息 · 支持历史记录</p>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="9">
        <div class="input-card">
          <div class="examples-toggle" @click="showExamples = !showExamples">
            <span>JD 示例</span>
            <el-icon :size="16"><component :is="showExamples ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
          </div>
          <div v-if="showExamples" class="examples-panel">
            <div v-for="ex in examples" :key="ex.title" class="example-item" @click="useExample(ex)">{{ ex.title }}</div>
          </div>

          <el-input v-model="jdText" type="textarea" :rows="20" placeholder="请粘贴完整的职位描述（JD）..." />

          <div class="input-footer">
            <span class="prompt-badge">Few-shot + JSON Schema</span>
            <el-button type="primary" :loading="loading" @click="handleAnalyze" size="large">
              <el-icon><MagicStick /></el-icon> 开始分析
            </el-button>
          </div>
        </div>
      </el-col>

      <el-col :span="15">
        <LoadingSkeleton v-if="loading" :lines="5" />

        <div v-else-if="result" class="result-card">
          <template v-if="result.position_title">
            <!-- 职位标题 + 关键元数据 -->
            <div class="result-head">
              <div>
                <h3 class="position-name">{{ result.position_title }}</h3>
                <div class="position-meta">
                  <span v-if="result.company_name" class="meta-item">
                    <el-icon><OfficeBuilding /></el-icon>{{ result.company_name }}
                  </span>
                  <span v-if="result.industry" class="meta-item">
                    <el-icon><Histogram /></el-icon>{{ result.industry }}
                  </span>
                  <span v-if="result.company_stage" class="meta-item stage-badge">{{ result.company_stage }}</span>
                  <span v-if="result.work_location" class="meta-item">
                    <el-icon><Location /></el-icon>{{ result.work_location }}
                  </span>
                  <span v-if="result.employment_type && result.employment_type !== '全职'" class="meta-item emp-type">{{ result.employment_type }}</span>
                </div>
              </div>
              <div v-if="result.salary_range" class="salary-badge">
                {{ result.salary_range }}<span class="currency">{{ result.salary_currency || 'CNY' }}</span>
              </div>
            </div>

            <!-- 基本信息卡片 -->
            <el-descriptions :column="3" border size="small" style="margin-bottom: 20px">
              <el-descriptions-item label="级别">{{ result.level || '—' }}</el-descriptions-item>
              <el-descriptions-item label="经验">
                <el-tag size="small" :color="experienceBadgeColor" effect="dark" style="border: 0">
                  {{ formatExperience(result.experience_years) }}
                </el-tag>
                <span v-if="result.experience_flexibility" class="flex-note">{{ result.experience_flexibility }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="学历">{{ result.education || '—' }}</el-descriptions-item>
              <el-descriptions-item v-if="result.education_major" label="专业">{{ result.education_major }}</el-descriptions-item>
              <el-descriptions-item v-if="result.team_size" label="团队">{{ result.team_size }}</el-descriptions-item>
              <el-descriptions-item v-if="result.reports_to" label="汇报">{{ result.reports_to }}</el-descriptions-item>
            </el-descriptions>

            <!-- 必备技能 -->
            <div v-if="result.hard_skills?.length" class="skill-section">
              <h4 class="section-label">
                <span class="section-bar"></span>必备技能
                <span class="section-count">{{ result.hard_skills.length }}</span>
              </h4>
              <div class="tag-row">
                <span v-for="(s, i) in result.hard_skills" :key="s" class="skill-tag required" :class="{ top: i < 3 }">{{ s }}</span>
              </div>
            </div>

            <!-- 加分技能 -->
            <div v-if="result.bonus_skills?.length" class="skill-section">
              <h4 class="section-label"><span class="section-bar"></span>加分技能</h4>
              <div class="tag-row">
                <span v-for="s in result.bonus_skills" :key="s" class="skill-tag bonus">{{ s }}</span>
              </div>
            </div>

            <!-- 软技能 -->
            <div v-if="result.soft_skills?.length" class="skill-section">
              <h4 class="section-label"><span class="section-bar"></span>软技能</h4>
              <div class="tag-row">
                <span v-for="s in result.soft_skills" :key="s" class="skill-tag soft">{{ s }}</span>
              </div>
            </div>

            <!-- 技术栈分类 -->
            <div v-if="result.tech_stack_category?.length" class="info-grid">
              <div v-if="result.languages?.length" class="info-block">
                <div class="info-block-label">编程语言</div>
                <div class="info-block-text">{{ result.languages.join(' · ') }}</div>
              </div>
              <div v-if="result.frameworks?.length" class="info-block">
                <div class="info-block-label">框架/库</div>
                <div class="info-block-text">{{ result.frameworks.join(' · ') }}</div>
              </div>
              <div v-if="result.tech_stack_category?.length" class="info-block">
                <div class="info-block-label">技术方向</div>
                <div class="info-block-text">{{ result.tech_stack_category.join(' · ') }}</div>
              </div>
            </div>

            <!-- 核心职责 -->
            <div v-if="result.core_responsibilities?.length" class="resp-section">
              <h4 class="section-label"><span class="section-bar"></span>核心职责</h4>
              <ul class="resp-list">
                <li v-for="r in result.core_responsibilities" :key="r">{{ r }}</li>
              </ul>
            </div>

            <!-- 关键结果 KR -->
            <div v-if="result.key_results?.length" class="resp-section">
              <h4 class="section-label"><span class="section-bar"></span>关键结果 (KR)</h4>
              <ul class="resp-list">
                <li v-for="r in result.key_results" :key="r">{{ r }}</li>
              </ul>
            </div>

            <!-- 公司文化 / 工作方式 -->
            <div v-if="result.company_culture?.length || result.work_style?.length" class="info-grid">
              <div v-if="result.company_culture?.length" class="info-block">
                <div class="info-block-label">公司文化</div>
                <div class="tag-row">
                  <span v-for="s in result.company_culture" :key="s" class="mini-tag">{{ s }}</span>
                </div>
              </div>
              <div v-if="result.work_style?.length" class="info-block">
                <div class="info-block-label">工作方式</div>
                <div class="tag-row">
                  <span v-for="s in result.work_style" :key="s" class="mini-tag">{{ s }}</span>
                </div>
              </div>
            </div>

            <!-- 面试重点 -->
            <div v-if="result.interview_focus?.length" class="warn-section">
              <h4 class="section-label"><span class="section-bar"></span>面试重点考察</h4>
              <div class="tag-row">
                <span v-for="s in result.interview_focus" :key="s" class="skill-tag focus">{{ s }}</span>
              </div>
            </div>

            <!-- 可能笔试题 -->
            <div v-if="result.possible_questions?.length" class="resp-section">
              <h4 class="section-label"><span class="section-bar"></span>可能面试题</h4>
              <ol class="question-list">
                <li v-for="q in result.possible_questions" :key="q">{{ q }}</li>
              </ol>
            </div>

            <!-- 风险信号 -->
            <div v-if="result.red_flags?.length" class="risk-section">
              <h4 class="section-label risk-title">
                <el-icon><Warning /></el-icon>风险信号
              </h4>
              <ul class="risk-list">
                <li v-for="r in result.red_flags" :key="r">{{ r }}</li>
              </ul>
            </div>

            <!-- 卖点 -->
            <div v-if="result.selling_points?.length" class="selling-section">
              <h4 class="section-label selling-title">
                <el-icon><Star /></el-icon>对候选人的吸引点
              </h4>
              <ul class="selling-list">
                <li v-for="s in result.selling_points" :key="s">{{ s }}</li>
              </ul>
            </div>

            <div class="result-actions">
              <el-button type="primary" plain @click="goToResume">
                <el-icon><Right /></el-icon> 发送到简历优化
              </el-button>
              <el-button text @click="copyResult">
                <el-icon><CopyDocument /></el-icon> 复制结果
              </el-button>
            </div>
          </template>
          <pre v-else class="raw-output">{{ result }}</pre>
        </div>

        <div v-else class="empty-result">
          <el-empty description="等待分析结果" />
        </div>
      </el-col>
    </el-row>

    <!-- 历史记录侧栏 -->
    <div class="history-sidebar" v-if="history.length > 0 || historyLoading">
      <div class="history-header">
        <h4>分析历史 <el-tag size="small" type="info">{{ history.length }}</el-tag></h4>
        <el-button size="small" text @click="loadHistory" :loading="historyLoading">刷新</el-button>
      </div>
      <div v-if="historyLoading && history.length === 0" class="history-empty">加载中...</div>
      <div v-else-if="history.length === 0" class="history-empty">暂无历史，每次分析的 JD都会自动保存到这里</div>
      <div v-else class="history-list">
        <div
          v-for="item in history"
          :key="item.id"
          class="history-item"
          :class="{ selected: selectedId === item.id }"
          @click="loadFromHistory(item)"
        >
          <div class="hi-top">
            <span class="hi-id">#{{ item.id }}</span>
            <span v-if="item.analysis?.level" class="hi-level">{{ item.analysis.level }}</span>
            <span v-if="item.analysis?.salary_range" class="hi-salary">{{ item.analysis.salary_range }}</span>
            <span class="hi-del" @click="removeHistory(item, $event)" title="删除">×</span>
          </div>
          <div class="hi-title">
            {{ item.position_title || '未知职位' }}
            <span v-if="item.company_name" class="hi-company"> · {{ item.company_name }}</span>
          </div>
          <div class="hi-meta">
            <span v-if="item.analysis?.experience_years">{{ formatExperience(item.analysis.experience_years) }}</span>
            <span v-if="item.analysis?.industry">· {{ item.analysis.industry }}</span>
          </div>
          <div class="hi-preview">{{ item.jd_preview }}</div>
          <div class="hi-time">{{ item.created_at?.slice(0, 16) }}</div>
        </div>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
  </div>
</template>

<style scoped>
.jd-page { max-width: 1200px; margin: 0 auto; position: relative; }
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

.input-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
}

.examples-toggle {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; margin-bottom: 12px;
  cursor: pointer; color: var(--text-secondary);
  font-size: 13px; user-select: none;
  transition: color var(--t-fast) ease;
}
.examples-toggle:hover { color: var(--accent); }

.examples-panel { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.example-item {
  padding: 6px 12px; border: 1px solid var(--border-input);
  border-radius: var(--radius-btn); font-size: 12px;
  color: var(--text-secondary); cursor: pointer;
  transition: all var(--t-fast) ease-out;
}
.example-item:hover { border-color: var(--accent); color: var(--accent); }

.input-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }

.prompt-badge {
  font-size: 12px; color: var(--accent);
  padding: 4px 10px; border: 1px solid rgba(240, 185, 11, 0.3);
  border-radius: 20px;
}

/* Result */
.result-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 24px;
  min-height: 400px;
}

.result-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 18px; padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.position-name {
  font-size: 22px; font-weight: 700;
  color: var(--accent); margin-bottom: 10px;
}
.position-meta { display: flex; flex-wrap: wrap; gap: 10px; font-size: 13px; color: var(--text-secondary); }
.meta-item { display: inline-flex; align-items: center; gap: 4px; }
.meta-item .el-icon { font-size: 13px; color: var(--text-muted); }
.stage-badge, .emp-type {
  padding: 1px 8px; border-radius: 4px;
  background: var(--bg-deepest); font-size: 12px;
}
.salary-badge {
  background: linear-gradient(135deg, var(--accent), #f59e0b);
  color: #fff; padding: 10px 16px; border-radius: 8px;
  font-weight: 700; font-size: 16px; white-space: nowrap;
}
.salary-badge .currency {
  margin-left: 4px; font-size: 11px; opacity: 0.85; font-weight: 500;
}

.flex-note { margin-left: 8px; font-size: 12px; color: var(--text-muted); }

.section-label {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600;
  color: var(--text-primary);
  margin: 18px 0 10px;
}
.section-label:first-child { margin-top: 0; }
.section-bar {
  width: 3px; height: 14px; background: var(--accent); border-radius: 2px;
}
.section-count {
  font-size: 12px; font-weight: 400;
  color: var(--text-muted); padding: 1px 6px;
  background: var(--bg-deepest); border-radius: 3px;
}

.skill-section { margin-bottom: 16px; }
.tag-row { display: flex; flex-wrap: wrap; gap: 8px; }

.skill-tag {
  padding: 4px 12px; border-radius: var(--radius-tag);
  font-size: 12px; font-weight: 500;
}
.skill-tag.required { background: var(--accent-subtle); color: var(--accent); }
.skill-tag.required.top {
  background: var(--accent); color: #fff;
  box-shadow: 0 1px 4px rgba(240, 185, 11, 0.3);
}
.skill-tag.bonus { background: rgba(52, 211, 153, 0.15); color: var(--color-success); }
.skill-tag.soft { background: rgba(245, 158, 11, 0.15); color: var(--color-warning); }
.skill-tag.focus {
  background: rgba(139, 92, 246, 0.15); color: #7c3aed;
  border: 1px solid rgba(139, 92, 246, 0.25);
}

.info-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px; margin: 16px 0;
  padding: 14px; background: var(--bg-deepest);
  border-radius: 8px;
}
.info-block-label {
  font-size: 12px; color: var(--text-muted);
  margin-bottom: 6px; font-weight: 500;
}
.info-block-text {
  font-size: 13px; color: var(--text-primary);
  font-weight: 500;
}
.mini-tag {
  padding: 2px 8px; border-radius: 10px;
  background: var(--bg-card); font-size: 11px;
  color: var(--text-secondary);
}

.resp-section { margin-bottom: 16px; }
.resp-list { list-style: none; padding: 0; margin: 0; }
.resp-list li {
  position: relative; padding-left: 18px;
  margin-bottom: 8px; color: var(--text-secondary);
  line-height: 1.6; font-size: 14px;
}
.resp-list li::before {
  content: ''; position: absolute; left: 0; top: 9px;
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
}

.question-list {
  margin: 0; padding-left: 22px;
}
.question-list li {
  margin-bottom: 8px; color: var(--text-secondary);
  line-height: 1.6; font-size: 13px;
}
.question-list li::marker { color: var(--accent); font-weight: 600; }

.warn-section { margin-bottom: 16px; }
.risk-section {
  margin: 18px 0;
  padding: 12px 14px;
  background: rgba(239, 68, 68, 0.05);
  border-left: 3px solid var(--color-danger);
  border-radius: 4px;
}
.risk-title { color: var(--color-danger); margin-bottom: 8px; }
.risk-title .el-icon { margin-right: 4px; }
.risk-list { margin: 0; padding-left: 20px; }
.risk-list li {
  color: var(--color-danger); font-size: 13px;
  margin-bottom: 4px; line-height: 1.5;
}

.selling-section {
  margin: 18px 0;
  padding: 12px 14px;
  background: rgba(52, 211, 153, 0.05);
  border-left: 3px solid var(--color-success);
  border-radius: 4px;
}
.selling-title { color: var(--color-success); margin-bottom: 8px; }
.selling-title .el-icon { margin-right: 4px; }
.selling-list { margin: 0; padding-left: 20px; }
.selling-list li {
  color: var(--text-primary); font-size: 13px;
  margin-bottom: 4px; line-height: 1.5;
}

.result-actions {
  display: flex; gap: 12px; margin-top: 24px;
  padding-top: 16px; border-top: 1px solid var(--border-subtle);
}

.raw-output { white-space: pre-wrap; font-size: 14px; line-height: 1.6; color: var(--text-primary); }

.empty-result {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  min-height: 400px;
  display: flex; align-items: center; justify-content: center;
}

/* 历史侧栏 */
.history-sidebar {
  margin-top: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 16px;
}
.history-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.history-header h4 {
  margin: 0; font-size: 14px; font-weight: 600;
  display: flex; align-items: center; gap: 8px;
}
.history-empty {
  text-align: center; color: var(--text-muted);
  padding: 24px 0; font-size: 13px;
}
.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-item {
  background: var(--bg-deepest);
  border: 1px solid var(--border-input);
  border-radius: 8px; padding: 10px 12px;
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}
.history-item:hover {
  border-color: var(--accent); background: var(--accent-subtle);
}
.history-item.selected {
  border-color: var(--accent);
  background: var(--accent-subtle);
}
.hi-top {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--text-muted);
}
.hi-id { font-weight: 600; color: var(--text-primary); }
.hi-level, .hi-salary {
  padding: 0 6px; border-radius: 3px;
  background: var(--bg-card); font-size: 10px;
}
.hi-level { color: var(--accent); }
.hi-salary { color: var(--color-success); }
.hi-del {
  margin-left: auto; cursor: pointer; font-size: 16px;
  line-height: 1; color: var(--text-muted); padding: 0 4px;
}
.hi-del:hover { color: var(--color-danger); }
.hi-title {
  font-size: 13px; font-weight: 500;
  color: var(--text-primary); margin: 4px 0 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.hi-company { color: var(--text-muted); font-weight: 400; }
.hi-meta { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.hi-preview {
  font-size: 12px; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-top: 4px;
}
.hi-time { font-size: 10px; color: var(--text-muted); margin-top: 4px; }
</style>