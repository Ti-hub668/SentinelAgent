<script setup>
import {
  computed,
  onMounted,
  onUnmounted,
  ref,
} from 'vue'

import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import {
  DataAnalysis,
  Monitor,
  Search,
  Connection,
  Warning,
  Cpu,
  SetUp,
  Document,
  Setting,
  Fold,
  Expand,
  Clock,
  Lock,
} from '@element-plus/icons-vue'

import axios from 'axios'

import { navigation } from '../router'
import { useUiStore } from '../stores/ui'

const icons = {
  DataAnalysis,
  Monitor,
  Search,
  Connection,
  Warning,
  Cpu,
  SetUp,
  Document,
  Setting,
}

const navigationGroups = computed(() => [
  {
    key: 'workspace',
    label: t('navigationGroups.workspace'),
    english: t('navigationGroups.workspace'),
  },
  {
    key: 'asset',
    label: t('navigationGroups.asset'),
    english: t('navigationGroups.asset'),
  },
  {
    key: 'security',
    label: t('navigationGroups.security'),
    english: t('navigationGroups.security'),
  },
  {
    key: 'governance',
    label: t('navigationGroups.governance'),
    english: t('navigationGroups.governance'),
  },
])

const groupedNavigation = computed(() =>
  navigationGroups.value.map((group) => ({
    ...group,
    items: navigation.filter(
      (item) => item.group === group.key,
    ),
  })),
)

const route = useRoute()
const ui = useUiStore()
const { t, locale } = useI18n()

const now = ref(new Date())
const apiOnline = ref(false)
const apiChecking = ref(true)

const time = computed(() =>
  now.value.toLocaleTimeString(
    locale.value,
    {
      hour12: false,
    },
  ),
)

let timer
let healthTimer

async function checkApiHealth() {
  apiChecking.value = true

  try {
    const response = await axios.get('/health', {
      timeout: 5000,
    })

    apiOnline.value = response.data?.status === 'healthy'
  } catch (error) {
    apiOnline.value = false
  } finally {
    apiChecking.value = false
  }
}

onMounted(() => {
  timer = setInterval(() => {
    now.value = new Date()
  }, 1000)

  checkApiHealth()

  healthTimer = setInterval(() => {
    checkApiHealth()
  }, 30000)
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(healthTimer)
})
</script>

<template>
  <div
    class="app-shell"
    :class="{ 'sidebar-collapsed': ui.collapsed }"
  >
    <aside class="sidebar">
      <router-link
        to="/dashboard"
        class="brand"
        :aria-label="t('layout.home')"
      >
        <span class="brand-mark">
          <el-icon>
            <Lock />
          </el-icon>
        </span>

        <span
          v-if="!ui.collapsed"
          class="brand-text"
        >
          Sentinel<span class="brand-accent">Agent</span>

          <small>
            {{ t('navigationGroups.security') }}
          </small>
        </span>
      </router-link>

      <nav :aria-label="t('layout.mainNavigation')">
        <div
          v-for="group in groupedNavigation"
          :key="group.key"
          class="nav-group"
        >
          <div
            v-if="!ui.collapsed"
            class="nav-caption"
          >
            {{ group.label }}
          </div>

          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            active-class="is-active"
            :title="t(`navigation.${item.i18nKey}`)"
            :aria-label="t(`navigation.${item.i18nKey}`)"
          >
            <el-icon>
              <component :is="icons[item.icon]" />
            </el-icon>

            <span v-if="!ui.collapsed">
              {{ t(`navigation.${item.i18nKey}`) }}
            </span>

            <small
              v-if="
                !ui.collapsed &&
                item.english === 'Investigations'
              "
              class="ai-badge"
            >
              AI
            </small>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-bottom">
        <div
          v-if="!ui.collapsed"
          class="phase-note"
        >
          <span class="status-dot"></span>

          {{ t('layout.frontendFramework') }}
        </div>

        <div class="profile">
          <span class="avatar">
            S
          </span>

          <div v-if="!ui.collapsed">
          <strong>
            {{ t('layout.workspace') }}
          </strong>

            <small>
              SentinelAgent v1.0-demo
            </small>
          </div>
        </div>
      </div>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <div class="topbar-left">
          <el-button
            text
            circle
            :aria-label="
              ui.collapsed
                ? t('layout.expandSidebar')
                : t('layout.collapseSidebar')
            "
            @click="ui.toggleSidebar"
          >
            <el-icon>
              <component
                :is="
                  ui.collapsed
                    ? Expand
                    : Fold
                "
              />
            </el-icon>
          </el-button>

          <strong>
            {{
              route.meta.i18nKey
                ? t(`navigation.${route.meta.i18nKey}`)
                : t('navigation.dashboard')
            }}
          </strong>

          <span class="breadcrumb">
            / {{ t(`navigation.${route.meta.i18nKey || 'dashboard'}`) }}
          </span>
        </div>

        <div class="topbar-right">
          <span class="clock">
            <el-icon>
              <Clock />
            </el-icon>

            {{ time }}
          </span>

          <span
            class="connection-state"
            :class="{
              online: apiOnline,
              offline: !apiOnline && !apiChecking,
            }"
          >
            <span
              class="status-dot"
              :class="{
                neutral: apiChecking,
                online: apiOnline,
                offline: !apiOnline && !apiChecking,
              }"
            ></span>

            {{
              apiChecking
                ? t('layout.apiChecking')
                : apiOnline
                  ? t('layout.apiOnline')
                  : t('layout.apiOffline')
            }}
          </span>

          <span class="topbar-divider"></span>

          <span class="workspace-label">
            {{ t('layout.localDevelopment') }}
          </span>
        </div>
      </header>

      <main class="page-content">
        <router-view />
      </main>

      <footer class="page-footer">
        <span>
          {{ t('layout.footer') }}
        </span>

        <span>
          {{ t('layout.foundation') }}
        </span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: #f5f7fb;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 30;

  width: 240px;

  display: flex;
  flex-direction: column;

  background: #ffffff;
  border-right: 1px solid #e7ebf1;

  transition: width 0.2s ease;
}

.sidebar-collapsed .sidebar {
  width: 72px;
}

.brand {
  min-height: 72px;

  display: flex;
  align-items: center;

  gap: 12px;

  padding: 0 20px;

  border-bottom: 1px solid #edf0f5;

  text-decoration: none;
}

.brand-mark {
  width: 36px;
  height: 36px;

  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 10px;

  color: #ffffff;

  background:
    linear-gradient(
      135deg,
      #1769ff,
      #15b7d3
    );
}

.brand-text {
  min-width: 0;

  color: #172033;

  font-size: 17px;
  font-weight: 700;
  line-height: 1.1;
}

.brand-accent {
  color: #1769ff;
}

.brand-text small {
  display: block;

  margin-top: 5px;

  color: #97a1b1;

  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.9px;
}

.sidebar nav {
  flex: 1;

  padding: 4px 12px 12px;

  overflow-y: auto;
  overflow-x: hidden;
}

.nav-group + .nav-group {
  margin-top: 8px;
}

.nav-caption {
  padding: 14px 12px 8px;

  color: #94a0b2;

  font-size: 10px;
  font-weight: 600;

  white-space: nowrap;
}

.nav-caption span {
  margin-left: 5px;

  color: #b2bbc7;

  font-size: 8px;
  font-weight: 500;
}

.nav-item {
  position: relative;

  min-height: 44px;

  display: flex;
  align-items: center;

  gap: 12px;

  margin-bottom: 4px;
  padding: 0 13px;

  border-radius: 9px;

  color: #5e697a;

  text-decoration: none;

  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.nav-item:hover {
  background: #f4f7fb;
  color: #233044;
}

.nav-item.is-active {
  background: #edf5ff;
  color: #1769ff;

  font-weight: 600;
}

.nav-item.is-active::before {
  content: '';

  position: absolute;

  left: 0;

  width: 3px;
  height: 22px;

  border-radius: 0 3px 3px 0;

  background: #1769ff;
}

.nav-item .el-icon {
  width: 20px;

  flex-shrink: 0;

  font-size: 18px;
}

.ai-badge {
  margin-left: auto;

  padding: 2px 6px;

  border-radius: 5px;

  color: #1769ff;

  background: #eaf3ff;

  font-size: 9px;
  font-weight: 700;
}

.sidebar-bottom {
  padding: 14px;

  border-top: 1px solid #edf0f5;
}

.phase-note {
  display: flex;
  align-items: center;

  gap: 8px;

  margin-bottom: 12px;
  padding: 9px 10px;

  border-radius: 8px;

  color: #5d6878;

  background: #f7f9fc;

  font-size: 11px;
}

.profile {
  display: flex;
  align-items: center;

  gap: 10px;

  min-height: 42px;

  padding: 5px 6px;
}

.avatar {
  width: 34px;
  height: 34px;

  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 9px;

  color: #ffffff;

  background:
    linear-gradient(
      135deg,
      #27364e,
      #516783
    );

  font-weight: 700;
}

.profile div {
  min-width: 0;
}

.profile strong {
  display: block;

  color: #344054;

  font-size: 12px;
}

.profile small {
  display: block;

  margin-top: 3px;

  color: #98a2b3;

  font-size: 10px;
}

.main-shell {
  width: calc(100% - 240px);

  display: flex;
  flex-direction: column;

  min-height: 100vh;

  margin-left: 240px;

  transition:
    margin-left 0.2s ease,
    width 0.2s ease;
}

.sidebar-collapsed .main-shell {
  width: calc(100% - 72px);
  margin-left: 72px;
}

.topbar {
  position: sticky;
  top: 0;

  z-index: 20;

  min-height: 64px;

  display: flex;
  align-items: center;
  justify-content: space-between;

  gap: 18px;

  padding: 12px 24px;

  background:
    rgba(
      255,
      255,
      255,
      0.95
    );

  border-bottom: 1px solid #e8edf3;

  backdrop-filter: blur(8px);

  flex-wrap: wrap;
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
}

.topbar-left {
  gap: 10px;
  min-width: 0;
  flex: 1 1 auto;
}

.topbar-left strong {
  color: #253044;

  font-size: 14px;
}

.breadcrumb {
  color: #9aa4b4;

  font-size: 12px;
}

.topbar-right {
  gap: 16px;

  color: #697586;

  font-size: 12px;
}

.clock {
  display: flex;
  align-items: center;

  gap: 6px;
}

.connection-state {
  display: flex;
  align-items: center;

  gap: 7px;

  transition: color 0.15s ease;
}

.connection-state.online {
  color: #239774;
}

.connection-state.offline {
  color: #d45e68;
}

.status-dot {
  width: 7px;
  height: 7px;

  display: inline-block;

  border-radius: 50%;

  background: #24b18d;
}

.status-dot.neutral {
  background: #aeb6c2;
}

.status-dot.online {
  background: #24b18d;

  box-shadow:
    0 0 0 3px
    rgba(36, 177, 141, 0.1);
}

.status-dot.offline {
  background: #df5965;

  box-shadow:
    0 0 0 3px
    rgba(223, 89, 101, 0.1);
}

.topbar-divider {
  width: 1px;
  height: 18px;

  background: #e4e8ee;
}

.workspace-label {
  padding: 5px 9px;

  border-radius: 6px;

  color: #687386;

  background: #f5f7fa;

  font-size: 11px;
}

.page-content {
  flex: 1;

  padding: 24px;
}

.page-footer {
  min-height: 46px;

  display: flex;
  align-items: center;
  justify-content: space-between;

  gap: 20px;

  padding: 12px 24px;

  color: #a0a8b5;

  border-top: 1px solid #e8edf3;

  background: #ffffff;

  font-size: 10px;

  flex-wrap: wrap;
}

.sidebar-collapsed .brand {
  justify-content: center;

  padding-left: 0;
  padding-right: 0;
}

.sidebar-collapsed .nav-item {
  justify-content: center;

  padding-left: 0;
  padding-right: 0;
}

.sidebar-collapsed .profile {
  justify-content: center;
}

.sidebar-collapsed .sidebar-bottom {
  padding-left: 8px;
  padding-right: 8px;
}

@media (max-width: 1200px) {
  .topbar-right .clock {
    display: none;
  }
}

.nav-caption { white-space: normal; overflow: visible; overflow-wrap: anywhere; }
.nav-item > span { min-width: 0; white-space: normal; overflow: visible; overflow-wrap: anywhere; }
.topbar-left strong { min-width: 0; white-space: normal; overflow: visible; overflow-wrap: anywhere; }
</style>