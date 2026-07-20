# JobCopilot UI 品牌化升级 — 实施计划

**Plan date:** 2026-07-11
**Author:** UI redesign spec → implementation plan
**Spec:** `jobcopilot/docs/ui-redesign-spec.md`

---

## Goal

将 JobCopilot 前端从 Element Plus 默认外观升级为深靛蓝 + 金/琥珀品牌视觉，覆盖全局设计 Token、侧边栏框架、5 个功能页面、交互动效。

## Architecture

```
frontend/src/
├── styles/
│   ├── variables.css          # NEW — 设计 Token CSS 变量
│   ├── element-overrides.css  # NEW — Element Plus 深色全局覆写
│   ├── global.css             # NEW — 全局排版、动效、body 重置
│   └── transitions.css        # NEW — 路由/组件过渡动画
├── components/
│   ├── StatusIndicator.vue    # NEW — 后端状态指示器组件
│   ├── LoadingSkeleton.vue    # NEW — 骨架屏加载组件
│   ├── RadarChart.vue         # NEW — SVG 五维度雷达图组件
│   ├── ProgressBar.vue        # NEW — 迷你进度条组件
│   └── EmptyState.vue         # NEW — 空态引导组件
├── App.vue                    # MODIFY — 新侧边栏
├── main.ts                    # MODIFY — 导入样式
├── index.html                 # MODIFY — 引入 Inter + 思源黑体
├── api/index.ts               # NO CHANGE
├── router/index.ts            # NO CHANGE
├── views/
│   ├── Dashboard.vue          # MODIFY — Bento Grid + 看板管道 + 欢迎横幅
│   ├── JDAnalyzer.vue         # MODIFY — 40:60 布局 + 骨架加载 + 金色标签
│   ├── ResumeOptimizer.vue    # MODIFY — 两栏 + 雷达图 + 时间线 + 一键优化
│   ├── CoverLetter.vue        # MODIFY — 垂直向导 + 风格卡片 + 信纸
│   └── Tracker.vue            # MODIFY — 看板管道 + FAB + pill 筛选 + 空态
└── stores/                    # NO CHANGE
```

## Tech Stack

Vue 3 + TypeScript + Element Plus + Pinia + Vite. 所有改动纯前端，不新增 npm 依赖。雷达图用内联 SVG 实现，骨架屏用纯 CSS。

## Global Constraints

- 不新增 npm 包（雷达图用 SVG，骨架屏用 CSS）
- Element Plus 覆写用 `:root` + `--el-*` 变量 + `/deep/` 局部覆写，不修改 node_modules
- 所有颜色引用必须使用 CSS 变量，禁止直接写 hex 值
- 过渡动画仅用 `transform` 和 `opacity`
- 尊重 `prefers-reduced-motion`
- 每个任务结束后 Vue 编译无错误（`npm run build` 或 `vite build` 通过）

---

## Task 1: 设计 Token + 全局样式基础

**Files:**
- CREATE `frontend/src/styles/variables.css`
- CREATE `frontend/src/styles/global.css`
- CREATE `frontend/src/styles/element-overrides.css`
- CREATE `frontend/src/styles/transitions.css`
- MODIFY `frontend/index.html`
- MODIFY `frontend/src/main.ts`

**Interfaces:**
- Consumes: design spec Section 1 (tokens)
- Produces: CSS variables available globally; Inter + Noto Sans SC loaded; Element Plus themed dark

**Steps:**

### Step 1.1 — Create variables.css

Write `frontend/src/styles/variables.css`:

```css
:root {
  /* Background layers — deep indigo */
  --bg-deepest: #0b0a1a;
  --bg-card: #13102e;
  --bg-hover: #1c1845;
  --bg-elevated: #242055;
  --bg-input: #0f0d24;

  /* Accent — gold/amber */
  --accent: #f0b90b;
  --accent-hover: #f5cc3a;
  --accent-subtle: rgba(240, 185, 11, 0.15);
  --accent-glow: rgba(240, 185, 11, 0.25);

  /* Text */
  --text-primary: #e8e4f0;
  --text-secondary: #9690b8;
  --text-muted: #6b6588;

  /* Semantic */
  --color-success: #34d399;
  --color-warning: #f59e0b;
  --color-danger: #f87171;
  --color-info: #60a5fa;

  /* Borders */
  --border-subtle: #1c1845;
  --border-input: #2a2560;
  --border-focus: #f0b90b;

  /* Typography */
  --font-sans: 'Inter', 'Noto Sans SC', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Shadows */
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.4);
  --shadow-elevated: 0 4px 16px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 20px var(--accent-glow);

  /* Radii */
  --radius-card: 12px;
  --radius-btn: 8px;
  --radius-input: 8px;
  --radius-tag: 6px;
  --radius-modal: 16px;

  /* Transition durations */
  --t-fast: 150ms;
  --t-normal: 250ms;
  --t-slow: 300ms;
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --t-fast: 0ms;
    --t-normal: 0ms;
    --t-slow: 0ms;
  }
}
```

### Step 1.2 — Create global.css

Write `frontend/src/styles/global.css`:

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-deepest);
}

h1, h2, h3, h4, h5, h6 {
  color: var(--text-primary);
  margin: 0;
}

h1 { font-size: 24px; font-weight: 700; line-height: 1.3; }
h2 { font-size: 20px; font-weight: 600; line-height: 1.3; }
h3 { font-size: 16px; font-weight: 600; line-height: 1.4; }
h4 { font-size: 14px; font-weight: 600; line-height: 1.4; }

p {
  margin: 0;
  color: var(--text-secondary);
}

a {
  color: var(--accent);
  text-decoration: none;
}

a:hover {
  color: var(--accent-hover);
}

::selection {
  background: var(--accent-subtle);
  color: var(--text-primary);
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: var(--bg-deepest);
}
::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--border-input);
}

/* Shimmer animation for skeletons */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--bg-card) 25%,
    var(--bg-hover) 50%,
    var(--bg-card) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

/* Page transition */
.page-enter-active {
  transition: opacity var(--t-slow) ease-out;
}
.page-leave-active {
  transition: opacity var(--t-fast) ease-in;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
}
```

### Step 1.3 — Create element-overrides.css

Write `frontend/src/styles/element-overrides.css`:

```css
/* Override Element Plus CSS variables for dark theme */
:root {
  --el-color-primary: var(--accent);
  --el-color-primary-light-3: var(--accent-subtle);
  --el-color-primary-light-5: rgba(240, 185, 11, 0.3);
  --el-color-primary-light-7: rgba(240, 185, 11, 0.1);
  --el-color-primary-light-9: rgba(240, 185, 11, 0.05);
  --el-color-primary-dark-2: #d4a40a;

  --el-color-success: var(--color-success);
  --el-color-warning: var(--color-warning);
  --el-color-danger: var(--color-danger);
  --el-color-info: var(--color-info);

  --el-bg-color: var(--bg-deepest);
  --el-bg-color-overlay: var(--bg-elevated);
  --el-bg-color-page: var(--bg-deepest);

  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-text-color-secondary: var(--text-muted);
  --el-text-color-placeholder: var(--text-muted);
  --el-text-color-disabled: var(--border-input);

  --el-border-color: var(--border-subtle);
  --el-border-color-light: var(--border-subtle);
  --el-border-color-lighter: var(--border-input);
  --el-border-color-extra-light: rgba(255, 255, 255, 0.05);

  --el-border-radius-base: var(--radius-btn);
  --el-border-radius-small: 6px;

  --el-fill-color: var(--bg-card);
  --el-fill-color-light: var(--bg-hover);
  --el-fill-color-blank: var(--bg-card);
  --el-fill-color-lighter: var(--bg-hover);

  --el-mask-color: rgba(0, 0, 0, 0.6);
}

/* Card overrides */
.el-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-card) !important;
  color: var(--text-primary);
}

.el-card__header {
  border-bottom: 1px solid var(--border-subtle) !important;
  padding: 16px 20px !important;
  color: var(--text-primary);
}

.el-card__body {
  padding: 20px !important;
}

/* Button overrides */
.el-button--primary {
  --el-button-bg-color: var(--accent);
  --el-button-border-color: var(--accent);
  --el-button-text-color: #0b0a1a;
  --el-button-hover-bg-color: var(--accent-hover);
  --el-button-hover-border-color: var(--accent-hover);
  --el-button-hover-text-color: #0b0a1a;
  --el-button-active-bg-color: #d4a40a;
  --el-button-active-border-color: #d4a40a;
  font-weight: 600;
  transition: all var(--t-fast) ease-out;
}

.el-button--primary:active {
  transform: scale(0.97);
}

.el-button--default {
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--border-input);
  --el-button-text-color: var(--text-secondary);
  --el-button-hover-bg-color: var(--bg-hover);
  --el-button-hover-border-color: var(--text-muted);
  --el-button-hover-text-color: var(--text-primary);
}

.el-button--danger {
  --el-button-bg-color: var(--color-danger);
  --el-button-border-color: var(--color-danger);
}

.el-button--text {
  --el-button-text-color: var(--accent);
}

.el-button--text:hover {
  background: var(--accent-subtle) !important;
}

/* Input overrides */
.el-input__wrapper {
  background: var(--bg-input) !important;
  border: 1px solid var(--border-input) !important;
  border-radius: var(--radius-input) !important;
  box-shadow: none !important;
  transition: border-color var(--t-fast) ease, box-shadow var(--t-fast) ease;
}

.el-input__inner {
  color: var(--text-primary) !important;
}

.el-input__inner::placeholder {
  color: var(--text-muted) !important;
}

.el-textarea__inner {
  background: var(--bg-input) !important;
  border: 1px solid var(--border-input) !important;
  border-radius: var(--radius-input) !important;
  color: var(--text-primary) !important;
  transition: border-color var(--t-fast) ease, box-shadow var(--t-fast) ease;
}

.el-textarea__inner::placeholder {
  color: var(--text-muted) !important;
}

.el-input__wrapper:hover,
.el-textarea__inner:hover {
  border-color: var(--text-muted) !important;
}

.el-input.is-focus .el-input__wrapper,
.el-textarea__inner:focus {
  border-color: var(--border-focus) !important;
  box-shadow: 0 0 0 3px rgba(240, 185, 11, 0.15) !important;
}

/* Tag overrides */
.el-tag {
  border: none !important;
  border-radius: var(--radius-tag) !important;
  font-size: 12px;
}

.el-tag--default {
  background: var(--accent-subtle) !important;
  color: var(--accent) !important;
}

.el-tag--success {
  background: rgba(52, 211, 153, 0.15) !important;
  color: var(--color-success) !important;
}

.el-tag--warning {
  background: rgba(245, 158, 11, 0.15) !important;
  color: var(--color-warning) !important;
}

.el-tag--danger {
  background: rgba(248, 113, 113, 0.15) !important;
  color: var(--color-danger) !important;
}

.el-tag--info {
  background: rgba(96, 165, 250, 0.15) !important;
  color: var(--color-info) !important;
}

/* Table overrides */
.el-table {
  --el-table-bg-color: var(--bg-card);
  --el-table-tr-bg-color: var(--bg-card);
  --el-table-header-bg-color: var(--bg-deepest);
  --el-table-row-hover-bg-color: var(--bg-hover);
  --el-table-border-color: var(--border-subtle);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-secondary);
}

.el-table th.el-table__cell {
  background: var(--bg-deepest);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: rgba(255, 255, 255, 0.015);
}

/* Dialog overrides */
.el-dialog {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-modal) !important;
}

.el-dialog__header {
  color: var(--text-primary);
}

.el-dialog__body {
  color: var(--text-primary);
}

.el-overlay {
  background: var(--el-mask-color) !important;
}

/* Menu (sidebar) overrides */
.el-menu {
  border-right: none !important;
}

.el-menu-item {
  margin: 0 8px !important;
  border-radius: var(--radius-btn) !important;
  height: 44px !important;
  line-height: 44px !important;
  transition: all var(--t-fast) ease-out !important;
}

.el-menu-item:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
}

.el-menu-item.is-active {
  background: var(--accent-subtle) !important;
  color: var(--accent) !important;
  border-left: 3px solid var(--accent) !important;
}

/* Tabs overrides */
.el-tabs__item {
  color: var(--text-secondary) !important;
  transition: color var(--t-normal) ease;
}

.el-tabs__item:hover {
  color: var(--text-primary) !important;
}

.el-tabs__item.is-active {
  color: var(--accent) !important;
}

.el-tabs__active-bar {
  background: var(--accent) !important;
}

/* Alert overrides */
.el-alert--error {
  background: rgba(248, 113, 113, 0.1) !important;
  border: 1px solid rgba(248, 113, 113, 0.2) !important;
}

.el-alert--info {
  background: rgba(96, 165, 250, 0.1) !important;
  border: 1px solid rgba(96, 165, 250, 0.2) !important;
}

.el-alert__title {
  color: var(--text-primary) !important;
}

.el-alert__description {
  color: var(--text-secondary) !important;
}

/* Divider */
.el-divider--horizontal {
  border-top-color: var(--border-subtle) !important;
}

/* Progress */
.el-progress-bar__outer {
  background: var(--bg-hover) !important;
}

/* Steps */
.el-step__title {
  color: var(--text-primary) !important;
}

.el-step__description {
  color: var(--text-secondary) !important;
}

/* Select dropdown */
.el-select-dropdown {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-subtle) !important;
}

.el-select-dropdown__item {
  color: var(--text-secondary) !important;
}

.el-select-dropdown__item.hover,
.el-select-dropdown__item:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
}

.el-select-dropdown__item.selected {
  color: var(--accent) !important;
}

/* Empty component */
.el-empty__description p {
  color: var(--text-muted) !important;
}

/* Skeleton */
.el-skeleton__item {
  background: linear-gradient(
    90deg,
    var(--bg-card) 25%,
    var(--bg-hover) 50%,
    var(--bg-card) 75%
  ) !important;
  background-size: 200% 100% !important;
  animation: shimmer 1.5s ease-in-out infinite !important;
}

/* Collapse */
.el-collapse-item__header {
  background: var(--bg-card) !important;
  color: var(--text-secondary) !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}

.el-collapse-item__wrap {
  background: var(--bg-card) !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}

.el-collapse-item__content {
  color: var(--text-secondary) !important;
}
```

### Step 1.4 — Create transitions.css

Write `frontend/src/styles/transitions.css`:

```css
/* Route-level page transitions */
.fade-slide-enter-active {
  transition: opacity var(--t-slow) ease-out, transform var(--t-slow) ease-out;
}
.fade-slide-leave-active {
  transition: opacity var(--t-fast) ease-in, transform var(--t-fast) ease-in;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Card list staggered entrance */
.card-stagger-enter-active {
  transition: opacity var(--t-normal) ease-out, transform var(--t-normal) ease-out;
}
.card-stagger-leave-active {
  transition: opacity var(--t-fast) ease-in;
}
.card-stagger-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.card-stagger-leave-to {
  opacity: 0;
}
```

### Step 1.5 — Modify index.html

Edit `frontend/index.html`. Replace the `<head>` section content:

```html
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/svg+xml" href="/vite.svg" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>JobCopilot - AI求职助手</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet" />
</head>
```

### Step 1.6 — Modify main.ts

Edit `frontend/src/main.ts`. Add style imports before `import App`:

```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import '@/styles/variables.css'
import '@/styles/global.css'
import '@/styles/element-overrides.css'
import '@/styles/transitions.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: undefined })

app.mount('#app')
```

### Step 1.7 — Verify

Run `npm run build` from the frontend directory. It should compile without errors. Verify in browser that the page background is `#0b0a1a`, text is light, and Element Plus components (buttons, inputs, cards) use the new dark gold theme.

---

## Task 2: 全局框架 — 侧边栏 + App.vue

**Files:**
- CREATE `frontend/src/components/StatusIndicator.vue`
- MODIFY `frontend/src/App.vue`

**Interfaces:**
- App.vue: `<router-view>` wrapped with `<transition>` for page animations
- StatusIndicator: Props `{ status: 'online' | 'offline' | 'loading' }` — displays colored dot + label

### Step 2.1 — Create StatusIndicator.vue

Write `frontend/src/components/StatusIndicator.vue`:

```vue
<script setup lang="ts">
defineProps<{ status: 'online' | 'offline' | 'loading' }>()
</script>

<template>
  <div class="status-indicator">
    <span class="status-dot" :class="`dot-${status}`"></span>
    <span class="status-label">
      {{ status === 'online' ? '服务在线' : status === 'offline' ? '服务离线' : '连接中...' }}
    </span>
  </div>
</template>

<style scoped>
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-online {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
}

.dot-offline {
  background: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
}

.dot-loading {
  background: var(--color-warning);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.status-label {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
```

### Step 2.2 — Rewrite App.vue

Fully rewrite `frontend/src/App.vue`:

```vue
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
        <div class="logo-sub">AI求职助手</div>
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

    <!-- Main content -->
    <main class="main-area">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--bg-deepest);
}

.sidebar {
  width: 220px;
  background: var(--bg-deepest);
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
  background: rgba(240, 185, 11, 0.2);
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
}

.nav-label {
  line-height: 1;
}

.sidebar-footer {
  border-top: 1px solid var(--border-subtle);
}
</style>
```

### Step 2.3 — Verify

Run `npm run dev`. Open browser. Confirm:
- Sidebar shows dark indigo with gold "JobCopilot" logo
- Navigation items highlight with gold left border and subtle gold background on active
- Bottom shows green "服务在线" or red "服务离线" status
- Page transitions have fade+slide animation
- Main area background is `#0b0a1a`

---

## Task 3: 仪表盘 Dashboard

**Files:**
- MODIFY `frontend/src/views/Dashboard.vue`

### Step 3.1 — Rewrite Dashboard.vue

Fully rewrite `frontend/src/views/Dashboard.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTrackerStats, healthCheck } from '@/api'

const router = useRouter()
const stats = ref({ total: 0, by_status: {} as Record<string, number>, avg_match_score: 0 })
const backendOnline = ref(true)
const lastAnalysis = ref('')

const statusOrder = ['待投递', '已投递', '初筛中', '面试中', '已发Offer', '已拒绝']

onMounted(async () => {
  try {
    await healthCheck()
    backendOnline.value = true
    const data: any = await getTrackerStats()
    stats.value = data
  } catch {
    backendOnline.value = false
  }
  lastAnalysis.value = localStorage.getItem('last_jd_title') || ''
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

const total = computed(() => stats.value.total || 0)

const maxCount = computed(() => {
  const vals = Object.values(stats.value.by_status || {})
  return vals.length ? Math.max(...vals, 1) : 1
})
</script>

<template>
  <div class="dashboard">
    <!-- Welcome banner -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">{{ greeting() }}，萧仁科</h1>
        <p class="banner-sub">
          你有 <strong style="color: var(--accent)">{{ stats.by_status?.['待投递'] || 0 }}</strong> 个岗位等待投递
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
          v-for="status in statusOrder"
          :key="status"
          class="kanban-segment"
          :class="{ 'segment-pulse': status === '待投递' && (stats.by_status?.[status] || 0) > 0 }"
          :style="{
            flex: (stats.by_status?.[status] || 0) || '0.3',
            background: `rgba(240, 185, 11, ${0.15 + (statusOrder.indexOf(status) * 0.12)})`,
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
.dashboard {
  max-width: 1100px;
}

.welcome-banner {
  background: linear-gradient(135deg, #13102e, #1c1845);
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

.span-2 {
  grid-column: span 2;
}

.span-1 {
  grid-column: span 1;
}

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

.kanban-unit {
  color: var(--text-muted);
}

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
```

Fix: the `computed` import is missing. Add to the imports:

```ts
import { ref, computed, onMounted } from 'vue'
```

### Step 3.2 — Verify

Run dev server. Open browser to `/`. Confirm:
- Welcome banner with greeting and stats
- 4 bento cards in asymmetric grid (JD big, cover letter small, resume small, tracker big)
- Kanban pipe bar shows proportional segments
- Quick start guide with 3 step cards

---

## Task 4: 投递管理 Tracker

**Files:**
- CREATE `frontend/src/components/ProgressBar.vue`
- CREATE `frontend/src/components/EmptyState.vue`
- MODIFY `frontend/src/views/Tracker.vue`

### Step 4.1 — Create ProgressBar.vue

Write `frontend/src/components/ProgressBar.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number }>()

const color = computed(() => {
  if (props.value >= 80) return 'var(--color-success)'
  if (props.value >= 60) return 'var(--color-warning)'
  return 'var(--color-danger)'
})
</script>

<template>
  <div class="mini-progress">
    <div class="mini-progress-track">
      <div
        class="mini-progress-fill"
        :style="{ width: value + '%', background: color }"
      ></div>
    </div>
    <span class="mini-progress-value">{{ value }}</span>
  </div>
</template>

<style scoped>
.mini-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-progress-track {
  width: 60px;
  height: 6px;
  background: var(--bg-hover);
  border-radius: 3px;
  overflow: hidden;
}

.mini-progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width var(--t-normal) ease;
}

.mini-progress-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
```

### Step 4.2 — Create EmptyState.vue

Write `frontend/src/components/EmptyState.vue`:

```vue
<script setup lang="ts">
defineProps<{ title: string; description: string; actionLabel?: string }>()
const emit = defineEmits<{ action: [] }>()
</script>

<template>
  <div class="empty-state">
    <svg class="empty-illustration" width="80" height="80" viewBox="0 0 80 80" fill="none">
      <path d="M20 60 L40 20 L60 60" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.4" fill="none" />
      <circle cx="40" cy="50" r="6" stroke="var(--accent)" stroke-width="1.5" opacity="0.6" fill="none" />
      <path d="M40 56 L40 62" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" opacity="0.4" />
    </svg>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-desc">{{ description }}</p>
    <button v-if="actionLabel" class="empty-action" @click="emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  animation: empty-in var(--t-slow) ease-out;
}

@keyframes empty-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.empty-illustration {
  margin-bottom: 20px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  max-width: 280px;
  line-height: 1.5;
}

.empty-action {
  margin-top: 16px;
  padding: 8px 24px;
  background: var(--accent);
  color: #0b0a1a;
  border: none;
  border-radius: var(--radius-btn);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}

.empty-action:hover {
  background: var(--accent-hover);
  transform: scale(1.02);
}
</style>
```

### Step 4.3 — Rewrite Tracker.vue

Fully rewrite `frontend/src/views/Tracker.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listApplications, updateApplication, deleteApplication, createApplication, getTrackerStats } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProgressBar from '@/components/ProgressBar.vue'
import EmptyState from '@/components/EmptyState.vue'

const applications = ref<any[]>([])
const loading = ref(false)
const stats = ref<any>({ total: 0, by_status: {}, avg_match_score: 0 })
const dialogVisible = ref(false)
const form = ref({ company_name: '', position_title: '', jd_text: '', status: '待投递' })

const statusOrder = ['待投递', '已投递', '初筛中', '面试中', '已发Offer', '已拒绝']
const statusFilter = ref('')
const filters = ref(['全部', ...statusOrder])

function selectFilter(f: string) {
  statusFilter.value = f === '全部' ? '' : f
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const data: any = await listApplications(statusFilter.value || undefined)
    applications.value = data
    const s: any = await getTrackerStats()
    stats.value = s
  } catch { ElMessage.error('获取数据失败') }
  finally { loading.value = false }
}

async function handleStatusChange(row: any) {
  try {
    await updateApplication(row.id, { status: row.status })
    ElMessage.success('状态已更新')
    fetchData()
  } catch { ElMessage.error('更新失败') }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此记录？', '确认', { type: 'warning' })
    await deleteApplication(id)
    ElMessage.success('已删除')
    fetchData()
  } catch { /* user cancelled */ }
}

async function handleCreate() {
  try {
    await createApplication(form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    form.value = { company_name: '', position_title: '', jd_text: '', status: '待投递' }
    fetchData()
  } catch { ElMessage.error('创建失败') }
}

function getStatusType(status: string) {
  const map: Record<string, string> = {
    '待投递': 'info', '已投递': '', '初筛中': 'warning',
    '面试中': 'primary', '已发Offer': 'success', '已拒绝': 'danger',
  }
  return map[status] || 'info'
}

onMounted(fetchData)
</script>

<template>
  <div class="tracker-page">
    <div class="tracker-header">
      <div>
        <h2 class="page-title">投递进度管理</h2>
        <p class="page-sub">共 {{ stats.total }} 条记录 · 平均匹配度 {{ stats.avg_match_score }}</p>
      </div>
    </div>

    <!-- Kanban pipe -->
    <div class="tracker-kanban" v-if="stats.total > 0">
      <div class="pipe-header">
        <div>
          <span class="pipe-total">{{ stats.total }}</span>
          <span class="pipe-unit">条记录</span>
        </div>
        <div class="pipe-avg">
          平均匹配度 <span class="pipe-score">{{ stats.avg_match_score }}</span>
        </div>
      </div>
      <div class="pipe-bar">
        <div
          v-for="status in statusOrder"
          :key="status"
          class="pipe-seg"
          :style="{ flex: (stats.by_status?.[status] || 0) || 0.3 }"
        ></div>
      </div>
      <div class="pipe-labels">
        <span v-for="status in statusOrder" :key="status" class="pipe-label">
          {{ status }} <strong>{{ stats.by_status?.[status] || 0 }}</strong>
        </span>
      </div>
    </div>

    <!-- Pill filters -->
    <div class="pill-filters">
      <button
        v-for="f in filters"
        :key="f"
        class="pill"
        :class="{ active: (f === '全部' ? '' : f) === statusFilter }"
        @click="selectFilter(f)"
      >{{ f }}</button>
    </div>

    <!-- Table area -->
    <div v-if="applications.length > 0" class="table-wrap">
      <el-table :data="applications" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="company_name" label="公司" min-width="150" />
        <el-table-column prop="position_title" label="职位" min-width="150" />
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-select
              v-model="row.status"
              size="small"
              @change="handleStatusChange(row)"
              style="width: 110px"
            >
              <el-option v-for="s in statusOrder" :key="s" :label="s" :value="s" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="匹配度" width="120">
          <template #default="{ row }">
            <ProgressBar v-if="row.match_score !== null && row.match_score !== undefined" :value="row.match_score" />
            <span v-else style="color: var(--text-muted)">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ row.updated_at?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" text @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <EmptyState
      v-else-if="!loading"
      title="还没有投递记录"
      description="点击右下角 + 按钮开始记录第一份投递"
      action-label="立即添加"
      @action="dialogVisible = true"
    />

    <!-- FAB -->
    <button class="fab" @click="dialogVisible = true" title="新增投递">
      <el-icon :size="24"><Plus /></el-icon>
    </button>

    <!-- Create dialog -->
    <el-dialog v-model="dialogVisible" title="新增投递记录" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="公司名称">
          <el-input v-model="form.company_name" placeholder="例如：字节跳动" />
        </el-form-item>
        <el-form-item label="职位名称">
          <el-input v-model="form.position_title" placeholder="例如：AI 产品经理" />
        </el-form-item>
        <el-form-item label="JD文本">
          <el-input v-model="form.jd_text" type="textarea" :rows="4" placeholder="可选，粘贴职位描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tracker-page {
  position: relative;
  min-height: calc(100vh - 48px);
}

.page-title { margin-bottom: 4px; }
.page-sub { font-size: 13px; color: var(--text-muted); }

.tracker-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

/* Kanban */
.tracker-kanban {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
  margin-bottom: 16px;
}

.pipe-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
  color: var(--text-secondary);
  font-size: 13px;
}

.pipe-total { font-size: 32px; font-weight: 700; color: var(--text-primary); margin-right: 8px; }
.pipe-unit { color: var(--text-muted); }
.pipe-score { color: var(--accent); font-weight: 600; }

.pipe-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  gap: 2px;
  margin-bottom: 12px;
}

.pipe-seg {
  background: rgba(240, 185, 11, 0.3);
  border-radius: 2px;
  transition: flex var(--t-normal) ease;
}

.pipe-seg:first-child { background: rgba(240, 185, 11, 0.5); }
.pipe-seg:last-child { background: rgba(240, 185, 11, 0.1); }

.pipe-labels { display: flex; justify-content: space-between; }
.pipe-label { font-size: 12px; color: var(--text-muted); }
.pipe-label strong { color: var(--text-secondary); font-weight: 600; }

/* Pill filters */
.pill-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pill {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid var(--border-input);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--t-fast) ease-out;
}

.pill:hover { border-color: var(--text-muted); color: var(--text-primary); }

.pill.active {
  background: var(--accent);
  color: #0b0a1a;
  border-color: var(--accent);
  font-weight: 600;
}

/* Table */
.table-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  overflow: hidden;
}

/* FAB */
.fab {
  position: fixed;
  bottom: 32px;
  right: 32px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--accent);
  color: #0b0a1a;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(240, 185, 11, 0.3);
  transition: all var(--t-fast) ease-out;
  z-index: 100;
}

.fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 28px rgba(240, 185, 11, 0.45);
}

.fab:active { transform: scale(0.95); }
</style>
```

### Step 4.4 — Verify

Run dev server. Open browser to `/tracker`. Confirm:
- Kanban pipe bar at top showing proportional status segments
- Pill tag filters (全部|待投递|已投递...), clicking filters table
- Table dark-themed with progress bars in match-score column
- FAB button fixed bottom-right
- Empty state with illustration when no records

---

## Task 5: JD 分析 JDAnalyzer

**Files:**
- CREATE `frontend/src/components/LoadingSkeleton.vue`
- MODIFY `frontend/src/views/JDAnalyzer.vue`

### Step 5.1 — Create LoadingSkeleton.vue

Write `frontend/src/components/LoadingSkeleton.vue`:

```vue
<script setup lang="ts">
defineProps<{ lines?: number; delay?: number }>()
</script>

<template>
  <div class="skeleton-panel">
    <div class="skeleton-header">AI 正在解析...</div>
    <div
      v-for="i in (lines || 4)"
      :key="i"
      class="skeleton-row"
      :style="{ animationDelay: (delay || 200) * i + 'ms' }"
    >
      <div class="skeleton-label skeleton-line"></div>
      <div class="skeleton-value skeleton-line" :style="{ width: (40 + Math.random() * 50) + '%' }"></div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 24px;
}

.skeleton-header {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 24px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  animation: skeleton-fade-in 0.3s ease-out both;
}

@keyframes skeleton-fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.skeleton-label {
  width: 80px;
  flex-shrink: 0;
}

.skeleton-value {
  flex: 1;
}
</style>
```

### Step 5.2 — Rewrite JDAnalyzer.vue

Fully rewrite `frontend/src/views/JDAnalyzer.vue`:

```vue
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
    <p class="page-sub">粘贴职位描述，AI 自动提取技能要求、经验年限、公司文化等关键信息</p>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- Input area: 40% -->
      <el-col :span="10">
        <div class="input-card">
          <!-- JD Examples collapsible -->
          <div class="examples-toggle" @click="showExamples = !showExamples">
            <span>JD 示例</span>
            <el-icon :size="16"><component :is="showExamples ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
          </div>
          <div v-if="showExamples" class="examples-panel">
            <div
              v-for="ex in examples" :key="ex.title"
              class="example-item"
              @click="useExample(ex)"
            >{{ ex.title }}</div>
          </div>

          <el-input
            v-model="jdText"
            type="textarea"
            :rows="18"
            placeholder="请粘贴完整的职位描述（JD）..."
          />

          <div class="input-footer">
            <span class="prompt-badge">Few-shot + JSON Schema 输出</span>
            <el-button type="primary" :loading="loading" @click="handleAnalyze" size="large">
              <el-icon><MagicStick /></el-icon> 开始分析
            </el-button>
          </div>
        </div>
      </el-col>

      <!-- Result area: 60% -->
      <el-col :span="14">
        <!-- Loading skeleton -->
        <LoadingSkeleton v-if="loading" :lines="5" />

        <!-- Result -->
        <div v-else-if="result" class="result-card">
          <template v-if="result.position_title">
            <div class="result-header">
              <h3 class="position-name">{{ result.position_title }}</h3>
            </div>

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

        <!-- Empty state -->
        <div v-else class="empty-result">
          <el-empty description="等待分析结果" />
        </div>
      </el-col>
    </el-row>

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
  </div>
</template>

<style scoped>
.jd-page { max-width: 1200px; }
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
```

### Step 5.3 — Verify

Run dev server. Open `/jd`. Confirm:
- 40:60 layout
- "JD 示例" toggle expands to show example JDs, clicking one fills textarea
- "开始分析" button triggers loading skeleton in result area
- Result shows gold position name, skill tags with gold/green/warn colors, bulleted responsibilities
- "发送到简历优化" and "复制结果" buttons at bottom

---

## Task 6: 简历优化 ResumeOptimizer

**Files:**
- CREATE `frontend/src/components/RadarChart.vue`
- MODIFY `frontend/src/views/ResumeOptimizer.vue`

### Step 6.1 — Create RadarChart.vue

Write `frontend/src/components/RadarChart.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: Record<string, number>
  size?: number
}>()

const dims = computed(() => {
  const entries = Object.entries(props.data)
  return { labels: entries.map(([k]) => k), values: entries.map(([, v]) => v) }
})

const s = computed(() => props.size || 200)
const cx = computed(() => s.value / 2)
const cy = computed(() => s.value / 2)
const r = computed(() => s.value / 2 - 30)

function polar(i: number, total: number, radius: number): [number, number] {
  const angle = (Math.PI * 2 * i) / total - Math.PI / 2
  return [cx.value + radius * Math.cos(angle), cy.value + radius * Math.sin(angle)]
}

const pathData = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return ''
  const pts = dims.value.values.map((v, i) => {
    const [x, y] = polar(i, n, (v / 100) * r.value)
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  })
  return pts.join(' ') + 'Z'
})

const gridPaths = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return []
  const levels = [0.25, 0.5, 0.75, 1]
  return levels.map(level => {
    const pts = Array.from({ length: n }, (_, i) => {
      const [x, y] = polar(i, n, level * r.value)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    return pts.join(' ') + 'Z'
  })
})

const axisLines = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return []
  return Array.from({ length: n }, (_, i) => {
    const [x, y] = polar(i, n, r.value)
    return { x1: cx.value, y1: cy.value, x2: x, y2: y }
  })
})

const labelPositions = computed(() => {
  const n = dims.value.labels.length
  if (n < 3) return []
  return dims.value.labels.map((label, i) => {
    const [x, y] = polar(i, n, r.value + 16)
    return { label, x, y }
  })
})
</script>

<template>
  <svg :width="s" :height="s" :viewBox="`0 0 ${s} ${s}`">
    <!-- Grid -->
    <path
      v-for="(gp, idx) in gridPaths"
      :key="'g' + idx"
      :d="gp"
      fill="none"
      :stroke="'var(--border-subtle)'"
      stroke-width="1"
    />
    <!-- Axes -->
    <line
      v-for="(al, idx) in axisLines"
      :key="'a' + idx"
      :x1="al.x1" :y1="al.y1" :x2="al.x2" :y2="al.y2"
      stroke="var(--border-subtle)" stroke-width="1"
    />
    <!-- Data area -->
    <path
      :d="pathData"
      fill="rgba(240, 185, 11, 0.15)"
      stroke="var(--accent)"
      stroke-width="2"
      stroke-linejoin="round"
    />
    <!-- Data points -->
    <circle
      v-for="(v, idx) in dims.values"
      :key="'p' + idx"
      :cx="polar(idx, dims.labels.length, (v / 100) * r)[0]"
      :cy="polar(idx, dims.labels.length, (v / 100) * r)[1]"
      r="3"
      fill="var(--accent)"
    />
    <!-- Labels -->
    <text
      v-for="lp in labelPositions"
      :key="lp.label"
      :x="lp.x" :y="lp.y"
      text-anchor="middle"
      dominant-baseline="middle"
      fill="var(--text-muted)"
      font-size="11"
    >{{ lp.label }}</text>
  </svg>
</template>
```

### Step 6.2 — Rewrite ResumeOptimizer.vue

This is the most complex page. Full rewrite:

```vue
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { matchResume, tailorResume, getJDAnalyses, getResumeOptimizations } from '@/api'
import RadarChart from '@/components/RadarChart.vue'
import { ElMessage } from 'element-plus'

const resumeText = ref('')
const jdAnalysisText = ref('')
const loading = ref(false)
const matchResult = ref<any>(null)
const tailoredResult = ref('')
const error = ref('')
const activeTab = ref('match')
const currentOptId = ref<number | null>(null)
const showAnnotations = ref(true)

// Optimization flow steps
const optStep = ref(0) // 0: idle, 1-3: steps
const optSteps = [
  { label: '正在搜索相关 JD 信息...', icon: 'Search' },
  { label: '正在检索简历匹配片段...', icon: 'List' },
  { label: '正在生成优化版本...', icon: 'MagicStick' },
]

const jdHistory = ref<any[]>([])
const selectedJdId = ref<number | null>(null)
const historyLoading = ref(false)
const optHistory = ref<any[]>([])
const lastMatchedForTailor = ref('')

// Gap point expansion
const expandedGaps = ref<Set<number>>(new Set())

function toggleGap(idx: number) {
  const s = new Set(expandedGaps.value)
  s.has(idx) ? s.delete(idx) : s.add(idx)
  expandedGaps.value = s
}

// Score color
function scoreColor(s: number) {
  if (s >= 80) return 'var(--color-success)'
  if (s >= 60) return 'var(--color-warning)'
  return 'var(--color-danger)'
}

// Load history
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
    activeTab.value = 'tailored'
  }
}

watch(showAnnotations, async (val) => {
  if (!tailoredResult.value || !matchResult.value || loading.value) return
  loading.value = true; error.value = ''
  try {
    const res: any = await tailorResume(resumeText.value, jdAnalysisText.value, JSON.stringify(matchResult.value), currentOptId.value || undefined, val)
    tailoredResult.value = res.result
    if (res.opt_id) currentOptId.value = res.opt_id
    loadHistory()
  } catch (e: any) { error.value = e.message || '重新生成失败' }
  finally { loading.value = false }
})

onMounted(loadHistory)

async function handleMatch() {
  if (!resumeText.value.trim() || !jdAnalysisText.value.trim()) { error.value = '请填写简历并选择JD分析结果'; return }
  loading.value = true; error.value = ''; matchResult.value = null; tailoredResult.value = ''; activeTab.value = 'match'
  try {
    const res: any = await matchResume(resumeText.value, jdAnalysisText.value, selectedJdId.value || undefined)
    matchResult.value = res.result
    lastMatchedForTailor.value = JSON.stringify(res.result)
    if (res.opt_id) currentOptId.value = res.opt_id
    loadHistory()
  } catch (e: any) { error.value = e.message || '匹配分析失败' }
  finally { loading.value = false }
}

async function handleTailor() {
  if (!matchResult.value) { error.value = '请先完成匹配度分析'; return }
  loading.value = true; error.value = ''; tailoredResult.value = ''; optStep.value = 1

  // Simulate step progress
  const stepInterval = setInterval(() => {
    if (optStep.value < 3) optStep.value++
    else clearInterval(stepInterval)
  }, 2000)

  try {
    const res: any = await tailorResume(resumeText.value, jdAnalysisText.value, JSON.stringify(matchResult.value), currentOptId.value || undefined, showAnnotations.value)
    clearInterval(stepInterval)
    optStep.value = 3
    tailoredResult.value = res.result
    if (res.opt_id) currentOptId.value = res.opt_id
    activeTab.value = 'tailored'
    loadHistory()
    setTimeout(() => { optStep.value = 0 }, 500)
  } catch (e: any) {
    clearInterval(stepInterval)
    optStep.value = 0
    error.value = e.message || '简历优化失败'
  }
  finally { loading.value = false }
}

// Derive radar data from score_breakdown
const radarData = computed(() => {
  const bd = matchResult.value?.score_breakdown
  if (!bd) return {}
  // Use first 5 keys or fallback
  const keys = Object.keys(bd).slice(0, 5)
  const obj: Record<string, number> = {}
  keys.forEach(k => { obj[k] = bd[k] })
  return obj
})
</script>

<template>
  <div class="resume-page">
    <h2 class="page-title">简历智能优化</h2>
    <p class="page-sub">上传简历 + 选择历史JD分析，AI 评估匹配度并定向优化（RAG 检索增强）</p>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- Left: input area 1/3 -->
      <el-col :span="8">
        <div class="input-card">
          <h4 style="margin-bottom: 12px">简历文本</h4>
          <el-input v-model="resumeText" type="textarea" :rows="10" placeholder="粘贴你的简历全文..." />
        </div>

        <div class="input-card" style="margin-top: 16px">
          <div class="card-header-row">
            <h4>选择 JD 分析结果</h4>
            <el-button size="small" text @click="loadHistory" :loading="historyLoading">刷新</el-button>
          </div>
          <div v-if="jdHistory.length === 0" class="jd-empty">
            暂无历史，请先去「JD智能分析」页面分析职位。
          </div>
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
          <el-button type="primary" :loading="loading" @click="handleMatch" style="width: 100%; margin-top: 16px" :disabled="!selectedJdId" size="large">
            开始匹配分析
          </el-button>
        </div>
      </el-col>

      <!-- Right: results 2/3 -->
      <el-col :span="16">
        <!-- Optimization history timeline -->
        <div v-if="optHistory.length > 0" class="history-timeline">
          <div
            v-for="opt in optHistory"
            :key="opt.id"
            class="history-card"
            :class="{ active: currentOptId === opt.id }"
            @click="loadOpt(opt)"
          >
            <span v-if="opt.match_score" class="history-score" :style="{ background: scoreColor(opt.match_score) }">
              {{ opt.match_score }}
            </span>
            <div class="history-preview">{{ opt.resume_preview }}</div>
          </div>
        </div>

        <!-- Optimization flow -->
        <div v-if="optStep > 0" class="opt-flow">
          <div v-for="(step, idx) in optSteps" :key="idx" class="opt-step" :class="{ done: optStep > idx, active: optStep === idx }">
            <el-icon :size="18" v-if="optStep > idx"><Check /></el-icon>
            <el-icon :size="18" v-else-if="optStep === idx" class="spinning"><Loading /></el-icon>
            <span class="step-num" v-else>{{ idx + 1 }}</span>
            <span class="step-label">{{ step.label }}</span>
          </div>
        </div>

        <el-tabs v-model="activeTab" v-if="!optStep">
          <el-tab-pane label="匹配度分析" name="match">
            <div v-if="matchResult" class="match-area">
              <!-- Score + Radar row -->
              <div class="score-radar-row">
                <div class="score-display">
                  <div class="score-num" :style="{ color: scoreColor(matchResult.match_score) }">
                    {{ matchResult.match_score }}
                  </div>
                  <div class="score-label">匹配度评分</div>
                </div>
                <div v-if="Object.keys(radarData).length >= 3" class="radar-wrap">
                  <RadarChart :data="radarData" :size="180" />
                </div>
              </div>

              <!-- Score breakdown bars -->
              <div v-if="matchResult?.score_breakdown" class="breakdown">
                <div v-for="(score, label) in matchResult.score_breakdown" :key="label" class="breakdown-row">
                  <span class="breakdown-label">{{ label }}</span>
                  <el-progress :percentage="score" :color="scoreColor(score)" style="flex:1; margin: 0 12px" />
                  <span class="breakdown-val">{{ score }}</span>
                </div>
              </div>

              <!-- Matched points with evidence -->
              <div v-if="matchResult?.matched_points?.length" class="points-section">
                <h4 class="points-heading">匹配点</h4>
                <div v-for="(point, i) in matchResult.matched_points" :key="'m'+i" class="point-card matched">
                  <div class="point-header">
                    <span class="dot green"></span>
                    <span>{{ typeof point === 'string' ? point : point.point }}</span>
                  </div>
                  <div v-if="typeof point !== 'string' && (point.jd_evidence || point.resume_evidence)" class="point-evidence">
                    <div v-if="point.jd_evidence" class="evidence-line">JD原文: {{ point.jd_evidence }}</div>
                    <div v-if="point.resume_evidence" class="evidence-line">简历原文: {{ point.resume_evidence }}</div>
                  </div>
                </div>
              </div>

              <!-- Gap points with evidence and suggestions -->
              <div v-if="matchResult?.gap_points?.length" class="points-section">
                <h4 class="points-heading">差距点</h4>
                <div v-for="(point, i) in matchResult.gap_points" :key="'g'+i" class="point-card gap">
                  <div class="point-header" @click="point.suggestion ? toggleGap(i) : null" :style="{ cursor: point.suggestion ? 'pointer' : 'default' }">
                    <span class="dot red"></span>
                    <span>{{ typeof point === 'string' ? point : point.point }}</span>
                    <el-icon v-if="point.suggestion" :size="14" style="margin-left: auto">
                      <component :is="expandedGaps.has(i) ? 'ArrowUp' : 'ArrowDown'" />
                    </el-icon>
                  </div>
                  <div v-if="typeof point !== 'string' && (point.jd_evidence || point.resume_evidence)" class="point-evidence">
                    <div v-if="point.jd_evidence" class="evidence-line">JD原文: {{ point.jd_evidence }}</div>
                    <div v-if="point.resume_evidence" class="evidence-line">简历原文: {{ point.resume_evidence }}</div>
                  </div>
                  <div v-if="point.suggestion && expandedGaps.has(i)" class="point-suggestion">
                    {{ point.suggestion }}
                  </div>
                </div>
              </div>

              <div v-if="matchResult?.overall_assessment" class="overall">
                <h4>整体评价</h4>
                <p>{{ matchResult.overall_assessment }}</p>
              </div>

              <el-button type="success" :loading="loading" @click="handleTailor" size="large" style="width: 100%; margin-top: 20px">
                <el-icon><MagicStick /></el-icon>
                {{ tailoredResult ? '重新生成优化简历' : '一键优化 — 根据匹配结果自动优化简历' }}
              </el-button>
            </div>
            <div v-else class="empty-result">
              <el-empty description="等待匹配分析" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="优化后简历" name="tailored">
            <div v-if="tailoredResult" class="tailored-area">
              <div class="tailored-toolbar">
                <span style="font-size: 13px; color: var(--text-secondary)">改动注释</span>
                <el-switch v-model="showAnnotations" :disabled="loading" size="small" />
                <span style="font-size: 12px; color: var(--text-muted)">{{ showAnnotations ? '开启' : '关闭' }}</span>
              </div>
              <div class="letter-paper">
                {{ tailoredResult }}
              </div>
              <div class="tailored-toolbar bottom">
                <el-button size="small" @click="navigator.clipboard?.writeText(tailoredResult)">复制</el-button>
                <el-button size="small" @click="() => { const b = new Blob([tailoredResult],{type:'text/plain'}); const a=document.createElement('a'); a.href=URL.createObjectURL(b); a.download='resume.txt'; a.click() }">下载为文本</el-button>
              </div>
            </div>
            <el-empty v-else description="请先完成匹配度分析并点击优化" />
          </el-tab-pane>
        </el-tabs>
      </el-col>
    </el-row>

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
  </div>
</template>

<style scoped>
.resume-page { max-width: 1300px; }
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

.input-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  padding: 20px;
}

.card-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.card-header-row h4 { margin: 0; }

.jd-empty { color: var(--text-muted); padding: 12px 0; font-size: 13px; }

.jd-list { max-height: 240px; overflow-y: auto; }

.jd-item {
  padding: 10px 12px; margin-bottom: 6px; border-radius: 8px;
  border: 1px solid var(--border-subtle); cursor: pointer;
  transition: all var(--t-fast) ease-out;
}
.jd-item:hover { border-color: var(--accent); }
.jd-item.selected { border-color: var(--accent); background: var(--accent-subtle); }

.jd-item-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.jd-item-preview { font-size: 12px; color: var(--text-muted); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* History timeline */
.history-timeline {
  display: flex; gap: 10px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 16px;
}

.history-card {
  flex-shrink: 0; width: 170px; padding: 10px 12px;
  border: 1px solid var(--border-subtle); border-radius: var(--radius-btn);
  cursor: pointer; transition: all var(--t-fast) ease-out;
}
.history-card:hover { border-color: var(--accent); }
.history-card.active { border-color: var(--accent); background: var(--accent-subtle); }

.history-score {
  display: inline-block; width: 24px; height: 18px; line-height: 18px;
  text-align: center; border-radius: 4px; font-size: 11px; font-weight: 600;
  color: #fff; margin-bottom: 4px;
}

.history-preview { font-size: 12px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Optimization flow */
.opt-flow {
  display: flex; flex-direction: column; gap: 12px;
  padding: 24px; background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); margin-bottom: 16px;
}

.opt-step { display: flex; align-items: center; gap: 12px; font-size: 14px; color: var(--text-muted); transition: color var(--t-normal) ease; }

.opt-step.done { color: var(--accent); }
.opt-step.active { color: var(--text-primary); }

.step-num {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid var(--text-muted); display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; flex-shrink: 0;
}

.opt-step.done .step-num { border-color: var(--accent); background: var(--accent); color: #0b0a1a; }
.opt-step.active .step-num { border-color: var(--accent); }

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Match result */
.match-area {
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); padding: 24px;
}

.score-radar-row {
  display: flex; align-items: center; justify-content: center; gap: 40px; margin-bottom: 20px;
}

.score-display { text-align: center; }
.score-num { font-size: 72px; font-weight: 800; line-height: 1; }
.score-label { color: var(--text-muted); margin-top: 4px; font-size: 13px; }

.breakdown { margin-bottom: 20px; }
.breakdown-row { display: flex; align-items: center; margin-bottom: 10px; }
.breakdown-label { width: 80px; font-size: 13px; color: var(--text-secondary); flex-shrink: 0; text-align: right; }
.breakdown-val { width: 36px; text-align: right; font-size: 13px; color: var(--text-primary); font-weight: 600; }

.points-section { margin-bottom: 16px; }
.points-heading { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; }

.point-card {
  padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;
  border: 1px solid var(--border-subtle);
}

.point-card.matched { background: rgba(52, 211, 153, 0.05); }
.point-card.gap { background: rgba(248, 113, 113, 0.05); }

.point-header { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-primary); }

.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot.green { background: var(--color-success); }
.dot.red { background: var(--color-danger); }

.point-evidence { margin-top: 6px; padding-left: 16px; }
.evidence-line { font-size: 12px; color: var(--text-muted); line-height: 1.5; }

.point-suggestion {
  margin-top: 8px; padding: 10px 14px; background: rgba(248, 113, 113, 0.08);
  border-radius: 6px; font-size: 13px; color: var(--text-secondary); line-height: 1.5;
  animation: slide-down 0.25s ease-out;
}

@keyframes slide-down { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }

.overall { margin-top: 16px; }
.overall h4 { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.overall p { font-size: 14px; color: var(--text-secondary); line-height: 1.6; }

.empty-result {
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); min-height: 300px;
  display: flex; align-items: center; justify-content: center;
}

/* Tailored result */
.tailored-area { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-card); padding: 24px; }

.tailored-toolbar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
}
.tailored-toolbar.bottom { margin-top: 12px; margin-bottom: 0; padding-top: 12px; border-top: 1px solid var(--border-subtle); }

.letter-paper {
  white-space: pre-wrap; line-height: 1.8; font-size: 14px;
  background: linear-gradient(135deg, #faf8f0, #f5f0e0);
  color: #2c2416; padding: 32px; border-radius: 8px;
  box-shadow: inset 0 0 60px rgba(0,0,0,0.03);
}
</style>
```

Fix: add `computed` import at the top:

```ts
import { ref, computed, onMounted, watch } from 'vue'
```

### Step 6.3 — Verify

Run dev server. Open `/resume`. Paste resume text, select a JD, click "开始匹配分析". Confirm:
- Score display with large number and color
- Radar chart showing 5 dimensions
- Match/gap point cards with evidence lines
- Gap cards expand to show suggestions on click
- History timeline horizontal scroll
- "一键优化" triggers 3-step flow animation
- Tailored resume shows on letter-paper background

---

## Task 7: 求职信 CoverLetter

**Files:**
- MODIFY `frontend/src/views/CoverLetter.vue`

### Step 7.1 — Rewrite CoverLetter.vue

Fully rewrite `frontend/src/views/CoverLetter.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { generateCoverLetter } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const jdText = ref('')
const resumeText = ref('')
const candidateName = ref('')
const style = ref('formal')
const recipient = ref('招聘负责人')
const loading = ref(false)
const result = ref('')
const error = ref('')
const genStep = ref(0) // 0: idle, 1-3: generating

const styleOptions = [
  {
    value: 'formal',
    label: '正式商务',
    desc: '适合传统企业、金融、咨询',
    preview: '尊敬的XX公司招聘负责人：\n\n获悉贵公司正在招聘相关岗位，我对此深感兴趣...',
    accent: '#1c1845',
  },
  {
    value: 'casual',
    label: '亲和自然',
    desc: '适合互联网创业公司、创意行业',
    preview: '你好！看到你们在招人，我觉得自己还挺合适的～',
    accent: '#f5cc3a',
  },
  {
    value: 'tech',
    label: '技术极客',
    desc: '适合纯技术岗位',
    preview: 'TL;DR: 3年AI产品经验，大模型+RAG全栈，求勾搭。',
    accent: '#34d399',
  },
]

const genSteps = [
  { label: '正在分析目标公司需求...', icon: 'Search' },
  { label: '正在匹配你的相关经历...', icon: 'List' },
  { label: '正在撰写个性化求职信...', icon: 'Edit' },
]

async function handleGenerate() {
  if (!jdText.value.trim() || !resumeText.value.trim()) { error.value = '请填写JD文本和简历'; return }
  loading.value = true; error.value = ''; result.value = ''; genStep.value = 1

  const stepInterval = setInterval(() => {
    if (genStep.value < 3) genStep.value++
    else clearInterval(stepInterval)
  }, 2000)

  try {
    const res: any = await generateCoverLetter({
      jd_text: jdText.value,
      resume_text: resumeText.value,
      candidate_name: candidateName.value || '求职者',
      style: style.value,
      recipient: recipient.value,
    })
    clearInterval(stepInterval)
    genStep.value = 3
    result.value = res.result
    setTimeout(() => { genStep.value = 0 }, 500)
  } catch (e: any) {
    clearInterval(stepInterval)
    genStep.value = 0
    error.value = e.message || '生成失败'
  }
  finally { loading.value = false }
}

async function handleRegenerate() {
  try {
    await ElMessageBox.confirm('确定要重新生成吗？当前结果将被覆盖。', '确认', { type: 'warning' })
    handleGenerate()
  } catch { /* cancelled */ }
}

async function copyResult() {
  try {
    await navigator.clipboard.writeText(result.value)
    ElMessage.success('已复制到剪贴板')
  } catch { ElMessage.error('复制失败') }
}

function downloadTxt() {
  const blob = new Blob([result.value], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = '求职信.txt'
  a.click()
  URL.revokeObjectURL(a.href)
}

const hasContent = (t: string) => t.trim().length > 0
</script>

<template>
  <div class="cover-page">
    <h2 class="page-title">求职信生成</h2>
    <p class="page-sub">Chain-of-Thought 链式 Prompt：公司需求分析 → 经历匹配 → 求职信生成 · 支持 3 种风格</p>

    <!-- Input section: 3 cards -->
    <div class="input-row">
      <div class="input-card">
        <div class="card-head">
          <h4>职位描述</h4>
          <el-icon v-if="hasContent(jdText)" color="var(--color-success)" :size="16"><Check /></el-icon>
        </div>
        <el-input v-model="jdText" type="textarea" :rows="6" placeholder="粘贴目标职位 JD..." />
      </div>

      <div class="input-card">
        <div class="card-head">
          <h4>你的简历</h4>
          <el-icon v-if="hasContent(resumeText)" color="var(--color-success)" :size="16"><Check /></el-icon>
        </div>
        <el-input v-model="resumeText" type="textarea" :rows="6" placeholder="粘贴你的简历..." />
      </div>

      <div class="input-card">
        <div class="card-head">
          <h4>收信人信息</h4>
        </div>
        <el-input v-model="candidateName" placeholder="你的姓名" style="margin-bottom: 8px" />
        <el-input v-model="recipient" placeholder="收信人（如：招聘负责人）" />
      </div>
    </div>

    <!-- Style selector: 3 cards -->
    <div class="style-row">
      <h4 style="margin-bottom: 12px">选择风格</h4>
      <div class="style-cards">
        <div
          v-for="opt in styleOptions"
          :key="opt.value"
          class="style-card"
          :class="{ selected: style === opt.value }"
          @click="style = opt.value"
        >
          <div class="style-accent-strip" :style="{ background: opt.accent }"></div>
          <div class="style-body">
            <div class="style-check">
              <span class="style-name">{{ opt.label }}</span>
              <el-icon v-if="style === opt.value" color="var(--accent)" :size="16"><Check /></el-icon>
            </div>
            <p class="style-desc">{{ opt.desc }}</p>
            <div class="style-preview">{{ opt.preview }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Generate button -->
    <button class="generate-btn" :class="{ loading: loading }" :disabled="loading" @click="handleGenerate">
      <el-icon :size="20"><MagicStick /></el-icon>
      {{ loading ? '生成中...' : '生成求职信' }}
    </button>

    <!-- Generation animation -->
    <div v-if="genStep > 0" class="gen-flow">
      <div v-for="(step, idx) in genSteps" :key="idx" class="gen-step" :class="{ done: genStep > idx, active: genStep === idx }">
        <el-icon :size="18" v-if="genStep > idx" color="var(--accent)"><Check /></el-icon>
        <el-icon :size="18" v-else-if="genStep === idx" class="spinning" color="var(--accent)"><Loading /></el-icon>
        <span v-else class="gstep-num">{{ idx + 1 }}</span>
        <span class="gstep-label">{{ step.label }}</span>
      </div>
    </div>

    <!-- Result: letter-style -->
    <div v-if="result && genStep === 0" class="result-area">
      <div class="letter-toolbar">
        <el-button size="small" @click="copyResult">复制全文</el-button>
        <el-button size="small" @click="downloadTxt">下载为 .txt</el-button>
        <el-button size="small" @click="handleRegenerate">重新生成</el-button>
      </div>
      <div class="letter-paper">
        {{ result }}
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" style="margin-top: 16px" />
  </div>
</template>

<style scoped>
.cover-page { max-width: 1000px; }
.page-title { margin-bottom: 4px; }
.page-sub { color: var(--text-muted); font-size: 13px; }

/* Input row */
.input-row { display: flex; gap: 16px; margin-top: 24px; }
.input-card {
  flex: 1; background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); padding: 20px;
}

.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.card-head h4 { margin: 0; }

/* Style selector */
.style-row { margin-top: 24px; }

.style-cards { display: flex; gap: 12px; }

.style-card {
  flex: 1; background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card); overflow: hidden; cursor: pointer;
  transition: all var(--t-fast) ease-out;
}

.style-card:hover { border-color: var(--text-muted); }

.style-card.selected {
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(240, 185, 11, 0.15);
}

.style-accent-strip { height: 4px; }

.style-body { padding: 14px 16px; }

.style-check { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.style-name { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.style-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }

.style-preview {
  font-size: 11px; color: var(--text-secondary); line-height: 1.5;
  white-space: pre-line; opacity: 0.7; font-style: italic;
}

/* Generate button */
.generate-btn {
  display: flex; align-items: center; justify-content: center;
  gap: 10px; width: 100%; height: 48px; margin-top: 24px;
  background: linear-gradient(135deg, var(--accent), #d4a40a);
  color: #0b0a1a; border: none; border-radius: var(--radius-btn);
  font-size: 16px; font-weight: 700; cursor: pointer;
  transition: all var(--t-fast) ease-out;
}

.generate-btn:hover:not(:disabled) {
  transform: scale(1.02); filter: brightness(1.1);
}

.generate-btn:active:not(:disabled) { transform: scale(0.98); }
.generate-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.generate-btn.loading { opacity: 0.8; }

/* Generation flow */
.gen-flow {
  display: flex; flex-direction: column; gap: 12px;
  margin-top: 24px; padding: 24px;
  background: var(--bg-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
}

.gen-step { display: flex; align-items: center; gap: 12px; font-size: 14px; color: var(--text-muted); transition: color var(--t-normal) ease; }

.gen-step.done { color: var(--accent); }
.gen-step.active { color: var(--text-primary); }

.gstep-num {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid var(--text-muted); display: flex;
  align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; flex-shrink: 0;
}

.gen-step.done .gstep-num { border-color: var(--accent); background: var(--accent); color: #0b0a1a; }
.gen-step.active .gstep-num { border-color: var(--accent); }

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Letter result */
.result-area { margin-top: 24px; }

.letter-toolbar {
  display: flex; gap: 8px; margin-bottom: 12px;
}

.letter-paper {
  white-space: pre-wrap; line-height: 1.8; font-size: 15px;
  background: linear-gradient(135deg, #faf8f0, #f5f0e0);
  color: #2c2416; padding: 40px; border-radius: 12px;
  box-shadow: inset 0 0 60px rgba(0,0,0,0.03);
  border: 1px solid rgba(0,0,0,0.06);
}
</style>
```

### Step 7.2 — Verify

Run dev server. Open `/cover-letter`. Confirm:
- 3 input cards side by side (JD, resume, recipient info)
- 3 style cards with colored accent strips, preview text, and check mark on selected
- Golden gradient "生成求职信" button with sparkle icon
- 3-step generation flow animation
- Result shows on letter-paper background with toolbar

---

## Task 8: 统一 Review

**Files:**
- Check all modified files

### Step 8.1 — Build check

Run from `frontend/`:

```bash
npm run build
```

Verify no TypeScript errors and no build warnings.

### Step 8.2 — Visual consistency check

Manually verify across all 5 pages:
- All use `--bg-deepest` as page background
- All cards use `--bg-card` + `--border-subtle` border
- All primary buttons use gold `--accent`
- All text uses CSS variables (no hardcoded colors)
- Sidebar consistent on all pages
- Page title styling consistent across all pages (h2 + subtitle)

### Step 8.3 — Checklist

- [ ] Colors: No hardcoded hex values exist in `<style>` blocks (only CSS variables)
- [ ] Fonts: Inter + Noto Sans SC loaded and applied
- [ ] Transitions: All animations use `transform`/`opacity`, respect `prefers-reduced-motion`
- [ ] Contrast: Gold on dark meets AAA; text on cards meets AA
- [ ] Responsive: Layouts degrade gracefully on narrow viewports (no horizontal scroll)
- [ ] Empty states: Tracker page shows EmptyState component when no data
- [ ] Loading states: JD Analyzer shows LoadingSkeleton; CoverLetter/ResumeOptimizer show step flow
- [ ] No console errors: Check browser console for each page

---

## Dependencies Between Tasks

```
Task 1 (Tokens) ──> Task 2 (Sidebar) ──> Tasks 3-7 (Pages, any order) ──> Task 8 (Review)
```

Tasks 3, 4, 5, 6, 7 can be done in parallel after Tasks 1-2 are complete. Task 8 must be last.

## Total Files

- **CREATE:** 8 (variables.css, global.css, element-overrides.css, transitions.css, StatusIndicator.vue, LoadingSkeleton.vue, RadarChart.vue, ProgressBar.vue, EmptyState.vue)
- **MODIFY:** 7 (index.html, main.ts, App.vue, Dashboard.vue, JDAnalyzer.vue, ResumeOptimizer.vue, CoverLetter.vue, Tracker.vue)
- **NO CHANGE:** 3 (api/index.ts, router/index.ts, vite.config.ts)
