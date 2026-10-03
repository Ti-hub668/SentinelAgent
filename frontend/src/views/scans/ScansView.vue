<script setup>
import { useI18n } from 'vue-i18n'
import { useDisplayLabels } from '../../i18n/display'
const { t, locale } = useI18n()
const { label } = useDisplayLabels()

import {
  computed,
  onMounted,
  reactive,
  ref,
} from 'vue'

import {
  useRoute,
  useRouter,
} from 'vue-router'

import {
  ElMessage,
} from 'element-plus'

import {
  Refresh,
  Search,
  Position,
  View,
} from '@element-plus/icons-vue'

import {
  createScan,
  getAssets,
  getScan,
  getScans,
} from '../../api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const creating = ref(false)

const scans = ref([])
const assets = ref([])

const keyword = ref('')
const statusFilter = ref('')

const detailVisible = ref(false)
const selectedScan = ref(null)
const detailLoading = ref(false)

const form = reactive({
  asset_id: '',
  scan_profile: 'fast',
})

const assetMap = computed(() => {
  const map = new Map()

  for (const asset of assets.value) {
    map.set(
      Number(asset.id),
      asset,
    )
  }

  return map
})

const filteredScans = computed(() => {
  const query = keyword.value
    .trim()
    .toLowerCase()

  return scans.value.filter((scan) => {
    if (
      statusFilter.value &&
      scan.status !== statusFilter.value
    ) {
      return false
    }

    if (!query) {
      return true
    }

    const asset =
      assetMap.value.get(
        Number(scan.asset_id),
      )

    const fields = [
      scan.id,
      scan.asset_id,
      scan.scanner,
      scan.status,
      asset?.name,
      asset?.target,
    ]

    return fields.some((value) =>
      String(value || '')
        .toLowerCase()
        .includes(query),
    )
  })
})

function normalizeList(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.items)) {
    return data.items
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function formatDate(value) {
  if (!value) {
    return '—'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleString(locale.value)
}

function statusType(status) {
  if (status === 'completed') {
    return 'success'
  }

  if (status === 'running') {
    return 'warning'
  }

  if (status === 'failed') {
    return 'danger'
  }

  return 'info'
}

function assetName(assetId) {
  const asset =
    assetMap.value.get(
      Number(assetId),
    )

  if (!asset) {
    return t('interface.assetValue', { p0: assetId })
  }

  return asset.name
}

function assetTarget(assetId) {
  const asset =
    assetMap.value.get(
      Number(assetId),
    )

  return asset?.target || '—'
}

async function loadPage() {
  loading.value = true

  try {
    const [
      scansData,
      assetsData,
    ] = await Promise.all([
      getScans({
        silent: true,
      }),

      getAssets({
        silent: true,
      }),
    ])

    scans.value =
      normalizeList(scansData)

    assets.value =
      normalizeList(assetsData)

    const queryAssetId =
      route.query.asset_id

    if (
      queryAssetId &&
      assets.value.some(
        (item) =>
          String(item.id) ===
          String(queryAssetId),
      )
    ) {
      form.asset_id =
        Number(queryAssetId)
    }

    const target =
      String(
        route.query.target || '',
      ).trim()

    if (target) {
      const matchingAsset =
        assets.value.find(
          (asset) =>
            asset.target === target,
        )

      if (matchingAsset) {
        form.asset_id =
          matchingAsset.id
      }
    }
  } catch (error) {
    console.error(error)

    ElMessage.error(
      t('interface.failedToLoadScanData'),
    )
  } finally {
    loading.value = false
  }
}

async function submitScan() {
  if (!form.asset_id) {
    ElMessage.warning(
      t('interface.pleaseSelectAnAssetToScan'),
    )

    return
  }

  creating.value = true

  try {
    const result = await createScan(
      {
        asset_id:
          Number(form.asset_id),

        scan_profile:
          form.scan_profile,
      },
      {
        timeout: 600000,
      },
    )

    ElMessage.success(
      t('interface.scanTaskValueCompleted', { p0: result.id }),
    )

    await loadPage()

    await router.replace({
      name: 'scans',
    })
  } catch (error) {
    console.error(error)
  } finally {
    creating.value = false
  }
}

async function openDetail(scanId) {
  detailVisible.value = true
  detailLoading.value = true
  selectedScan.value = null

  try {
    selectedScan.value =
      await getScan(
        scanId,
        {
          silent: true,
        },
      )
  } catch (error) {
    console.error(error)

    ElMessage.error(
      t('interface.failedToLoadScanDetails'),
    )
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => {
  loadPage()
})
</script>

<template>
  <div class="scan-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">
          {{ t('interface.securityScanning') }}
        </div>

        <h2>
          {{ t('interface.scanTasks') }}
        </h2>

        <p>
          {{ t('interface.nmapAssetDiscoveryAndNucleiWebSecurityScanning') }}
        </p>
      </div>

      <el-button
        :icon="Refresh"
        @click="loadPage"
      >
        {{ t('interface.refresh') }}
      </el-button>
    </div>

    <section class="panel scan-launcher">
      <div class="launcher-heading">
        <div>
          <h3>
            {{ t('interface.launchScanTask') }}
          </h3>

          <p>
            {{ t('interface.selectARegisteredAssetAndScanProfile') }}
          </p>
        </div>

        <el-tag
          effect="plain"
          type="info"
        >
          {{ t('interface.nmapNuclei') }}
        </el-tag>
      </div>

      <el-form
        class="scan-form"
        label-position="top"
      >
        <el-form-item :label="t('interface.scanAsset')">
          <el-select
            v-model="form.asset_id"
            :placeholder="t('interface.selectAsset')"
            filterable
          >
            <el-option
              v-for="asset in assets"
              :key="asset.id"
              :label="
                `${asset.name} · ${asset.target}`
              "
              :value="asset.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('interface.scanProfile')">
          <el-select
            v-model="form.scan_profile"
          >
            <el-option
              :label="t('interface.fast')"
              value="fast"
            />

            <el-option
              :label="t('interface.security')"
              value="security"
            />

            <el-option
              :label="t('interface.full')"
              value="full"
            />
          </el-select>
        </el-form-item>

        <el-form-item class="submit-field">
          <el-button
            type="primary"
            :icon="Position"
            :loading="creating"
            @click="submitScan"
          >
            {{
              creating
                ? t('interface.scanning')
                : t('interface.startScan')
            }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="route.query.target"
        type="info"
        :closable="false"
        show-icon
      >
        <template #title>
          {{ t('interface.targetFromDashboard') }}
        </template>

        {{
          route.query.target
        }}
      </el-alert>
    </section>

    <section class="panel">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          class="search-input"
          :placeholder="t('interface.searchScanIdAssetOrScanner')"
          clearable
        >
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>

        <el-select
          v-model="statusFilter"
          class="status-filter"
          :placeholder="t('interface.allStatuses')"
          clearable
        >
          <el-option
            :label="t('interface.completed')"
            value="completed"
          />

          <el-option
            :label="t('interface.running')"
            value="running"
          />

          <el-option
            :label="t('interface.failed')"
            value="failed"
          />
        </el-select>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredScans"
        :empty-text="t('interface.noScanTasks')"
      >
        <el-table-column
          prop="id"
          :label="t('interface.scanId')"
          width="100"
        />

        <el-table-column
          :label="t('interface.asset')"
          min-width="220"
        >
          <template #default="{ row }">
            <div class="asset-cell">
              <strong>
                {{ assetName(row.asset_id) }}
              </strong>

              <small>
                {{ assetTarget(row.asset_id) }}
              </small>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          prop="scanner"
          :label="t('interface.scanner')"
          width="160"
        />

        <el-table-column
          :label="t('interface.status')"
          width="130"
        >
          <template #default="{ row }">
            <el-tag
              :type="statusType(row.status)"
              effect="light"
            >
              {{ label(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          :label="t('interface.openPorts')"
          width="120"
        >
          <template #default="{ row }">
            {{ row.ports?.length ?? 0 }}
          </template>
        </el-table-column>

        <el-table-column
          :label="t('interface.startedAt')"
          min-width="190"
        >
          <template #default="{ row }">
            {{
              formatDate(
                row.started_at,
              )
            }}
          </template>
        </el-table-column>

        <el-table-column
          :label="t('interface.finishedAt')"
          min-width="190"
        >
          <template #default="{ row }">
            {{
              formatDate(
                row.finished_at,
              )
            }}
          </template>
        </el-table-column>

        <el-table-column
          :label="t('interface.actions')"
          width="110"
          align="right"
        >
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              :icon="View"
              @click="openDetail(row.id)"
            >
              {{ t('interface.details') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-drawer
      v-model="detailVisible"
      :title="t('interface.scanDetail')"
      size="520px"
    >
      <div
        v-loading="detailLoading"
        class="scan-detail"
      >
        <template v-if="selectedScan">
          <div class="detail-title">
            <div>
              <span>
                {{ t('interface.scan63') }}
              </span>

              <h3>
                #{{ selectedScan.id }}
              </h3>
            </div>

            <el-tag
              :type="
                statusType(
                  selectedScan.status,
                )
              "
            >
              {{ label(selectedScan.status) }}
            </el-tag>
          </div>

          <dl class="detail-grid">
            <div>
              <dt>
                {{ t('interface.asset64') }}
              </dt>

              <dd>
                {{
                  assetName(
                    selectedScan.asset_id,
                  )
                }}
              </dd>
            </div>

            <div>
              <dt>
                {{ t('interface.scanner') }}
              </dt>

              <dd>
                {{ selectedScan.scanner }}
              </dd>
            </div>

            <div>
              <dt>
                {{ t('interface.started') }}
              </dt>

              <dd>
                {{
                  formatDate(
                    selectedScan.started_at,
                  )
                }}
              </dd>
            </div>

            <div>
              <dt>
                {{ t('interface.finished') }}
              </dt>

              <dd>
                {{
                  formatDate(
                    selectedScan.finished_at,
                  )
                }}
              </dd>
            </div>
          </dl>

          <div class="ports-heading">
            <h4>
              {{ t('interface.openPorts67') }}
            </h4>

            <span>
              {{
                selectedScan.ports?.length ||
                0
              }}
            </span>
          </div>

          <el-table
            :data="selectedScan.ports || []"
            size="small"
          >
            <el-table-column
              prop="port"
              :label="t('interface.port')"
              width="80"
            />

            <el-table-column
              prop="protocol"
              :label="t('interface.protocol')"
              width="90"
            />

            <el-table-column
              prop="service"
              :label="t('interface.service')"
            />

            <el-table-column
              prop="product"
              :label="t('interface.product')"
            />

            <el-table-column
              prop="version"
              :label="t('interface.version')"
            />
          </el-table>

          <el-alert
            v-if="selectedScan.error_message"
            type="error"
            :closable="false"
            class="error-alert"
          >
            {{
              selectedScan.error_message
            }}
          </el-alert>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.scan-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.scan-launcher {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.launcher-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.launcher-heading h3 {
  margin: 0;
  color: #334155;
}

.launcher-heading p {
  margin: 5px 0 0;
  color: #94a3b8;
  font-size: 12px;
}

.scan-form {
  display: grid;
  grid-template-columns:
    minmax(0, 1.6fr)
    minmax(180px, 0.8fr)
    auto;
  align-items: end;
  gap: 14px;
}

.scan-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.scan-form :deep(.el-select) {
  width: 100%;
}

.submit-field {
  min-width: 140px;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  max-width: 360px;
}

.status-filter {
  width: 170px;
}

.asset-cell strong {
  display: block;
  color: #334155;
}

.asset-cell small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
}

.scan-detail {
  min-height: 300px;
}

.detail-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 22px;
}

.detail-title span {
  color: #94a3b8;
  font-size: 12px;
}

.detail-title h3 {
  margin: 3px 0 0;
  color: #334155;
  font-size: 26px;
}

.detail-grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.detail-grid div {
  padding: 14px;
  border: 1px solid #edf0f4;
  border-radius: 10px;
  background: #fafbfc;
}

.detail-grid dt {
  color: #94a3b8;
  font-size: 11px;
}

.detail-grid dd {
  margin: 6px 0 0;
  color: #334155;
  font-size: 13px;
  word-break: break-all;
}

.ports-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 8px 0 12px;
}

.ports-heading h4 {
  margin: 0;
  color: #334155;
}

.ports-heading span {
  color: #94a3b8;
  font-size: 12px;
}

.error-alert {
  margin-top: 18px;
}

@media (max-width: 1000px) {
  .scan-form {
    grid-template-columns: 1fr;
  }
}
</style>