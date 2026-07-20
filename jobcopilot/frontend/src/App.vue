<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { healthCheck } from '@/api'
import StatusIndicator from '@/components/StatusIndicator.vue'

const router = useRouter()
const currentRoute = router.currentRoute
const backendStatus = ref<'online' | 'offline' | 'loading'>('loading')
let healthInterval: ReturnType<typeof setInterval> | null = null

const navItems = [
  { path: '/', label: '仪表盘', icon: 'Odometer' },
  { path: '/jd', label: 'JD分析', icon: 'Document' },
  { path: '/resume', label: '简历优化', icon: 'Edit' },
  { path: '/cover-letter', label: '求职信', icon: 'Message' },
  { path: '/tracker', label: '投递管理', icon: 'List' },
]

async function checkHealth() {
  try {
    await healthCheck()
    backendStatus.value = 'online'
  } catch {
    backendStatus.value = 'offline'
  }
}

onMounted(() => {
  checkHealth()
  healthInterval = setInterval(checkHealth, 30000)
})

onUnmounted(() => {
  if (healthInterval) clearInterval(healthInterval)
})
</script>

<template>
  <div class="app-shell">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo-area">
        <div class="logo-text">JobCopilot</div>
        <div class="logo-sub">AI 求职助手</div>
        <div class="logo-divider"></div>
      </div>

      <nav class="nav-list">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: currentRoute.path === item.path }"
        >
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <StatusIndicator :status="backendStatus" />
      </div>
    </aside>

    <!-- Main content — centered wrapper -->
    <main class="main-area">
      <div class="main-inner">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--bg-deepest);
}

/* Sidebar — white + light accent */
.sidebar {
  width: 220px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.logo-area {
  padding: 20px 16px 16px;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  color: var(--accent);
  text-align: center;
}

.logo-sub {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  margin-top: 4px;
}

.logo-divider {
  height: 1px;
  background: var(--border-subtle);
  margin-top: 16px;
}

.nav-list {
  flex: 1;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding: 0 12px;
  margin: 0 8px;
  border-radius: var(--radius-btn);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all var(--t-fast) ease-out;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-subtle);
  color: var(--accent);
  border-left-color: var(--accent);
  font-weight: 600;
}

.nav-label {
  line-height: 1;
}

.sidebar-footer {
  border-top: 1px solid var(--border-subtle);
  padding: 12px 16px;
}

/* Main — flex center */
.main-area {
  flex: 1;
  min-width: 0;
  padding: 32px;
  overflow-x: hidden;
  display: flex;
  justify-content: center;
}

.main-inner {
  width: 100%;
  max-width: 1200px;
}
</style>
