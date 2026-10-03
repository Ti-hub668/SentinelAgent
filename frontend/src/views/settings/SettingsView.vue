<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { STORAGE_KEY } from '../../i18n'
import { getHealth } from '../../api'

const { locale, t } = useI18n()
const currentLanguage = computed({
  get: () => locale.value,
  set(value) {
    locale.value = value
    localStorage.setItem(STORAGE_KEY, value)
    document.documentElement.lang = value
    ElMessage.success(t('settings.saved'))
  },
})
const checking = ref(false)
const backendStatus = ref('notChecked')
const checkedAt = ref(null)
const controller = new AbortController()
const formattedCheck = computed(() => checkedAt.value?.toLocaleString(locale.value) || '—')
const guides = [
  { title: 'models', description: 'modelsDescription', rows: ['ollama', 'llm', 'embedding'] },
  { title: 'scanners', description: 'scannersDescription', rows: ['nmap', 'nuclei', 'templates'] },
  { title: 'integrations', description: 'integrationsDescription', rows: ['github', 'executionMode', 'externalExecution'] },
]
async function refreshHealth() {
  if (checking.value) return
  checking.value = true
  try {
    const result = await getHealth({ signal: controller.signal, silent: true, timeout: 5000 })
    backendStatus.value = result?.status === 'healthy' ? 'available' : 'unconfirmed'
  } catch {
    if (!controller.signal.aborted) backendStatus.value = 'unreachable'
  } finally {
    if (!controller.signal.aborted) {
      checkedAt.value = new Date()
      checking.value = false
    }
  }
}
onMounted(refreshHealth)
onBeforeUnmount(() => controller.abort())
</script>

<template>
  <section class="settings-page">
    <div class="page-heading">
      <div><h2>{{ t('settings.title') }}</h2><p>{{ t('settingsCenter.description') }}</p></div>
      <el-button :loading="checking" @click="refreshHealth">{{ t('settingsCenter.refresh') }}</el-button>
    </div>

    <section class="panel settings-section">
      <div class="panel-heading"><div><h3>{{ t('settingsCenter.general') }}</h3><p>{{ t('settingsCenter.browserPreferences') }}</p></div></div>
      <div class="setting-row">
        <div><strong>{{ t('settings.language') }}</strong><p>{{ t('settings.languageDescription') }}</p></div>
        <el-select v-model="currentLanguage" class="language-select" :aria-label="t('settings.language')">
          <el-option :label="t('settings.chinese')" value="zh-CN" />
          <el-option :label="t('settings.english')" value="en-US" />
        </el-select>
      </div>
    </section>

    <section class="panel settings-section">
      <div class="panel-heading"><div><h3>{{ t('settingsCenter.system') }}</h3><p>{{ t('settingsCenter.healthScope') }}</p></div><el-tag effect="plain">{{ t('settingsCenter.readOnly') }}</el-tag></div>
      <dl class="system-grid" aria-live="polite">
        <div><dt>{{ t('settingsCenter.backend') }}</dt><dd><el-tag :type="backendStatus === 'available' ? 'success' : backendStatus === 'unreachable' ? 'danger' : 'info'">{{ t(`settingsCenter.${checking ? 'checking' : backendStatus}`) }}</el-tag></dd></div>
        <div><dt>MySQL</dt><dd>{{ t('settingsCenter.notExposed') }}</dd></div>
        <div><dt>Ollama</dt><dd>{{ t('settingsCenter.notExposed') }}</dd></div>
        <div><dt>{{ t('settingsCenter.lastChecked') }}</dt><dd>{{ formattedCheck }}</dd></div>
      </dl>
    </section>

    <div class="settings-grid">
      <section v-for="guide in guides" :key="guide.title" class="panel settings-section">
        <div class="panel-heading"><div><h3>{{ t(`settingsCenter.${guide.title}`) }}</h3><p>{{ t(`settingsCenter.${guide.description}`) }}</p></div><el-tag type="info" effect="plain">{{ t('settingsCenter.configurationGuide') }}</el-tag></div>
        <dl class="configuration-list">
          <div v-for="row in guide.rows" :key="row"><dt>{{ t(`settingsCenter.${row}`) }}</dt><dd>{{ t(`settingsCenter.${row}Help`) }}</dd></div>
        </dl>
      </section>
    </div>
  </section>
</template>

<style scoped>
.settings-section { min-width: 0; }
.settings-section .panel-heading p { margin: 8px 0 0; font-size: 13px; line-height: 1.7; color: var(--sa-text-secondary); }
.setting-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 24px; padding: 0 24px 24px; }
.setting-row > div { min-width: 0; }
.setting-row p { margin: 8px 0 0; color: var(--sa-text-secondary); line-height: 1.7; }
.language-select { width: 240px; max-width: 100%; }
.system-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20px; margin: 0; padding: 0 24px 24px; }
.system-grid > div { padding: 16px; min-width: 0; background: var(--sa-surface-muted); border-radius: 8px; }
dt { color: var(--sa-text); font-weight: 600; font-size: 13px; line-height: 1.6; }
dd { margin: 8px 0 0; color: var(--sa-text-secondary); font-size: 13px; line-height: 1.75; overflow-wrap: anywhere; }
.settings-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.settings-grid > :last-child { grid-column: 1 / -1; }
.configuration-list { margin: 0; padding: 0 24px 24px; display: grid; gap: 20px; }
.configuration-list > div + div { border-top: 1px solid var(--sa-border); padding-top: 20px; }
@media (max-width: 1280px) { .system-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 900px) { .settings-grid { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 640px) { .system-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
