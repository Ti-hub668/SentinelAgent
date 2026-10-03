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
  ElMessage,
} from 'element-plus'

import {
  Plus,
  Refresh,
  Search,
  Monitor,
  Position,
} from '@element-plus/icons-vue'

import {
  createAsset,
  getAssets,
} from '../../api'

const loading = ref(false)
const creating = ref(false)
const createDialogVisible = ref(false)

const assets = ref([])
const keyword = ref('')

const form = reactive({
  name: '',
  target: '',
  asset_type: 'host',
})

const filteredAssets = computed(() => {
  const query = keyword.value
    .trim()
    .toLowerCase()

  if (!query) {
    return assets.value
  }

  return assets.value.filter((asset) => {
    const fields = [
      asset.name,
      asset.target,
      asset.asset_type,
      asset.status,
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
  if (status === 'active') {
    return 'success'
  }

  if (status === 'inactive') {
    return 'info'
  }

  return 'warning'
}

async function loadAssets() {
  loading.value = true

  try {
    const data = await getAssets({
      silent: true,
    })

    assets.value = normalizeList(data)
  } catch (error) {
    console.error(error)

    ElMessage.error(
      t('interface.failedToLoadAssets'),
    )
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  form.name = ''
  form.target = ''
  form.asset_type = 'host'

  createDialogVisible.value = true
}

async function submitAsset() {
  const name = form.name.trim()
  const target = form.target.trim()

  if (!name || !target) {
    ElMessage.warning(
      t('interface.pleaseEnterAnAssetNameAndTargetAddress'),
    )

    return
  }

  creating.value = true

  try {
    await createAsset({
      name,
      target,
      asset_type: form.asset_type,
    })

    ElMessage.success(
      t('interface.assetCreatedSuccessfully'),
    )

    createDialogVisible.value = false

    await loadAssets()
  } catch (error) {
    console.error(error)
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadAssets()
})
</script>

<template>
  <div class="asset-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">
          {{ t('interface.assetManagement') }}
        </div>

        <h2>
          {{ t('interface.assets') }}
        </h2>

        <p>
          {{ t('interface.manageSentinelagentScanTargetsAndAssetStatus') }}
        </p>
      </div>

      <div class="heading-actions">
        <el-button
          :icon="Refresh"
          @click="loadAssets"
        >
          {{ t('interface.refresh') }}
        </el-button>

        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          {{ t('interface.addAsset') }}
        </el-button>
      </div>
    </div>

    <section class="panel summary-grid">
      <div class="summary-card">
        <span>
          {{ t('interface.totalAssets') }}
        </span>

        <strong>
          {{ assets.length }}
        </strong>
      </div>

      <div class="summary-card">
        <span>
          {{ t('interface.active') }}
        </span>

        <strong>
          {{
            assets.filter(
              (item) =>
                item.status === 'active',
            ).length
          }}
        </strong>
      </div>

      <div class="summary-card">
        <span>
          {{ t('interface.host') }}
        </span>

        <strong>
          {{
            assets.filter(
              (item) =>
                item.asset_type === 'host',
            ).length
          }}
        </strong>
      </div>
    </section>

    <section class="panel">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          class="search-input"
          :placeholder="t('interface.searchNameIpTypeOrStatus')"
          clearable
        >
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>

        <span class="muted">
          {{ filteredAssets.length }} {{ t('interface.assets12') }}
        </span>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredAssets"
        :empty-text="t('interface.noAssets')"
      >
        <el-table-column
          prop="id"
          :label="t('interface.id')"
          width="80"
        />

        <el-table-column
          :label="t('interface.asset')"
          min-width="220"
        >
          <template #default="{ row }">
            <div class="asset-cell">
              <div class="asset-icon">
                <el-icon>
                  <Monitor />
                </el-icon>
              </div>

              <div>
                <strong>
                  {{ row.name }}
                </strong>

                <small>
                  {{ row.target }}
                </small>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          prop="asset_type"
          :label="t('interface.type')"
          width="130"
        >
          <template #default="{ row }">
            <el-tag
              effect="plain"
              type="info"
            >
              {{ label(row.asset_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          prop="status"
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
          :label="t('interface.createdAt')"
          min-width="190"
        >
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column
          :label="t('interface.scan')"
          width="120"
          align="right"
        >
          <template #default="{ row }">
            <router-link
              :to="{
                name: 'scans',
                query: {
                  asset_id: row.id,
                },
              }"
              class="scan-link"
            >
              <el-icon>
                <Position />
              </el-icon>

              {{ t('interface.scan') }}
            </router-link>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="createDialogVisible"
      :title="t('interface.addAsset')"
      width="520px"
    >
      <el-form label-position="top">
        <el-form-item :label="t('interface.assetName')">
          <el-input
            v-model="form.name"
            :placeholder="t('interface.eGLocalTestServer')"
          />
        </el-form-item>

        <el-form-item :label="t('interface.targetAddress')">
          <el-input
            v-model="form.target"
            :placeholder="t('interface.eG127001')"
          />
        </el-form-item>

        <el-form-item :label="t('interface.assetType')">
          <el-select
            v-model="form.asset_type"
            style="width: 100%"
          >
            <el-option
              :label="t('interface.host')"
              value="host"
            />

            <el-option
              :label="t('interface.domain')"
              value="domain"
            />

            <el-option
              :label="t('interface.url')"
              value="url"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button
          @click="
            createDialogVisible = false
          "
        >
          {{ t('interface.cancel') }}
        </el-button>

        <el-button
          type="primary"
          :loading="creating"
          @click="submitAsset"
        >
          {{ t('interface.createAsset') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.asset-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.search-input {
  max-width: 360px;
}

.asset-cell {
  display: flex;
  align-items: center;
  gap: 12px;
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

.asset-icon {
  display: flex;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: #299dbc;
  background: #eef8fb;
}

.scan-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #299dbc;
  text-decoration: none;
}

.muted {
  color: #94a3b8;
  font-size: 12px;
}

@media (max-width: 900px) {
  .page-heading {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>