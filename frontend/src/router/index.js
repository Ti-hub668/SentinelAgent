import { watch } from 'vue'
import i18n from '../i18n'
import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

export const navigation = [
  {
    path: '/dashboard',
    title: '仪表盘',
    english: 'Dashboard',
    i18nKey: 'dashboard',
    icon: 'DataAnalysis',
    group: 'workspace',
    component: () =>
      import('../views/dashboard/DashboardView.vue'),
  },

  {
    path: '/assets',
    title: '资产管理',
    english: 'Assets',
    i18nKey: 'assets',
    icon: 'Monitor',
    group: 'asset',
    component: () =>
      import('../views/assets/AssetsView.vue'),
  },

  {
    path: '/scans',
    title: '扫描任务',
    english: 'Scans',
    i18nKey: 'scans',
    icon: 'Search',
    group: 'asset',
    component: () =>
      import('../views/scans/ScansView.vue'),
  },

  {
    path: '/discovery',
    title: '资产发现',
    english: 'Discovery',
    i18nKey: 'discovery',
    icon: 'Connection',
    group: 'asset',
    component: () =>
      import('../views/discovery/DiscoveryView.vue'),
  },

  {
    path: '/findings',
    title: '安全发现',
    english: 'Findings',
    i18nKey: 'findings',
    icon: 'Warning',
    group: 'security',
    component: () =>
      import('../views/findings/FindingsView.vue'),
  },

  {
    path: '/investigations',
    title: 'AI 调查中心',
    english: 'Investigations',
    i18nKey: 'investigations',
    icon: 'Cpu',
    group: 'security',
    component: () =>
      import(
        '../views/investigations/InvestigationsView.vue'
      ),
  },

  {
    path: '/response',
    title: '响应中心',
    english: 'Response',
    i18nKey: 'response',
    icon: 'SetUp',
    group: 'security',
    component: () =>
      import('../views/response/ResponseView.vue'),
  },

  {
    path: '/audit',
    title: '审计中心',
    english: 'Audit',
    i18nKey: 'audit',
    icon: 'Document',
    group: 'governance',
    component: () =>
      import('../views/audit/AuditView.vue'),
  },

  {
    path: '/settings',
    title: '系统设置',
    english: 'Settings',
    i18nKey: 'settings',
    icon: 'Setting',
    group: 'governance',
    component: () =>
      import('../views/settings/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/', component: MainLayout, redirect: '/dashboard',
      children: navigation.map((item) => ({
        path: item.path.slice(1), name: item.english.toLowerCase(), component: item.component,
       meta: {
        title: item.title,
        english: item.english,
        i18nKey: item.i18nKey,
      },
      })),
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

function updateDocumentTitle(route = router.currentRoute.value) {
  document.title = `${i18n.global.t(`navigation.${route.meta.i18nKey || 'dashboard'}`)} · SentinelAgent`
}
router.afterEach(updateDocumentTitle)
watch(i18n.global.locale, () => updateDocumentTitle(), { immediate: true })
export default router
