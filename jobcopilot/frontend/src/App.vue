<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { healthCheck } from '@/api'
import StatusIndicator from '@/components/StatusIndicator.vue'

const router = useRouter()
const currentRoute = router.currentRoute
const backendStatus = ref<'online' | 'offline' | 'loading'>('loading')
let healthInterval: ReturnType<typeof setInterval> | null = null

const navItems = [
  { path: '/', label: '仪表盘', icon: 'Odometer' },
  { path: '/chat', label: '对话', icon: 'MagicStick' },
  { path: '/materials', label: '素材库', icon: 'Files' },
  { path: '/jd', label: 'JD分析', icon: 'Document' },
  { path: '/resume', label: '岗位匹配 & 简历优化', icon: 'Edit' },
  { path: '/cover-letter', label: '求职信', icon: 'Message' },
  { path: '/greet', label: '打招呼', icon: 'ChatDotRound' },
  { path: '/tracker', label: '投递管理', icon: 'List' },
]

// 当前用户
const currentUser = computed<{ username: string; nickname: string | null } | null>(() => {
  try {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  } catch { return null }
})

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

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
      <!-- 右上角用户栏 -->
      <div class="topbar" v-if="currentUser">
        <div class="topbar-user">
          <el-icon :size="14"><UserFilled /></el-icon>
          <span>{{ currentUser.nickname || currentUser.username }}</span>
        </div>
        <button class="topbar-logout" @click="logout">
          <el-icon :size="14"><SwitchButton /></el-icon>
          <span>退出登录</span>
        </button>
      </div>

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

.user-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.logout-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 2px;
  font-family: inherit;
  transition: color var(--t-fast);
}
.logout-btn:hover { color: var(--color-danger); }

/* Main — flex center */
.main-area {
  flex: 1;
  min-width: 0;
  padding: 32px;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  position: relative;
}

/* 右上角用户栏 */
.topbar {
  position: absolute;
  top: 16px;
  right: 32px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 10;
}
.topbar-user {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
.topbar-user .el-icon { color: var(--accent); font-size: 13px; }

.topbar-logout {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  font-family: inherit;
  transition: all var(--t-fast);
}
.topbar-logout:hover {
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.main-inner {
  width: 100%;
  max-width: 1200px;
}
</style>
