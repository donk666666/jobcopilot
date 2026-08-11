<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { generateGreeting, getActiveResume } from '@/api'
import { ElMessage } from 'element-plus'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'

const resumeText = ref('')
const jdText = ref('')
const companyName = ref('')
const positionTitle = ref('')
const candidateName = ref('')
const style = ref('casual')
const variantCount = ref(3)
const loading = ref(false)
const variants = ref<string[]>([])
const copiedIdx = ref<number | null>(null)

const styles = [
  { key: 'casual', label: '亲和自然', desc: '像真人私信，适合互联网/创业公司' },
  { key: 'professional', label: '专业得体', desc: '措辞正式，适合中大型企业' },
  { key: 'tech', label: '技术直击', desc: '开门见山展示技术，适合技术岗' },
]

async function handleGenerate() {
  if (!resumeText.value.trim()) {
    ElMessage.warning('请先填写简历内容')
    return
  }
  loading.value = true
  variants.value = []
  try {
    const res: any = await generateGreeting({
      resume_text: resumeText.value,
      jd_text: jdText.value,
      company_name: companyName.value,
      position_title: positionTitle.value,
      candidate_name: candidateName.value || '求职者',
      style: style.value,
      variant_count: variantCount.value,
    })
    if (res.success) {
      variants.value = res.variants || []
      if (variants.value.length === 0) ElMessage.warning('未生成结果，请重试')
    } else {
      ElMessage.error(res.error || '生成失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e.message || '生成失败')
  } finally {
    loading.value = false
  }
}

async function copyVariant(idx: number) {
  try {
    await navigator.clipboard.writeText(variants.value[idx])
    copiedIdx.value = idx
    ElMessage.success('已复制')
    setTimeout(() => (copiedIdx.value = null), 1500)
  } catch {
    ElMessage.error('复制失败')
  }
}

onMounted(async () => {
  try {
    const res: any = await getActiveResume()
    if (res?.content) resumeText.value = res.content
  } catch { /* ignore */ }
})
</script>

<template>
  <div class="greet-page">
    <h2 class="page-title">个性化打招呼</h2>
    <p class="page-sub">基于 JD 和简历，生成打动 HR 的私信打招呼文案（Boss直聘 / 脉脉 / 领英）</p>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <div class="input-card">
          <h4 class="card-header">求职信息</h4>

          <div class="field">
            <label class="field-label">简历内容</label>
            <el-input v-model="resumeText" type="textarea" :rows="7" placeholder="粘贴简历全文，或从简历优化页自动带入" />
          </div>

          <div class="field">
            <label class="field-label">目标职位描述（JD）</label>
            <el-input v-model="jdText" type="textarea" :rows="3" placeholder="可选，粘贴职位描述让文案更有针对性" />
          </div>

          <el-row :gutter="12">
            <el-col :span="12">
              <div class="field">
                <label class="field-label">公司名称</label>
                <el-input v-model="companyName" placeholder="例如：字节跳动" />
              </div>
            </el-col>
            <el-col :span="12">
              <div class="field">
                <label class="field-label">职位名称</label>
                <el-input v-model="positionTitle" placeholder="例如：AI 产品经理" />
              </div>
            </el-col>
          </el-row>

          <div class="field">
            <label class="field-label">称呼</label>
            <el-input v-model="candidateName" placeholder="你的名字（默认：求职者）" />
          </div>

          <div class="field">
            <label class="field-label">语气风格</label>
            <div class="style-list">
              <div
                v-for="s in styles"
                :key="s.key"
                class="style-item"
                :class="{ active: style === s.key }"
                @click="style = s.key"
              >
                <div class="style-name">{{ s.label }}</div>
                <div class="style-desc">{{ s.desc }}</div>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="field-label">生成条数</label>
            <el-radio-group v-model="variantCount">
              <el-radio :value="1">1 条</el-radio>
              <el-radio :value="3">3 条</el-radio>
              <el-radio :value="5">5 条</el-radio>
            </el-radio-group>
          </div>

          <el-button type="primary" :loading="loading" @click="handleGenerate" style="width: 100%; margin-top: 8px">
            {{ loading ? '正在生成（约15秒）...' : '生成打招呼文案' }}
          </el-button>
        </div>
      </el-col>

      <el-col :span="16">
        <LoadingSkeleton v-if="loading && variants.length === 0" :lines="3" />
        <div v-else-if="variants.length > 0" class="result-card">
          <h4 class="card-header">生成的打招呼文案</h4>
          <div
            v-for="(v, i) in variants"
            :key="i"
            class="variant-item"
          >
            <p class="variant-text">{{ v }}</p>
            <el-button
              size="small"
              :type="copiedIdx === i ? 'success' : 'primary'"
              text
              @click="copyVariant(i)"
            >
              {{ copiedIdx === i ? '已复制 ✓' : '复制' }}
            </el-button>
          </div>
          <div class="result-footer">
            <el-button :loading="loading" @click="handleGenerate" round>换一批</el-button>
          </div>
        </div>
        <EmptyState
          v-else
          title="生成你的个性化打招呼"
          description="填写左侧信息，生成打动 HR 的第一句话"
        />
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.greet-page {}
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

.input-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
}

.card-header { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: var(--text-primary); }

.field { margin-bottom: 14px; }
.field-label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; }

.style-list { display: flex; flex-direction: column; gap: 6px; }
.style-item {
  padding: 8px 12px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-btn);
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}
.style-item:hover { border-color: var(--accent); }
.style-item.active { border-color: var(--accent); background: var(--accent-subtle); }
.style-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.style-desc { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.result-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 24px;
  min-height: 400px;
}

.variant-item {
  background: var(--bg-deepest);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 16px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.variant-text { margin: 0; font-size: 14px; line-height: 1.7; color: var(--text-primary); flex: 1; }

.result-footer { text-align: center; margin-top: 16px; }
</style>
