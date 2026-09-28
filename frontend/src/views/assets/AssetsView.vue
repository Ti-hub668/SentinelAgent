<script setup>
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

  return date.toLocaleString()
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
      '资产列表加载失败',
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
      '请填写资产名称和目标地址',
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
      '资产创建成功',
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
          ASSET MANAGEMENT
        </div>

        <h2>
          Assets
        </h2>

        <p>
          管理 SentinelAgent 扫描目标与资产状态
        </p>
      </div>

      <div class="heading-actions">
        <el-button
          :icon="Refresh"
          @click="loadAssets"
        >
          刷新
        </el-button>

        <el-button
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          添加资产
        </el-button>
      </div>
    </div>

    <section class="panel summary-grid">
      <div class="summary-card">
        <span>
          总资产
        </span>

        <strong>
          {{ assets.length }}
        </strong>
      </div>

      <div class="summary-card">
        <span>
          Active
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
          Host
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
          placeholder="搜索名称、IP、类型或状态"
          clearable
        >
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>

        <span class="muted">
          {{ filteredAssets.length }} 个资产
        </span>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredAssets"
        empty-text="暂无资产"
      >
        <el-table-column
          prop="id"
          label="ID"
          width="80"
        />

        <el-table-column
          label="资产"
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
          label="类型"
          width="130"
        >
          <template #default="{ row }">
            <el-tag
              effect="plain"
              type="info"
            >
              {{ row.asset_type }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          prop="status"
          label="状态"
          width="130"
        >
          <template #default="{ row }">
            <el-tag
              :type="statusType(row.status)"
              effect="light"
            >
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="创建时间"
          min-width="190"
        >
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column
          label="扫描"
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

              扫描
            </router-link>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="createDialogVisible"
      title="添加资产"
      width="520px"
    >
      <el-form label-position="top">
        <el-form-item label="资产名称">
          <el-input
            v-model="form.name"
            placeholder="例如 Local Test Server"
          />
        </el-form-item>

        <el-form-item label="目标地址">
          <el-input
            v-model="form.target"
            placeholder="例如 127.0.0.1"
          />
        </el-form-item>

        <el-form-item label="资产类型">
          <el-select
            v-model="form.asset_type"
            style="width: 100%"
          >
            <el-option
              label="Host"
              value="host"
            />

            <el-option
              label="Domain"
              value="domain"
            />

            <el-option
              label="URL"
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
          取消
        </el-button>

        <el-button
          type="primary"
          :loading="creating"
          @click="submitAsset"
        >
          创建资产
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

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.page-heading h2 {
  margin: 4px 0 6px;
  color: #1f2937;
  font-size: 26px;
}

.page-heading p {
  margin: 0;
  color: #8a95a8;
}

.eyebrow {
  color: #299dbc;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.4px;
}

.heading-actions {
  display: flex;
  gap: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  padding: 18px;
  border-radius: 12px;
  background: #f8fafc;
}

.summary-card span {
  display: block;
  color: #8a95a8;
  font-size: 12px;
}

.summary-card strong {
  display: block;
  margin-top: 8px;
  color: #26364a;
  font-size: 26px;
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