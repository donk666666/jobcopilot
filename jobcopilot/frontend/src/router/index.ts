import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/jd',
      name: 'JDAnalyzer',
      component: () => import('@/views/JDAnalyzer.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/resume',
      name: 'ResumeOptimizer',
      component: () => import('@/views/ResumeOptimizer.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/cover-letter',
      name: 'CoverLetter',
      component: () => import('@/views/CoverLetter.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/greet',
      name: 'Greeting',
      component: () => import('@/views/Greeting.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/tracker',
      name: 'Tracker',
      component: () => import('@/views/Tracker.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/materials',
      name: 'Materials',
      component: () => import('@/views/MaterialsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
    },
  ],
})

// 路由守卫：未登录跳 /login
router.beforeEach((to, _from, next) => {
  const requiresAuth = to.meta?.requiresAuth
  const token = localStorage.getItem('token')
  if (requiresAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
