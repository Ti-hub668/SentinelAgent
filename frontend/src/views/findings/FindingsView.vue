<script setup>
import { useI18n } from 'vue-i18n'
import { useDisplayLabels } from '../../i18n/display'
const { t, locale } = useI18n()
const { label } = useDisplayLabels()

import {
  computed,
  onMounted,
  ref,
  watch,
} from 'vue'

import {
  useRouter,
} from 'vue-router'

import {
  ElMessage,
} from 'element-plus'

import {
  Cpu,
  Refresh,
  Search,
  View,
  WarningFilled,
  Document,
  Aim,
  Clock,
} from '@element-plus/icons-vue'

import {
  getFinding,
  getFindings,
} from '../../api'

const router = useRouter()

const loading = ref(false)
const detailLoading = ref(false)

const findings = ref([])

const selectedFinding = ref(null)
const selectedFindingId = ref(null)

const keyword = ref('')
const severityFilter = ref('')
const riskFilter = ref('')
const statusFilter = ref('')
const sourceFilter = ref('')

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

const sourceOptions = computed(() => {
  const values = new Set()

  for (const finding of findings.value) {
    if (finding.source) {
      values.add(finding.source)
    }
  }

  return [...values].sort()
})

const statusOptions = computed(() => {
  const values = new Set()

  for (const finding of findings.value) {
    if (finding.status) {
      values.add(finding.status)
    }
  }

  return [...values].sort()
})

const filteredFindings = computed(() => {
  const query = keyword.value
    .trim()
    .toLowerCase()

  return findings.value.filter((finding) => {
    if (
      severityFilter.value &&
      String(finding.severity || '').toLowerCase() !==
        severityFilter.value
    ) {
      return false
    }

    if (
      riskFilter.value &&
      String(finding.risk_level || '').toLowerCase() !==
        riskFilter.value
    ) {
      return false
    }

    if (
      statusFilter.value &&
      finding.status !== statusFilter.value
    ) {
      return false
    }

    if (
      sourceFilter.value &&
      finding.source !== sourceFilter.value
    ) {
      return false
    }

    if (!query) {
      return true
    }

    const fields = [
      finding.id,
      finding.title,
      finding.target,
      finding.source,
      finding.finding_type,
      finding.description,
      finding.severity,
      finding.risk_level,
      finding.status,
    ]

    return fields.some((value) =>
      String(value || '')
        .toLowerCase()
        .includes(query),
    )
  })
})

const findingStats = computed(() => {
  const result = {
    total: findings.value.length,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
    open: 0,
  }

  for (const finding of findings.value) {
    const riskLevel = String(
      finding.risk_level ||
        finding.severity ||
        '',
    ).toLowerCase()

    if (riskLevel in result) {
      result[riskLevel] += 1
    }

    if (finding.status === 'open') {
      result.open += 1
    }
  }

  return result
})

function severityTagType(level) {
  const normalized = String(
    level || '',
  ).toLowerCase()

  if (
    normalized === 'critical' ||
    normalized === 'high'
  ) {
    return 'danger'
  }

  if (normalized === 'medium') {
    return 'warning'
  }

  if (normalized === 'low') {
    return 'primary'
  }

  return 'info'
}

function riskClass(level) {
  return `risk-${String(
    level || 'unknown',
  ).toLowerCase()}`
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

function normalizeRiskScore(score) {
  const number = Number(score)

  if (Number.isNaN(number)) {
    return 0
  }

  return Math.min(
    Math.max(number, 0),
    100,
  )
}

function riskProgressStatus(level) {
  const normalized = String(
    level || '',
  ).toLowerCase()

  if (
    normalized === 'critical' ||
    normalized === 'high'
  ) {
    return 'exception'
  }

  if (normalized === 'medium') {
    return 'warning'
  }

  if (normalized === 'low') {
    return 'success'
  }

  return ''
}

async function loadFindings() {
  loading.value = true

  try {
    const data = await getFindings({
      silent: true,
    })

    findings.value =
      normalizeList(data)

    if (
      findings.value.length > 0 &&
      !selectedFinding.value
    ) {
      await selectFinding(
        findings.value[0].id,
      )
    }
  } catch (error) {
    console.error(error)

    ElMessage.error(
      t('interface.failedToLoadFindings'),
    )
  } finally {
    loading.value = false
  }
}

async function selectFinding(findingId) {
  if (!findingId) {
    return
  }

  selectedFindingId.value =
    Number(findingId)

  detailLoading.value = true

  try {
    selectedFinding.value =
      await getFinding(
        findingId,
        {
          silent: true,
        },
      )
  } catch (error) {
    console.error(error)

    const fallback =
      findings.value.find(
        (item) =>
          Number(item.id) ===
          Number(findingId),
      )

    if (fallback) {
      selectedFinding.value = fallback
    } else {
      ElMessage.error(
        t('interface.failedToLoadFindingDetails'),
      )
    }
  } finally {
    detailLoading.value = false
  }
}

function resetFilters() {
  keyword.value = ''
  severityFilter.value = ''
  riskFilter.value = ''
  statusFilter.value = ''
  sourceFilter.value = ''
}

function startInvestigation() {
  if (!selectedFinding.value) {
    return
  }

  router.push({
    name: 'investigations',

    query: {
      finding_id:
        selectedFinding.value.id,
    },
  })
}

watch(
  filteredFindings,
  (items) => {
    if (items.length === 0) {
      return
    }

    const currentStillVisible =
      items.some(
        (item) =>
          Number(item.id) ===
          Number(
            selectedFindingId.value,
          ),
      )

    if (!currentStillVisible) {
      selectFinding(items[0].id)
    }
  },
)

onMounted(() => {
  loadFindings()
})
</script>

<template>
  <div class="findings-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">
          {{ t('interface.securityOperations') }}
        </div>

        <h2>
          {{ t('interface.securityFindings') }}
        </h2>

        <p>
          {{ t('interface.scanFindingsRiskAssessmentsAndEvidenceContext') }}
        </p>
      </div>

      <el-button
        :icon="Refresh"
        :loading="loading"
        @click="loadFindings"
      >
        {{ t('interface.refresh') }}
      </el-button>
    </div>

    <div class="summary-grid">
      <section class="panel summary-card">
        <span>
          {{ t('interface.totalFindings') }}
        </span>

        <strong>
          {{ findingStats.total }}
        </strong>

        <small>
          {{ t('interface.allSecurityFindings') }}
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          {{ t('interface.open') }}
        </span>

        <strong>
          {{ findingStats.open }}
        </strong>

        <small>
          {{ t('interface.awaitingReview') }}
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          {{ t('interface.highCritical') }}
        </span>

        <strong>
          {{
            findingStats.high +
            findingStats.critical
          }}
        </strong>

        <small>
          {{ t('interface.highRiskFindings') }}
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          {{ t('interface.lowInfo') }}
        </span>

        <strong>
          {{
            findingStats.low +
            findingStats.info
          }}
        </strong>

        <small>
          {{ t('interface.lowRiskAndInformationalFindings') }}
        </small>
      </section>
    </div>

    <section class="panel filter-panel">
      <div class="filter-main">
        <el-input
          v-model="keyword"
          class="search-input"
          :placeholder="t('interface.searchTitleTargetSourceOrFindingId')"
          clearable
        >
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>

        <el-select
          v-model="severityFilter"
          class="filter-select"
          :placeholder="t('interface.severity')"
          clearable
        >
          <el-option
            :label="t('interface.critical')"
            value="critical"
          />

          <el-option
            :label="t('interface.high')"
            value="high"
          />

          <el-option
            :label="t('interface.medium')"
            value="medium"
          />

          <el-option
            :label="t('interface.low')"
            value="low"
          />

          <el-option
            :label="t('interface.info')"
            value="info"
          />
        </el-select>

        <el-select
          v-model="riskFilter"
          class="filter-select"
          :placeholder="t('interface.riskLevel')"
          clearable
        >
          <el-option
            :label="t('interface.critical')"
            value="critical"
          />

          <el-option
            :label="t('interface.high')"
            value="high"
          />

          <el-option
            :label="t('interface.medium')"
            value="medium"
          />

          <el-option
            :label="t('interface.low')"
            value="low"
          />

          <el-option
            :label="t('interface.info')"
            value="info"
          />
        </el-select>

        <el-select
          v-model="statusFilter"
          class="filter-select"
          :placeholder="t('interface.status94')"
          clearable
        >
          <el-option
            v-for="status in statusOptions"
            :key="status"
            :label="label(status)"
            :value="status"
          />
        </el-select>

        <el-select
          v-model="sourceFilter"
          class="filter-select"
          :placeholder="t('interface.source')"
          clearable
        >
          <el-option
            v-for="source in sourceOptions"
            :key="source"
            :label="source"
            :value="source"
          />
        </el-select>

        <el-button
          text
          @click="resetFilters"
        >
          {{ t('interface.reset') }}
        </el-button>
      </div>

      <span class="result-count">
        {{ filteredFindings.length }}
        /
        {{ findings.length }}
      </span>
    </section>

    <div class="workspace-grid">
      <section class="panel findings-list-panel">
        <div class="section-heading">
          <div>
            <h3>
              {{ t('interface.findingsQueue') }}
            </h3>

            <p>
              {{ t('interface.selectAFindingToViewItsFullEvidence') }}
            </p>
          </div>
        </div>

        <div
          v-loading="loading"
          class="findings-list"
        >
          <el-empty
            v-if="
              !loading &&
              filteredFindings.length === 0
            "
            :description="t('interface.noMatchingFindings')"
          />

          <button
            v-for="finding in filteredFindings"
            :key="finding.id"
            type="button"
            class="finding-item"
            :class="{
              active:
                Number(
                  selectedFindingId,
                ) ===
                Number(finding.id),
            }"
            @click="
              selectFinding(
                finding.id,
              )
            "
          >
            <div class="finding-topline">
              <span class="finding-id">
                #{{ finding.id }}
              </span>

              <el-tag
                size="small"
                effect="light"
                :type="
                  severityTagType(
                    finding.severity,
                  )
                "
              >
                {{ label(finding.severity ||
                  'unknown') }}
              </el-tag>
            </div>

            <strong class="finding-title">
              {{ finding.title }}
            </strong>

            <div class="finding-meta">
              <span>
                <el-icon>
                  <Aim />
                </el-icon>

                {{ finding.target }}
              </span>

              <span>
                {{ finding.source }}
              </span>
            </div>

            <div class="finding-footer">
              <span
                class="risk-badge"
                :class="
                  riskClass(
                    finding.risk_level,
                  )
                "
              >
                {{ label(finding.risk_level ||
                  'unknown') }}
              </span>

              <span class="status-text">
                {{ label(finding.status) }}
              </span>

              <span class="time-text">
                {{
                  formatDate(
                    finding.created_at,
                  )
                }}
              </span>
            </div>
          </button>
        </div>
      </section>

      <section
        class="panel finding-detail-panel"
      >
        <div
          v-loading="detailLoading"
          class="detail-container"
        >
          <el-empty
            v-if="
              !detailLoading &&
              !selectedFinding
            "
            :description="t('interface.selectAFindingToViewDetails')"
          />

          <template v-if="selectedFinding">
            <div class="detail-header">
              <div class="detail-header-main">
                <div class="detail-id">
                  {{ t('interface.finding') }}{{ selectedFinding.id }}
                </div>

                <h3>
                  {{ selectedFinding.title }}
                </h3>

                <div class="detail-tags">
                  <el-tag
                    :type="
                      severityTagType(
                        selectedFinding.severity,
                      )
                    "
                  >
                    {{ t('interface.severity102') }}
                    {{ label(selectedFinding.severity) }}
                  </el-tag>

                  <span
                    class="risk-badge detail-risk"
                    :class="
                      riskClass(
                        selectedFinding.risk_level,
                      )
                    "
                  >
                    {{ t('interface.risk') }}
                    {{ label(selectedFinding.risk_level ||
                      'unknown') }}
                  </span>

                  <el-tag
                    type="info"
                    effect="plain"
                  >
                    {{
                      selectedFinding.source
                    }}
                  </el-tag>
                </div>
              </div>

              <el-button
                type="primary"
                :icon="Cpu"
                @click="startInvestigation"
              >
                {{ t('interface.startAiInvestigation') }}
              </el-button>
            </div>

            <div class="detail-section">
              <div class="section-title">
                <View />

                {{ t('interface.findingOverview') }}
              </div>

              <div class="metadata-grid">
                <div>
                  <span>
                    {{ t('interface.findingId') }}
                  </span>

                  <strong>
                    #{{ selectedFinding.id }}
                  </strong>
                </div>

                <div>
                  <span>
                    {{ t('interface.assetId') }}
                  </span>

                  <strong>
                    #{{ selectedFinding.asset_id }}
                  </strong>
                </div>

                <div>
                  <span>
                    {{ t('interface.scanTask') }}
                  </span>

                  <strong>
                    #{{ selectedFinding.scan_task_id }}
                  </strong>
                </div>

                <div>
                  <span>
                    {{ t('interface.findingType') }}
                  </span>

                  <strong>
                    {{
                      selectedFinding.finding_type
                    }}
                  </strong>
                </div>

                <div>
                  <span>
                    {{ t('interface.target') }}
                  </span>

                  <strong>
                    {{
                      selectedFinding.target
                    }}
                  </strong>
                </div>

                <div>
                  <span>
                    {{ t('interface.status94') }}
                  </span>

                  <strong>
                    {{ label(selectedFinding.status) }}
                  </strong>
                </div>

                <div>
                  <span>
                    {{ t('interface.source') }}
                  </span>

                  <strong>
                    {{
                      selectedFinding.source
                    }}
                  </strong>
                </div>

                <div>
                  <span>
                    {{ t('interface.created') }}
                  </span>

                  <strong>
                    {{
                      formatDate(
                        selectedFinding.created_at,
                      )
                    }}
                  </strong>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <div class="section-title">
                <WarningFilled />

                {{ t('interface.deterministicRisk') }}
              </div>

              <div class="risk-score-box">
                <div class="risk-score-value">
                  <span>
                    {{ t('interface.riskScore') }}
                  </span>

                  <strong>
                    {{
                      selectedFinding.risk_score ??
                      '—'
                    }}
                  </strong>

                  <small>
                    / 100
                  </small>
                </div>

                <div class="risk-progress">
                  <div class="risk-progress-heading">
                    <span>
                      {{ t('interface.riskLevel') }}
                    </span>

                    <strong>
                      {{ label(selectedFinding.risk_level ||
                        'unknown') }}
                    </strong>
                  </div>

                  <el-progress
                    :percentage="
                      normalizeRiskScore(
                        selectedFinding.risk_score,
                      )
                    "
                    :stroke-width="8"
                    :show-text="false"
                    :status="
                      riskProgressStatus(
                        selectedFinding.risk_level,
                      )
                    "
                  />
                </div>
              </div>

              <div
                v-if="
                  selectedFinding.risk_reason
                "
                class="risk-reason"
              >
                {{
                  selectedFinding.risk_reason
                }}
              </div>
            </div>

            <div class="detail-section">
              <div class="section-title">
                <Document />

                {{ t('interface.description') }}
              </div>

              <div class="text-block">
                {{
                  selectedFinding.description ||
                  t('interface.noDescription')
                }}
              </div>
            </div>

            <div class="detail-section">
              <div class="section-title">
                <Clock />

                {{ t('interface.evidence') }}
              </div>

              <pre class="evidence-block">{{
                selectedFinding.evidence ||
                t('interface.noEvidence')
              }}</pre>
            </div>

            <div class="detail-section">
              <div class="section-title">
                <Document />

                {{ t('interface.remediation') }}
              </div>

              <div class="text-block">
                {{
                  selectedFinding.remediation ||
                  t('interface.noRemediationRecommendationsYetAiInvestigationAndResponseAgentWillProvideThemLater')
                }}
              </div>
            </div>

            <div class="investigation-callout">
              <div>
                <span class="callout-label">
                  {{ t('interface.sentinelAgent') }}
                </span>

                <h4>
                  {{ t('interface.aiInvestigation') }}
                </h4>

                <p>
                  {{ t('interface.sendFindingAssetAndScanContextRagKnowledgeAndThreatIntelligenceToLanggraphInvestigatorForEvidenceBackedRiskConclusions') }}
                </p>
              </div>

              <el-button
                type="primary"
                :icon="Cpu"
                @click="startInvestigation"
              >
                {{ t('interface.investigateThisFinding') }}
              </el-button>
            </div>
          </template>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.findings-page {
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

.summary-grid {
  display: grid;
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  padding: 18px;
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

.summary-card small {
  display: block;
  margin-top: 5px;
  color: #a0a9b8;
}

.filter-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.filter-main {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.search-input {
  width: 310px;
}

.filter-select {
  width: 145px;
}

.result-count {
  flex-shrink: 0;
  color: #94a3b8;
  font-size: 12px;
}

.workspace-grid {
  display: grid;
  grid-template-columns:
    minmax(330px, 0.8fr)
    minmax(0, 1.7fr);
  gap: 18px;
  align-items: start;
}

.findings-list-panel {
  padding: 0;
  overflow: hidden;
}

.section-heading {
  padding: 18px 18px 14px;
  border-bottom: 1px solid #edf0f4;
}

.section-heading h3 {
  margin: 0;
  color: #334155;
  font-size: 15px;
}

.section-heading p {
  margin: 5px 0 0;
  color: #94a3b8;
  font-size: 11px;
}

.findings-list {
  max-height: 850px;
  min-height: 400px;
  overflow-y: auto;
}

.finding-item {
  display: block;
  width: 100%;
  padding: 16px 18px;
  border: 0;
  border-bottom: 1px solid #edf0f4;
  border-left: 3px solid transparent;
  outline: none;
  text-align: left;
  cursor: pointer;
  background: #fff;
  transition:
    background 0.18s ease,
    border-color 0.18s ease;
}

.finding-item:hover {
  background: #f8fbfd;
}

.finding-item.active {
  border-left-color: #299dbc;
  background: #f2f9fc;
}

.finding-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.finding-id {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
}

.finding-title {
  display: block;
  margin-top: 9px;
  overflow: visible;
  color: #334155;
  font-size: 13px;
  line-height: 1.5;
  white-space: normal;
  overflow-wrap: anywhere;
}

.finding-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 9px;
  color: #8795a8;
  font-size: 11px;
  flex-wrap: wrap;
}

.finding-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.finding-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.status-text {
  color: #64748b;
  font-size: 10px;
}

.time-text {
  margin-left: auto;
  color: #a1aab8;
  font-size: 10px;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 7px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.risk-critical {
  color: #c2414e;
  background: #fff0f2;
}

.risk-high {
  color: #d66b23;
  background: #fff3e8;
}

.risk-medium {
  color: #ad8510;
  background: #fff8df;
}

.risk-low {
  color: #197f9d;
  background: #eaf7fb;
}

.risk-info,
.risk-informational,
.risk-unknown {
  color: #687a90;
  background: #eef2f6;
}

.finding-detail-panel {
  min-height: 600px;
}

.detail-container {
  min-height: 560px;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #edf0f4;
}

.detail-header-main {
  min-width: 0;
  flex: 1 1 auto;
}

.detail-id {
  color: #299dbc;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
}

.detail-header h3 {
  margin: 7px 0 12px;
  color: #26364a;
  font-size: 22px;
  line-height: 1.4;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.detail-risk {
  height: 24px;
  padding: 0 9px;
}

.detail-section {
  padding: 22px 0;
  border-bottom: 1px solid #edf0f4;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 14px;
  color: #34455a;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.section-title svg {
  width: 15px;
  height: 15px;
  color: #299dbc;
}

.metadata-grid {
  display: grid;
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metadata-grid > div {
  min-width: 0;
  padding: 12px;
  border: 1px solid #edf0f4;
  border-radius: 9px;
  background: #fafbfc;
}

.metadata-grid span {
  display: block;
  color: #94a3b8;
  font-size: 10px;
}

.metadata-grid strong {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.risk-score-box {
  display: grid;
  grid-template-columns:
    130px 1fr;
  gap: 20px;
  align-items: center;
  padding: 16px;
  border: 1px solid #edf0f4;
  border-radius: 10px;
  background: #fafbfc;
}

.risk-score-value span {
  display: block;
  color: #94a3b8;
  font-size: 10px;
}

.risk-score-value strong {
  color: #26364a;
  font-size: 32px;
}

.risk-score-value small {
  margin-left: 3px;
  color: #94a3b8;
}

.risk-progress-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 11px;
}

.risk-progress-heading strong {
  color: #334155;
  text-transform: uppercase;
}

.risk-reason {
  margin-top: 12px;
  padding: 13px 15px;
  border-left: 3px solid #d4aa26;
  border-radius: 5px;
  color: #59697b;
  font-size: 12px;
  line-height: 1.7;
  background: #fffbef;
}

.text-block {
  color: #56677b;
  font-size: 12px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.evidence-block {
  max-height: 390px;
  margin: 0;
  padding: 16px;
  overflow: auto;
  border: 1px solid #26384d;
  border-radius: 10px;
  color: #cbd8e6;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  font-size: 11px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  background: #182332;
}

.investigation-callout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-top: 22px;
  padding: 18px;
  border: 1px solid #d8edf5;
  border-radius: 12px;
  background:
    linear-gradient(
      135deg,
      #f4fbfd,
      #f9fcfd
    );
}

.callout-label {
  color: #299dbc;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 1.3px;
}

.investigation-callout h4 {
  margin: 5px 0;
  color: #334155;
}

.investigation-callout p {
  max-width: 620px;
  margin: 0;
  color: #7b899b;
  font-size: 11px;
  line-height: 1.6;
}

@media (max-width: 1250px) {
  .workspace-grid {
    grid-template-columns:
      minmax(300px, 0.85fr)
      minmax(0, 1.35fr);
  }

  .metadata-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .findings-list {
    max-height: 500px;
  }
}

@media (max-width: 760px) {
  .page-heading {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .filter-panel {
    align-items: flex-start;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }

  .detail-header {
    flex-direction: column;
  }

  .metadata-grid {
    grid-template-columns: 1fr;
  }

  .risk-score-box {
    grid-template-columns: 1fr;
  }

  .investigation-callout {
    flex-direction: column;
    align-items: flex-start;
  }
}
/* =========================
   Finding detail polish
   ========================= */

.workspace-grid {
  min-width: 0;
}

.workspace-grid > * {
  min-width: 0;
}

.finding-detail-panel {
  width: 100%;
  min-width: 0;

  overflow: hidden;
}

.detail-container {
  width: 100%;
  min-width: 0;
}

.detail-header {
  width: 100%;
  min-width: 0;

  align-items: flex-start;

  gap: 16px;
}

.detail-header-main {
  flex: 1 1 auto;
  min-width: 0;
}

.detail-id {
  overflow-wrap: anywhere;
}

.detail-header h3 {
  width: 100%;
  max-width: 100%;

  margin:
    7px 0 12px;

  font-size:
    clamp(
      18px,
      2vw,
      22px
    );

  line-height: 1.35;

  white-space: normal;

  overflow-wrap: anywhere;
  word-break: break-word;
}

.detail-tags {
  width: 100%;
  min-width: 0;

  display: flex;
  flex-wrap: wrap;

  gap: 8px;
}

.detail-tags > * {
  flex-shrink: 0;

  max-width: 100%;
}


/* Metadata 不要在中等宽度还强制四列 */

.metadata-grid {
  min-width: 0;

  grid-template-columns:
    repeat(
      4,
      minmax(0, 1fr)
    );
}

.metadata-grid > div {
  min-width: 0;
}

.metadata-grid strong {
  white-space: normal;

  overflow: visible;
  text-overflow: unset;

  overflow-wrap: anywhere;
  word-break: break-word;

  line-height: 1.5;
}


/* Risk block */

.risk-score-box {
  min-width: 0;

  grid-template-columns:
    minmax(110px, 130px)
    minmax(0, 1fr);
}


/* =========================
   Finding responsive layout
   ========================= */

@media (max-width: 1600px) {
  .workspace-grid {
    grid-template-columns:
      minmax(300px, 0.72fr)
      minmax(0, 1.7fr);
  }

  .metadata-grid {
    grid-template-columns:
      repeat(
        2,
        minmax(0, 1fr)
      );
  }
}

@media (max-width: 1180px) {
  .workspace-grid {
    grid-template-columns:
      minmax(0, 1fr);
  }

  .metadata-grid {
    grid-template-columns:
      repeat(
        2,
        minmax(0, 1fr)
      );
  }
}

@media (max-width: 720px) {
  .detail-header {
    flex-direction: column;
  }

  .detail-header-main {
    width: 100%;
    flex: 1 1 auto;
    min-width: 0;
  }

  .metadata-grid {
    grid-template-columns:
      minmax(0, 1fr);
  }

  .risk-score-box {
    grid-template-columns:
      minmax(0, 1fr);
  }
}
</style>