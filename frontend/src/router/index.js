import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

export const navigation = [
  {
    path: '/dashboard',
    title: '仪表盘',
    english: 'Dashboard',
    icon: 'DataAnalysis',
    group: 'workspace',
    component: () => import('../views/dashboard/DashboardView.vue'),
  },

  {
    path: '/assets',
    title: '资产管理',
    english: 'Assets',
    icon: 'Monitor',
    group: 'asset',
    component: () => import('../views/assets/AssetsView.vue'),
  },
  {
    path: '/scans',
    title: '扫描任务',
    english: 'Scans',
    icon: 'Search',
    group: 'asset',
    component: () => import('../views/scans/ScansView.vue'),
  },
  {
    path: '/discovery',
    title: '资产发现',
    english: 'Discovery',
    icon: 'Connection',
    group: 'asset',
    component: () => import('../views/discovery/DiscoveryView.vue'),
  },

  {
    path: '/findings',
    title: '安全发现',
    english: 'Findings',
    icon: 'Warning',
    group: 'security',
    component: () => import('../views/findings/FindingsView.vue'),
  },
  {
    path: '/investigations',
    title: 'AI 调查中心',
    english: 'Investigations',
    icon: 'Cpu',
    group: 'security',
    component: () => import('../views/investigations/InvestigationsView.vue'),
  },
  {
    path: '/response',
    title: '响应中心',
    english: 'Response',
    icon: 'SetUp',
    group: 'security',
    component: () => import('../views/response/ResponseView.vue'),
  },

  {
    path: '/audit',
    title: '审计中心',
    english: 'Audit',
    icon: 'Document',
    group: 'governance',
    component: () => import('../views/audit/AuditView.vue'),
  },
  {
    path: '/settings',
    title: '系统设置',
    english: 'Settings',
    icon: 'Setting',
    group: 'governance',
    component: () => import('../views/settings/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/', component: MainLayout, redirect: '/dashboard',
      children: navigation.map((item) => ({
        path: item.path.slice(1), name: item.english.toLowerCase(), component: item.component,
        meta: { title: item.title, english: item.english },
      })),
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => { document.title = `${to.meta.title || '仪表盘'} · SentinelAgent` })
export default router
