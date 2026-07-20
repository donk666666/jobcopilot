<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTrackerStats, healthCheck } from '@/api'

const router = useRouter()
const stats = ref({ total: 0, by_status: {} as Record<string, number>, avg_match_score: 0 })

const statusOrder = ['待投递', '已投递', '初筛中', '面试中', '已发Offer', '已拒绝']

onMounted(async () => {
  try {
    await healthCheck()
    const data: any = await getTrackerStats()
    stats.value = data
  } catch { /* backend offline — handled by sidebar indicator */ }
})

const greeting = () => {
  const h = new Date().getHours()
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
}

const cards = [
  { title: 'JD 分析', desc: '智能解析职位描述，提取关键信息', icon: 'Document', route: '/jd', span: 2 },
  { title: '求职信', desc: 'AI 定制化生成个性化求职信', icon: 'Message', route: '/cover-letter', span: 1 },
  { title: '简历优化', desc: 'RAG 增强匹配分析，定向优化', icon: 'Edit', route: '/resume', span: 1 },
  { title: '投递管理', desc: '全流程追踪，从投递到 Offer', icon: 'List', route: '/tracker', span: 2 },
]

const pendingCount = computed(() => stats.value.by_status?.['待投递'] || 0)
const total = computed(() => stats.value.total || 0)
</script>

<template>
  <div class="dashboard">
    <!-- Welcome banner -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">{{ greeting() }}，萧仁科</h1>
        <p class="banner-sub">
          你有 <strong style="color: var(--accent)">{{ pendingCount }}</strong> 个岗位等待投递
          <template v-if="stats.avg_match_score > 0">
             · 平均匹配度 <strong style="color: var(--accent)">{{ stats.avg_match_score }}</strong> 分
          </template>
        </p>
      </div>
      <div class="banner-decoration">
        <svg width="120" height="80" viewBox="0 0 120 80" fill="none">
          <circle cx="60" cy="40" r="30" stroke="var(--accent)" stroke-width="0.5" opacity="0.3" />
          <circle cx="60" cy="40" r="20" stroke="var(--accent)" stroke-width="0.5" opacity="0.5" />
          <circle cx="60" cy="40" r="10" stroke="var(--accent)" stroke-width="0.5" opacity="0.7" />
          <line x1="30" y1="40" x2="90" y2="40" stroke="var(--accent)" stroke-width="0.3" opacity="0.2" />
          <line x1="60" y1="10" x2="60" y2="70" stroke="var(--accent)" stroke-width="0.3" opacity="0.2" />
        </svg>
      </div>
    </div>

    <!-- Feature cards (Bento Grid) -->
    <div class="bento-grid">
      <div
        v-for="card in cards"
        :key="card.route"
        class="bento-card"
        :class="`span-${card.span}`"
        @click="router.push(card.route)"
      >
        <div class="bento-icon">
          <el-icon :size="32" color="var(--accent)"><component :is="card.icon" /></el-icon>
        </div>
        <div class="bento-info">
          <h3 class="bento-title">{{ card.title }}</h3>
          <p class="bento-desc">{{ card.desc }}</p>
        </div>
      </div>
    </div>

    <!-- Tracker kanban pipe -->
    <div class="kanban-section" v-if="total > 0">
      <div class="kanban-header">
        <div>
          <span class="kanban-total">{{ total }}</span>
          <span class="kanban-unit">条记录</span>
        </div>
        <div v-if="stats.avg_match_score > 0">
          平均匹配度 <span class="kanban-score">{{ stats.avg_match_score }}</span>
        </div>
      </div>
      <div class="kanban-pipe-bar">
        <div
          v-for="(status, idx) in statusOrder"
          :key="status"
          class="kanban-segment"
          :class="{ 'segment-pulse': status === '待投递' && (stats.by_status?.[status] || 0) > 0 }"
          :style="{
            flex: (stats.by_status?.[status] || 0) || 0.3,
            background: `rgba(240, 185, 11, ${0.15 + idx * 0.12})`,
          }"
        ></div>
      </div>
      <div class="kanban-labels">
        <span v-for="status in statusOrder" :key="status" class="kanban-label">
          {{ status }} <strong>{{ stats.by_status?.[status] || 0 }}</strong>
        </span>
      </div>
    </div>

    <!-- Quick start guide -->
    <div class="quick-start">
      <h3 style="margin-bottom: 16px">快速开始</h3>
      <div class="guide-row">
        <div class="guide-card" @click="router.push('/jd')">
          <div class="guide-num">01</div>
          <div class="guide-title">分析 JD</div>
          <p class="guide-desc">粘贴职位描述，AI 自动提取关键要求</p>
        </div>
        <div class="guide-arrow">→</div>
        <div class="guide-card" @click="router.push('/resume')">
          <div class="guide-num">02</div>
          <div class="guide-title">优化简历</div>
          <p class="guide-desc">上传简历，查看匹配度与改进建议</p>
        </div>
        <div class="guide-arrow">→</div>
        <div class="guide-card" @click="router.push('/cover-letter')">
          <div class="guide-num">03</div>
          <div class="guide-title">生成求职信</div>
          <p class="guide-desc">一键生成个性化求职信</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {}

.welcome-banner {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border-radius: var(--radius-card);
  padding: 32px;
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--border-subtle);
}

.banner-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.banner-sub {
  font-size: 14px;
  color: var(--text-secondary);
}

.banner-decoration {
  opacity: 0.6;
  flex-shrink: 0;
}

/* Bento grid */
.bento-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.bento-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 24px;
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
  display: flex;
  align-items: center;
  gap: 20px;
}

.bento-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow);
  border-color: rgba(240, 185, 11, 0.3);
}

.span-2 { grid-column: span 2; }
.span-1 { grid-column: span 1; }

.bento-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(240, 185, 11, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.bento-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.bento-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

/* Kanban pipe */
.kanban-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
  margin-bottom: 24px;
}

.kanban-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.kanban-total {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-right: 8px;
}

.kanban-unit { color: var(--text-muted); }

.kanban-score {
  color: var(--accent);
  font-weight: 600;
}

.kanban-pipe-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  gap: 2px;
  margin-bottom: 12px;
}

.kanban-segment {
  transition: flex var(--t-normal) ease;
  border-radius: 2px;
}

.segment-pulse {
  animation: pipe-pulse 2s ease-in-out infinite;
}

@keyframes pipe-pulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.kanban-labels {
  display: flex;
  justify-content: space-between;
}

.kanban-label {
  font-size: 12px;
  color: var(--text-muted);
}

.kanban-label strong {
  color: var(--text-secondary);
  font-weight: 600;
}

/* Quick start */
.quick-start {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 24px;
}

.guide-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.guide-card {
  flex: 1;
  background: var(--bg-deepest);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}

.guide-card:hover {
  border-color: var(--accent);
  background: var(--bg-hover);
}

.guide-num {
  font-size: 28px;
  font-weight: 800;
  color: var(--accent);
  opacity: 0.5;
  margin-bottom: 8px;
}

.guide-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.guide-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.guide-arrow {
  color: var(--accent);
  font-size: 20px;
  opacity: 0.4;
  flex-shrink: 0;
}
</style>
