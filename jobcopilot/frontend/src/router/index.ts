import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
    },
    {
      path: '/jd',
      name: 'JDAnalyzer',
      component: () => import('@/views/JDAnalyzer.vue'),
    },
    {
      path: '/resume',
      name: 'ResumeOptimizer',
      component: () => import('@/views/ResumeOptimizer.vue'),
    },
    {
      path: '/cover-letter',
      name: 'CoverLetter',
      component: () => import('@/views/CoverLetter.vue'),
    },
    {
      path: '/tracker',
      name: 'Tracker',
      component: () => import('@/views/Tracker.vue'),
    },
  ],
})

export default router
