<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { getDiscovery } from '../../api'
import { useDisplayLabels } from '../../i18n/display'

const { t, locale } = useI18n()
const { label } = useDisplayLabels()
const inventory = ref([])
const loading = ref(false)
const search = ref('')
const webOnly = ref(false)
const controller = new AbortController()
const columns = [
  ['asset_id', 'assetId', 100], ['scan_task_id', 'scanTask', 110],
  ['host', 'host', 160], ['port', 'port', 85], ['protocol', 'protocol', 100],
  ['service', 'service', 120], ['product', 'product', 170], ['version', 'version', 130],
]
const stats = computed(() => [
  ['services', inventory.value.filter(row => row.service?.trim()).length],
  ['ports', inventory.value.length],
  ['targets', new Set(inventory.value.map(row => row.web_target).filter(Boolean)).size],
  ['assets', new Set(inventory.value.map(row => row.asset_id)).size],
])
const visibleInventory = computed(() => {
  const query = search.value.trim().toLowerCase()
  return inventory.value.filter(row => (!webOnly.value || row.web_target) &&
    (!query || ['host', 'port', 'service', 'product', 'version', 'web_target']
      .some(key => String(row[key] ?? '').toLowerCase().includes(query))))
})
function webLink(value) {
  if (!value) return null
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null
  } catch { return null }
}
function date(value) {
  if (!value) return '—'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString(locale.value)
}
async function refresh() {
  if (loading.value) return
  loading.value = true
  try {
    const data = await getDiscovery({ signal: controller.signal, silent: true })
    inventory.value = data
  } catch (error) {
    if (!controller.signal.aborted) ElMessage.error(t('discovery.loadFailed'))
  } finally { loading.value = false }
}
onMounted(refresh)
onBeforeUnmount(() => controller.abort())
</script>

<template>
  <section class="discovery-page">
    <div class="page-heading">
      <div><h2>{{ t('discovery.title') }}</h2><p>{{ t('discovery.description') }}</p></div>
      <el-button :loading="loading" @click="refresh">{{ t('discovery.refresh') }}</el-button>
    </div>
    <div class="summary-grid">
      <article v-for="[key, value] in stats" :key="key" class="summary-card">
        <span>{{ t(`discovery.${key}`) }}</span><strong>{{ value }}</strong>
      </article>
    </div>
    <section class="panel inventory-panel" v-loading="loading">
      <div class="panel-heading"><h3>{{ t('discovery.inventory') }}</h3></div>
      <div class="inventory-toolbar">
        <el-input v-model="search" clearable :placeholder="t('discovery.search')" :aria-label="t('discovery.search')" />
        <el-checkbox v-model="webOnly">{{ t('discovery.webOnly') }}</el-checkbox>
      </div>
      <el-table :data="visibleInventory" row-key="port_id" :empty-text="t(inventory.length ? 'discovery.noMatch' : 'discovery.empty')">
        <el-table-column v-for="[field, key, width] in columns" :key="field" :prop="field" :label="t(`discovery.${key}`)" :min-width="width">
          <template #default="{ row }">{{ row[field] === '' || row[field] == null ? '—' : row[field] }}</template>
        </el-table-column>
        <el-table-column :label="t('discovery.webTarget')" min-width="240">
          <template #default="{ row }">
            <a v-if="webLink(row.web_target)" :href="webLink(row.web_target)" target="_blank" rel="noopener noreferrer">{{ row.web_target }}</a>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('discovery.scanStatus')" min-width="150">
          <template #default="{ row }"><el-tag>{{ label(row.scan_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column :label="t('discovery.discoveredAt')" min-width="210">
          <template #default="{ row }">{{ date(row.discovered_at) }}</template>
        </el-table-column>
      </el-table>
      <div class="inventory-footer">
        <span>{{ t('discovery.count', { visible: visibleInventory.length, total: inventory.length }) }}</span>
        <span>{{ t('discovery.statistics') }}</span>
      </div>
    </section>
  </section>
</template>

<style scoped>
.discovery-page { display: grid; gap: 20px; min-width: 0; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }
.inventory-panel { min-width: 0; }
.inventory-toolbar { display: flex; gap: 18px; flex-wrap: wrap; align-items: center; padding: 0 20px 20px; }
.inventory-toolbar .el-input { flex: 1 1 350px; min-width: 0; }
.inventory-toolbar .el-checkbox { margin-right: 0; height: auto; white-space: normal; }
.inventory-panel :deep(.el-table .cell) { overflow-wrap: anywhere; word-break: break-word; }
.inventory-panel :deep(.el-table__empty-block) { width: 100% !important; min-width: 0; }
.inventory-panel :deep(.el-table__empty-text) { max-width: 100%; padding: 24px; line-height: 1.7; }
.inventory-panel a { color: var(--el-color-primary); overflow-wrap: anywhere; }
.inventory-footer { display: flex; flex-wrap: wrap; gap: 12px 24px; padding: 20px; color: var(--text-secondary); font-size: 13px; }
.inventory-footer span { min-width: 0; overflow-wrap: anywhere; }
@media (max-width: 1280px) { .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .summary-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
