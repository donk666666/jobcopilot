<script setup lang="ts">
import { ref } from 'vue'
import { analyzeJD } from '@/api'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

const jdText = ref('')
const loading = ref(false)
const result = ref<any>(null)
const error = ref('')
const showExamples = ref(false)

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
- 与算法团队协作推进模型迭代
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

async function handleAnalyze() {
  if (!jdText.value.trim()) { error.value = '请输入JD文本'; return }
  loading.value = true; error.value = ''; result.value = null
  try {
    const res: any = await analyzeJD(jdText.value)
    if (res.success) {
      result.value = res.result
      const title = res.result?.position_title
      if (title) localStorage.setItem('last_jd_title', title)
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
</script>

<template>
  <div class="jd-page">
    <h2 class="page-title">JD 智能分析</h2>
    <p class="page-sub">粘贴职位描述，AI 自动提取技能要求、经验年限等关键信息</p>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="10">
        <div class="input-card">
          <div class="examples-toggle" @click="showExamples = !showExamples">
            <span>JD 示例</span>
            <el-icon :size="16"><component :is="showExamples ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
          </div>
          <div v-if="showExamples" class="examples-panel">
            <div v-for="ex in examples" :key="ex.title" class="example-item" @click="useExample(ex)">{{ ex.title }}</div>
          </div>

          <el-input v-model="jdText" type="textarea" :rows="18" placeholder="请粘贴完整的职位描述（JD）..." />

          <div class="input-footer">
            <span class="prompt-badge">Few-shot + JSON Schema 输出</span>
            <el-button type="primary" :loading="loading" @click="handleAnalyze" size="large">
              <el-icon><MagicStick /></el-icon> 开始分析
            </el-button>
          </div>
        </div>
      </el-col>

      <el-col :span="14">
        <LoadingSkeleton v-if="loading" :lines="5" />

        <div v-else-if="result" class="result-card">
          <template v-if="result.position_title">
            <h3 class="position-name">{{ result.position_title }}</h3>

            <el-descriptions :column="2" border size="small" style="margin-bottom: 20px">
              <el-descriptions-item label="级别">{{ result.level }}</el-descriptions-item>
              <el-descriptions-item label="经验">
                <template v-if="typeof result.experience_years === 'object'">
                  {{ result.experience_years.min }}-{{ result.experience_years.max }}年
                </template>
                <template v-else>{{ result.experience_years }}年</template>
              </el-descriptions-item>
              <el-descriptions-item label="学历">{{ result.education }}</el-descriptions-item>
            </el-descriptions>

            <div v-if="result.hard_skills?.length" class="skill-section">
              <h4 class="section-label">必备技能</h4>
              <div class="tag-row">
                <span v-for="s in result.hard_skills" :key="s" class="skill-tag required">{{ s }}</span>
              </div>
            </div>

            <div v-if="result.bonus_skills?.length" class="skill-section">
              <h4 class="section-label">加分技能</h4>
              <div class="tag-row">
                <span v-for="s in result.bonus_skills" :key="s" class="skill-tag bonus">{{ s }}</span>
              </div>
            </div>

            <div v-if="result.core_responsibilities?.length" class="resp-section">
              <h4 class="section-label">核心职责</h4>
              <ul class="resp-list">
                <li v-for="r in result.core_responsibilities" :key="r">{{ r }}</li>
              </ul>
            </div>

            <div v-if="result.soft_skills?.length" class="skill-section">
              <h4 class="section-label">软技能</h4>
              <div class="tag-row">
                <span v-for="s in result.soft_skills" :key="s" class="skill-tag soft">{{ s }}</span>
              </div>
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

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
  </div>
</template>

<style scoped>
.jd-page {}
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

.input-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
}

.examples-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  margin-bottom: 12px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 13px;
  user-select: none;
  transition: color var(--t-fast) ease;
}
.examples-toggle:hover { color: var(--accent); }

.examples-panel {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.example-item {
  padding: 6px 12px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-btn);
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}
.example-item:hover { border-color: var(--accent); color: var(--accent); }

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.prompt-badge {
  font-size: 12px;
  color: var(--accent);
  padding: 4px 10px;
  border: 1px solid rgba(240, 185, 11, 0.3);
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

.position-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 16px;
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
  margin-top: 0;
}

.skill-section { margin-bottom: 16px; }
.tag-row { display: flex; flex-wrap: wrap; gap: 8px; }

.skill-tag {
  padding: 4px 12px;
  border-radius: var(--radius-tag);
  font-size: 12px;
  font-weight: 500;
}

.skill-tag.required {
  background: var(--accent-subtle);
  color: var(--accent);
}

.skill-tag.bonus {
  background: rgba(52, 211, 153, 0.15);
  color: var(--color-success);
}

.skill-tag.soft {
  background: rgba(245, 158, 11, 0.15);
  color: var(--color-warning);
}

.resp-section { margin-bottom: 20px; }

.resp-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.resp-list li {
  position: relative;
  padding-left: 16px;
  margin-bottom: 8px;
  color: var(--text-secondary);
  line-height: 1.5;
  font-size: 14px;
}

.resp-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}

.raw-output {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}

.empty-result {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
