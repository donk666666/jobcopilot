<script setup lang="ts">
import { ref } from 'vue'
import { generateCoverLetter } from '@/api'
import { ElMessage } from 'element-plus'

const jdText = ref('')
const resumeText = ref('')
const candidateName = ref('')
const style = ref('formal')
const recipient = ref('招聘负责人')
const loading = ref(false)
const result = ref('')
const error = ref('')
const step = ref(1)

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
    })
    result.value = res.result; step.value = 4
  } catch (e: any) {
    error.value = e.message || '生成失败'; step.value = 4
  }
  finally { loading.value = false }
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

    <!-- Steps -->
    <div class="steps-bar">
      <div class="step-dot" :class="{ active: step >= 1, done: step > 1 }">1</div>
      <div class="step-line" :class="{ active: step > 1 }"></div>
      <div class="step-dot" :class="{ active: step >= 2, done: step > 2 }">2</div>
      <div class="step-line" :class="{ active: step > 2 }"></div>
      <div class="step-dot" :class="{ active: step >= 3, done: step > 3 }">3</div>
      <span class="step-label s1" :class="{ active: step === 1 }">填写信息</span>
      <span class="step-label s2" :class="{ active: step === 2 }">选择风格</span>
      <span class="step-label s3" :class="{ active: step >= 3 }">生成结果</span>
    </div>

    <!-- Step 1: Input -->
    <div v-if="step === 1" class="step-content">
      <div class="input-cards">
        <div class="cv-input-card">
          <h4>职位描述</h4>
          <el-input v-model="jdText" type="textarea" :rows="6" placeholder="粘贴目标职位JD..." />
        </div>
        <div class="cv-input-card">
          <h4>你的简历</h4>
          <el-input v-model="resumeText" type="textarea" :rows="8" placeholder="粘贴你的简历..." />
        </div>
        <div class="cv-input-card">
          <h4>补充信息（可选）</h4>
          <el-input v-model="candidateName" placeholder="你的姓名" style="margin-bottom: 12px" />
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

    <el-alert v-if="error && step !== 4" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
  </div>
</template>

<style scoped>
.cover-page { max-width: 900px; }
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

/* Steps */
.steps-bar { display: flex; align-items: center; margin: 28px 0 32px; position: relative; }
.step-dot {
  width: 36px; height: 36px; border-radius: 50%; border: 2px solid var(--border-input);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: var(--text-muted);
  background: var(--bg-deepest); flex-shrink: 0; transition: all var(--t-normal) ease;
}
.step-dot.active { border-color: var(--accent); color: var(--accent); }
.step-dot.done { background: var(--accent); border-color: var(--accent); color: #ffffff; }
.step-line { flex: 1; height: 2px; background: var(--border-input); margin: 0 12px; transition: background var(--t-normal) ease; }
.step-line.active { background: var(--accent); }
.step-label { position: absolute; top: 42px; font-size: 12px; color: var(--text-muted); transform: translateX(-50%); transition: color var(--t-fast) ease; }
.step-label.active { color: var(--accent); }
.s1 { left: calc(18px); }
.s2 { left: calc(50% - 18px); }
.s3 { left: calc(100% - 18px); }

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

@media (max-width: 768px) { .tone-cards { grid-template-columns: 1fr; } }
</style>
