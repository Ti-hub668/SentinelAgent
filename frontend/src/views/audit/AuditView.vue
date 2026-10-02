<script setup>
import { useI18n } from 'vue-i18n'
import { useDisplayLabels } from '../../i18n/display'
const { t, locale } = useI18n()
const { label } = useDisplayLabels()

import {
  computed,
  onMounted,
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
  Check,
  Clock,
  Cpu,
  Document,
  Filter,
  Refresh,
  Search,
  WarningFilled,
} from '@element-plus/icons-vue'

import {
  getFinding,
  getInvestigationRun,
  getInvestigationRuns,
  getInvestigationTrace,
  reconcileInvestigationExecutions,
} from '../../api'

const route = useRoute()
const router = useRouter()

const runs = ref([])
const selectedRun = ref(null)
const workflow = ref(null)
const trace = ref(null)
const finding = ref(null)
const selectedEvent = ref(null)

const loadingRuns = ref(false)
const loadingTrace = ref(false)
const reconciling = ref(false)

const reconciliationResult = ref(null)

const runSearch = ref('')
const runStatusFilter = ref('')
const eventSearch = ref('')
const eventStatusFilter = ref('')
const eventCategoryFilter = ref('')

const events = computed(
  () => trace.value?.events || [],
)

const runStats = computed(() => ({
  total: runs.value.length,

  completed:
    runs.value.filter(
      (item) =>
        item.status === 'completed',
    ).length,

  failed:
    runs.value.filter(
      (item) =>
        item.status === 'failed',
    ).length,

  events:
    runs.value.reduce(
      (sum, item) =>
        sum +
        Number(
          item.event_count || 0,
        ),
      0,
    ),
}))

const filteredRuns = computed(() => {
  const keyword =
    runSearch.value
      .trim()
      .toLowerCase()

  return runs.value.filter(
    (item) => {
      const matchesStatus =
        !runStatusFilter.value ||
        item.status ===
          runStatusFilter.value

      const searchable = [
        item.id,
        item.finding_id,
        item.final_verdict,
        item.status,
      ]
        .join(' ')
        .toLowerCase()

      return (
        matchesStatus &&
        (
          !keyword ||
          searchable.includes(keyword)
        )
      )
    },
  )
})

function eventCategory(event) {
  const type =
    event?.event_type || ''

  if (
    [
      'context_built',
      'triage_completed',
      'research_completed',
      'evidence_assessed',
      'risk_enriched',
      'grounding_validated',
    ].includes(type)
  ) {
    return 'investigation'
  }

  if (
    [
      'response_planned',
      'policy_evaluated',
    ].includes(type)
  ) {
    return 'response'
  }

  if (
    [
      'approval_requested',
      'approval_resolved',
    ].includes(type)
  ) {
    return 'governance'
  }

  if (
    type.startsWith(
      'tool_execution',
    ) ||
    type.startsWith(
      'tool_reconciliation',
    )
  ) {
    return 'execution'
  }

  return 'system'
}

const filteredEvents = computed(() => {
  const keyword =
    eventSearch.value
      .trim()
      .toLowerCase()

  return events.value.filter(
    (event) => {
      const category =
        eventCategory(event)

      const searchable = [
        event.event_type,
        event.node_name,
        event.summary,
      ]
        .join(' ')
        .toLowerCase()

      return (
        (
          !eventStatusFilter.value ||
          event.status ===
            eventStatusFilter.value
        ) &&
        (
          !eventCategoryFilter.value ||
          category ===
            eventCategoryFilter.value
        ) &&
        (
          !keyword ||
          searchable.includes(keyword)
        )
      )
    },
  )
})

const selectedRunDuration = computed(
  () => {
    const run =
      trace.value?.run

    if (
      !run?.started_at ||
      !run?.finished_at
    ) {
      return '—'
    }

    const start =
      new Date(
        run.started_at,
      ).getTime()

    const finish =
      new Date(
        run.finished_at,
      ).getTime()

    if (
      Number.isNaN(start) ||
      Number.isNaN(finish)
    ) {
      return '—'
    }

    const seconds =
      Math.max(
        0,
        Math.round(
          (finish - start) /
          1000,
        ),
      )

    if (seconds < 60) {
      return t('feedback.durationSeconds', { seconds })
    }

    const minutes =
      Math.floor(
        seconds / 60,
      )

    const remain =
      seconds % 60

    return t('feedback.durationMinutes', { minutes, seconds: remain })
  },
)


const isResearchEvent = computed(
  () =>
    selectedEvent.value
      ?.event_type ===
    'research_completed',
)

const researchMetadata = computed(
  () =>
    selectedEvent.value
      ?.event_metadata || {},
)

const researchEvidence = computed(
  () => {
    const value =
      researchMetadata.value
        ?.evidence

    return Array.isArray(value)
      ? value
      : []
  },
)

const researchIntelligence = computed(
  () => {
    const value =
      researchMetadata.value
        ?.intelligence

    return (
      value &&
      typeof value === 'object'
        ? value
        : null
    )
  },
)

const researchSources = computed(
  () => {
    const value =
      researchMetadata.value
        ?.retrieved_sources

    return Array.isArray(value)
      ? value
      : []
  },
)

const hasStructuredResearchMetadata =
  computed(
    () =>
      Boolean(
        researchMetadata.value
          ?.retrieval_strategy ||
        researchMetadata.value
          ?.rag_query ||
        researchMetadata.value
          ?.rag_index_path ||
        researchEvidence.value.length ||
        researchIntelligence.value,
      ),
  )

const selectedMetadata = computed(
  () =>
    selectedEvent.value
      ?.event_metadata || {},
)

const isResponseEvent = computed(
  () =>
    selectedEvent.value
      ?.event_type ===
    'response_planned',
)

const isPolicyEvent = computed(
  () =>
    selectedEvent.value
      ?.event_type ===
    'policy_evaluated',
)

const isApprovalEvent = computed(
  () =>
    [
      'approval_requested',
      'approval_resolved',
    ].includes(
      selectedEvent.value
        ?.event_type,
    ),
)

const isToolExecutionEvent = computed(
  () =>
    selectedEvent.value
      ?.event_type
      ?.startsWith(
        'tool_execution',
      ) || false,
)

const responsePlan = computed(
  () => {
    const metadata =
      selectedMetadata.value

    const nested =
      metadata?.response_plan

    return (
      nested &&
      typeof nested === 'object'
        ? nested
        : metadata
    )
  },
)

const responseToolRequests =
  computed(
    () => {
      const value =
        responsePlan.value
          ?.tool_requests ||
        selectedMetadata.value
          ?.tool_requests

      return Array.isArray(value)
        ? value
        : []
    },
  )

const policyEvaluation = computed(
  () => {
    const metadata =
      selectedMetadata.value

    const nested =
      metadata
        ?.policy_evaluation

    return (
      nested &&
      typeof nested === 'object'
        ? nested
        : metadata
    )
  },
)

const policyResults = computed(
  () => {
    const value =
      policyEvaluation.value
        ?.results ||
      selectedMetadata.value
        ?.results

    return Array.isArray(value)
      ? value
      : []
  },
)

const approvalRecord = computed(
  () => {
    const metadata =
      selectedMetadata.value

    const nested =
      metadata?.approval

    return {
      ...metadata,

      ...(
        nested &&
        typeof nested === 'object'
          ? nested
          : {}
      ),
    }
  },
)

const approvalToolRequest =
  computed(
    () =>
      approvalRecord.value
        ?.tool_request ||
      selectedMetadata.value
        ?.tool_request ||
      null,
  )

const executionRecord = computed(
  () => {
    const metadata =
      selectedMetadata.value

    const nested =
      metadata
        ?.execution_result

    return {
      ...metadata,

      ...(
        nested &&
        typeof nested === 'object'
          ? nested
          : {}
      ),
    }
  },
)

const executionToolRequest =
  computed(
    () =>
      executionRecord.value
        ?.tool_request ||
      selectedMetadata.value
        ?.tool_request ||
      (
        selectedMetadata.value
          ?.tool_name
          ? {
              tool_name:
                selectedMetadata
                  .value
                  .tool_name,

              target:
                selectedMetadata
                  .value
                  .target,

              parameters: {},
            }
          : null
      ),
  )

const isStructuredAuditEvent =
  computed(
    () =>
      (
        isResearchEvent.value &&
        hasStructuredResearchMetadata
          .value
      ) ||
      isResponseEvent.value ||
      isPolicyEvent.value ||
      isApprovalEvent.value ||
      isToolExecutionEvent.value,
  )

function normalizeList(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean)
  }

  if (
    typeof value === 'string' &&
    value.trim()
  ) {
    return [value.trim()]
  }

  return []
}

function formatScore(value) {
  const score = Number(value)

  if (Number.isNaN(score)) {
    return '—'
  }

  return score.toFixed(4)
}

function matchTypeLabel(value) {
  const labels = {
    canonical_exact:
      t('interface.canonicalExact'),
    relationship:
      t('interface.relationship'),
    semantic:
      t('interface.semantic'),
  }

  return (
    labels[value] ||
    value ||
    t('interface.unknown')
  )
}

function matchTypeTagType(value) {
  if (value === 'canonical_exact') {
    return 'success'
  }

  if (value === 'relationship') {
    return 'warning'
  }

  return 'info'
}

function compactHash(value) {
  if (!value) {
    return '—'
  }

  const textValue = String(value)

  if (textValue.length <= 24) {
    return textValue
  }

  return `${textValue.slice(
    0,
    12,
  )}…${textValue.slice(-8)}`
}

function booleanLabel(value) {
  if (value === true) {
    return t('interface.matched')
  }

  if (value === false) {
    return t('interface.noMatch')
  }

  return '—'
}

function formatDate(value) {
  if (!value) {
    return '—'
  }

  const date =
    new Date(value)

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value
  }

  return date.toLocaleString(locale.value)
}

function decisionTagType(value) {
  if (value === 'ALLOW') {
    return 'success'
  }

  if (value === 'DENY') {
    return 'danger'
  }

  if (
    value ===
    'REQUIRE_APPROVAL'
  ) {
    return 'warning'
  }

  return 'info'
}

function approvalStatusTagType(
  value,
) {
  if (value === 'approved') {
    return 'success'
  }

  if (value === 'rejected') {
    return 'danger'
  }

  if (value === 'pending') {
    return 'warning'
  }

  return 'info'
}

function executionStatusTagType(
  value,
) {
  if (
    value === 'completed'
  ) {
    return 'success'
  }

  if (
    value === 'simulated'
  ) {
    return 'warning'
  }

  if (
    value === 'failed' ||
    value === 'blocked'
  ) {
    return 'danger'
  }

  return 'info'
}

function yesNoLabel(value) {
  if (value === true) {
    return t('interface.yes')
  }

  if (value === false) {
    return t('interface.no')
  }

  return '—'
}

function formatTime(value) {
  if (!value) {
    return '—'
  }

  const date =
    new Date(value)

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value
  }

  return date.toLocaleTimeString(locale.value)
}

function runStatusType(status) {
  if (status === 'completed') {
    return 'success'
  }

  if (status === 'failed') {
    return 'danger'
  }

  return 'warning'
}

function eventStatusType(status) {
  if (status === 'completed') {
    return 'success'
  }

  if (status === 'failed') {
    return 'danger'
  }

  return 'warning'
}

function categoryLabel(category) {
  const labels = {
    investigation:
      t('interface.investigation'),

    response:
      t('interface.response'),

    governance:
      t('interface.governance'),

    execution:
      t('interface.execution'),

    system:
      t('interface.system'),
  }

  return (
    labels[category] ||
    category
  )
}

function categoryClass(category) {
  return `category-${category}`
}

function eventLabel(event) {
  const labels = {
    context_built:
      t('interface.contextBuilder'),

    triage_completed:
      t('interface.triage'),

    research_completed:
      t('interface.researchRagIntel'),

    evidence_assessed:
      t('interface.evidenceAssessment'),

    risk_enriched:
      t('interface.riskSynthesis'),

    grounding_validated:
      t('interface.groundingValidator'),

    response_planned:
      t('interface.responseAgent'),

    policy_evaluated:
      t('interface.policyEngine'),

    approval_requested:
      t('interface.approvalRequested'),

    approval_resolved:
      t('interface.approvalResolved'),

    tool_execution_simulated:
      t('interface.toolBrokerSimulated'),

    tool_execution_completed:
      t('interface.toolBroker'),

    tool_execution_failed:
      t('interface.toolBrokerFailed226'),

    tool_reconciliation_started:
      t('interface.reconciliationStarted'),

    tool_reconciliation_confirmed:
      t('interface.reconciliationConfirmed'),

    tool_reconciliation_unresolved:
      t('interface.reconciliationUnresolved'),

    tool_reconciliation_failed:
      t('interface.reconciliationFailed'),
  }

  return (
    labels[
      event?.event_type
    ] ||
    event?.node_name ||
    event?.event_type ||
    t('interface.auditEvent')
  )
}

function eventIcon(event) {
  const category =
    eventCategory(event)

  if (
    event.status === 'failed'
  ) {
    return WarningFilled
  }

  if (
    category === 'execution'
  ) {
    return Cpu
  }

  if (
    category === 'governance'
  ) {
    return Check
  }

  if (
    category === 'response'
  ) {
    return Document
  }

  return Clock
}

async function loadRuns() {
  loadingRuns.value = true

  try {
    runs.value =
      await getInvestigationRuns({
        silent: true,
      })
  } catch (error) {
    console.error(error)

    ElMessage.error(
      t('interface.failedToLoadInvestigationRuns'),
    )
  } finally {
    loadingRuns.value = false
  }
}

async function selectRun(run) {
  if (!run?.id) {
    return
  }

  selectedRun.value = run
  loadingTrace.value = true

  try {
    const [
      workflowResult,
      traceResult,
      findingResult,
    ] =
      await Promise.all([
        getInvestigationRun(
          run.id,
          {
            silent: true,
          },
        ),

        getInvestigationTrace(
          run.id,
          {
            silent: true,
          },
        ),

        getFinding(
          run.finding_id,
          {
            silent: true,
          },
        ),
      ])

    workflow.value =
      workflowResult

    trace.value =
      traceResult

    finding.value =
      findingResult

    selectedEvent.value =
      traceResult.events?.[
        traceResult.events.length -
          1
      ] || null

    eventSearch.value = ''
    eventStatusFilter.value = ''
    eventCategoryFilter.value = ''

    await router.replace({
      name: 'audit',

      query: {
        run_id: run.id,
      },
    })
  } catch (error) {
    console.error(error)

    ElMessage.error(
      t('interface.failedToLoadAuditTrace'),
    )
  } finally {
    loadingTrace.value = false
  }
}

async function reconcileSelectedRun() {
  const runId =
    trace.value?.run?.id ||
    selectedRun.value?.id

  if (!runId) {
    ElMessage.warning(
      t('interface.pleaseSelectAnInvestigationRunFirst'),
    )
    return
  }

  reconciling.value = true
  reconciliationResult.value = null

  try {
    const result =
      await reconcileInvestigationExecutions(
        runId,
      )

    reconciliationResult.value =
      result

    const [
      runResponse,
      traceResponse,
    ] = await Promise.all([
      getInvestigationRun(runId),
      getInvestigationTrace(runId),
    ])

    workflow.value =
      runResponse

    trace.value =
      traceResponse

    ElMessage.success(
      t('feedback.reconciliationSummary', { confirmed: result.confirmed, unresolved: result.unresolved, failed: result.failed }),
    )
  } catch (error) {
    console.error(
      t('interface.reconciliationError'),
      error,
    )

    ElMessage.error(
      error?.response?.data?.detail ||
      error?.message ||
      t('interface.executionReconciliationFailed'),
    )
  } finally {
    reconciling.value = false
  }
}
async function refreshAll() {
  const currentId =
    selectedRun.value?.id

  await loadRuns()

  if (currentId) {
    const updated =
      runs.value.find(
        (item) =>
          item.id === currentId,
      )

    if (updated) {
      await selectRun(
        updated,
      )
    }
  }
}

function goInvestigation() {
  if (!selectedRun.value) {
    return
  }

  router.push({
    name: 'investigations',

    query: {
      finding_id:
        selectedRun.value
          .finding_id,

      run_id:
        selectedRun.value.id,
    },
  })
}

function goResponse() {
  if (!selectedRun.value) {
    return
  }

  router.push({
    name: 'response',

    query: {
      finding_id:
        selectedRun.value
          .finding_id,

      run_id:
        selectedRun.value.id,
    },
  })
}

onMounted(async () => {
  await loadRuns()

  const queryRun =
    Number(route.query.run_id)

  const initial =
    runs.value.find(
      (item) =>
        item.id === queryRun,
    ) ||
    runs.value[0]

  if (initial) {
    await selectRun(initial)
  }
})
</script>

<template>
  <div class="audit-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">
          {{ t('interface.investigationLedger234') }}
        </div>

        <h2>
          {{ t('interface.auditCenter') }}
        </h2>

        <p>
          {{ t('interface.endToEndAuditTrailOfAgentInvestigationsGovernanceApprovalsAndToolBrokerExecution') }}
        </p>
      </div>

      <el-button
        :icon="Refresh"
        :loading="loadingRuns"
        @click="refreshAll"
      >
        {{ t('interface.refreshAuditData') }}
      </el-button>

      <el-button
        type="warning"
        :loading="reconciling"
        :disabled="!trace?.run?.id"
        @click="reconcileSelectedRun"
      >
        {{ t('interface.reconcileStaleExecutions') }}
      </el-button>
    </div>

    <el-alert
      v-if="reconciliationResult"
      type="info"
      show-icon
      :closable="false"
      class="reconciliation-alert"
    >
      <template #title>
        {{ t('interface.reconciliationCompleted') }}
      </template>

      {{ t('interface.checked') }}
      {{ reconciliationResult.checked }}

      {{ t('interface.confirmed') }}
      {{ reconciliationResult.confirmed }}

      {{ t('interface.unresolved') }}
      {{ reconciliationResult.unresolved }}

      {{ t('interface.failed243') }}
      {{ reconciliationResult.failed }}
    </el-alert>

    <div class="summary-grid">
      <section class="panel summary-card">
        <span>
          {{ t('interface.investigationRuns') }}
        </span>

        <strong>
          {{ runStats.total }}
        </strong>

        <small>
          {{ t('interface.ledgerRecords') }}
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          {{ t('interface.completed') }}
        </span>

        <strong>
          {{ runStats.completed }}
        </strong>

        <small>
          {{ t('interface.completedRuns') }}
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          {{ t('interface.failed') }}
        </span>

        <strong>
          {{ runStats.failed }}
        </strong>

        <small>
          {{ t('interface.failedRuns') }}
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          {{ t('interface.auditEvents') }}
        </span>

        <strong>
          {{ runStats.events }}
        </strong>

        <small>
          {{ t('interface.recordedEvents') }}
        </small>
      </section>
    </div>

    <div class="audit-workspace">
      <section
        class="panel run-panel"
        v-loading="loadingRuns"
      >
        <div class="panel-heading">
          <div>
            <span class="section-label">
              {{ t('interface.runQueue') }}
            </span>

            <h3>
              {{ t('interface.investigationRuns') }}
            </h3>
          </div>

          <el-tag
            type="info"
            effect="plain"
          >
            {{
              filteredRuns.length
            }}
          </el-tag>
        </div>

        <div class="run-filters">
          <el-input
            v-model="runSearch"
            :prefix-icon="Search"
            clearable
            :placeholder="t('interface.runFindingVerdict')"
          />

          <el-select
            v-model="
              runStatusFilter
            "
            clearable
            :placeholder="t('interface.runStatus')"
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

        <div
          v-if="
            filteredRuns.length
          "
          class="run-list"
        >
          <button
            v-for="run in
              filteredRuns"
            :key="run.id"
            type="button"
            class="run-item"
            :class="{
              active:
                selectedRun?.id ===
                run.id,
              failed:
                run.status ===
                'failed',
            }"
            @click="selectRun(run)"
          >
            <div class="run-item-top">
              <strong>
                {{ t('interface.run253') }}{{ run.id }}
              </strong>

              <el-tag
                size="small"
                :type="
                  runStatusType(
                    run.status,
                  )
                "
              >
                {{ label(run.status) }}
              </el-tag>
            </div>

            <div class="run-finding">
              {{ t('interface.finding177') }}{{ run.finding_id }}
            </div>

            <div class="run-verdict">
              {{ label(run.final_verdict ||
                t('interface.noVerdict')) }}
            </div>

            <div class="run-footer">
              <span>
                {{
                  run.event_count
                }}
                {{ t('interface.events') }}
              </span>

              <span>
                {{
                  formatDate(
                    run.started_at,
                  )
                }}
              </span>
            </div>
          </button>
        </div>

        <el-empty
          v-else
          :description="t('interface.noMatchingRuns')"
        />
      </section>

      <section
        class="panel timeline-panel"
        v-loading="loadingTrace"
      >
        <div class="panel-heading">
          <div>
            <span class="section-label">
              {{ t('interface.auditTimeline') }}
            </span>

            <h3>
              {{
                selectedRun
                  ? t('interface.runValue', { p0: selectedRun.id })
                  : t('interface.selectRun')
              }}
            </h3>
          </div>

          <el-tag
            v-if="trace"
            effect="plain"
          >
            {{
              filteredEvents.length
            }}
            /
            {{
              events.length
            }}
            {{ t('interface.events') }}
          </el-tag>
        </div>

        <template v-if="trace">
          <div class="run-overview">
            <div>
              <span>
                {{ t('interface.finding259') }}
              </span>

              <strong>
                #{{ trace.run.finding_id }}
              </strong>
            </div>

            <div>
              <span>
                {{ t('interface.finalVerdict') }}
              </span>

              <strong>
                {{ label(trace.run
                    .final_verdict ||
                  '—') }}
              </strong>
            </div>

            <div>
              <span>
                {{ t('interface.duration') }}
              </span>

              <strong>
                {{
                  selectedRunDuration
                }}
              </strong>
            </div>
          </div>

          <div class="event-filters">
            <el-input
              v-model="eventSearch"
              :prefix-icon="Search"
              clearable
              :placeholder="t('interface.searchEvents')"
            />

            <el-select
              v-model="
                eventCategoryFilter
              "
              clearable
              :placeholder="t('interface.category')"
            >
              <el-option
                :label="t('interface.investigation')"
                value="investigation"
              />

              <el-option
                :label="t('interface.response')"
                value="response"
              />

              <el-option
                :label="t('interface.governance')"
                value="governance"
              />

              <el-option
                :label="t('interface.execution')"
                value="execution"
              />
            </el-select>

            <el-select
              v-model="
                eventStatusFilter
              "
              clearable
              :placeholder="t('interface.status94')"
            >
              <el-option
                :label="t('interface.completed')"
                value="completed"
              />

              <el-option
                :label="t('interface.started')"
                value="started"
              />

              <el-option
                :label="t('interface.failed')"
                value="failed"
              />
            </el-select>
          </div>

          <div
            v-if="
              filteredEvents.length
            "
            class="timeline"
          >
            <button
              v-for="event in
                filteredEvents"
              :key="event.id"
              type="button"
              class="timeline-event"
              :class="{
                active:
                  selectedEvent?.id ===
                  event.id,
                failed:
                  event.status ===
                  'failed',
              }"
              @click="
                selectedEvent = event
              "
            >
              <div
                class="timeline-icon"
                :class="
                  categoryClass(
                    eventCategory(
                      event,
                    ),
                  )
                "
              >
                <el-icon>
                  <component
                    :is="
                      eventIcon(event)
                    "
                  />
                </el-icon>
              </div>

              <div class="timeline-main">
                <div class="timeline-header">
                  <div>
                    <strong>
                      {{
                        eventLabel(
                          event,
                        )
                      }}
                    </strong>

                    <span
                      class="event-category"
                    >
                      {{
                        categoryLabel(
                          eventCategory(
                            event,
                          ),
                        )
                      }}
                    </span>
                  </div>

                  <el-tag
                    size="small"
                    :type="
                      eventStatusType(
                        event.status,
                      )
                    "
                  >
                    {{ label(event.status) }}
                  </el-tag>
                </div>

                <p>
                  {{ label(event.summary ||
                    event.event_type) }}
                </p>

                <div class="timeline-meta">
                  <span>
                    {{ label(event.node_name ||
                      'system') }}
                  </span>

                  <span>
                    {{
                      formatTime(
                        event.created_at,
                      )
                    }}
                  </span>
                </div>
              </div>
            </button>
          </div>

          <el-empty
            v-else
            :description="t('interface.noMatchingEvents')"
          />
        </template>

        <el-empty
          v-else
          :description="t('interface.selectAnInvestigationRun')"
        />
      </section>

      <aside class="detail-column">
        <section
          v-if="
            selectedRun &&
            workflow
          "
          class="panel"
        >
          <div class="panel-heading">
            <div>
              <span class="section-label">
                {{ t('interface.workflowState') }}
              </span>

              <h3>
                {{ t('interface.runSummary') }}
              </h3>
            </div>

            <el-tag
              :type="
                runStatusType(
                  trace?.run?.status,
                )
              "
            >
              {{ label(workflow
                  .workflow_status) }}
            </el-tag>
          </div>

          <div
            v-if="finding"
            class="finding-card"
          >
            <span>
              {{ t('interface.finding177') }}{{ finding.id }}
            </span>

            <strong>
              {{ finding.title }}
            </strong>

            <small>
              {{ finding.target }}
            </small>
          </div>

          <div class="workflow-meta">
            <div>
              <span>
                {{ t('interface.verdict') }}
              </span>

              <strong>
                {{ label(workflow
                    .final_verdict ||
                  '—') }}
              </strong>
            </div>

            <div>
              <span>
                {{ t('interface.ledgerEvents') }}
              </span>

              <strong>
                {{ events.length }}
              </strong>
            </div>

            <div>
              <span>
                {{ t('interface.toolResults') }}
              </span>

              <strong>
                {{
                  workflow
                    .tool_results
                    ?.length || 0
                }}
              </strong>
            </div>
          </div>

          <div class="navigation-actions">
            <el-button
              @click="
                goInvestigation
              "
            >
              {{ t('interface.investigation') }}
            </el-button>

            <el-button
              type="primary"
              plain
              @click="goResponse"
            >
              {{ t('interface.response') }}
            </el-button>
          </div>
        </section>

        <section
          v-if="selectedEvent"
          class="panel event-detail"
        >
          <div class="panel-heading">
            <div>
              <span class="section-label">
                {{ t('interface.eventInspector') }}
              </span>

              <h3>
                {{
                  eventLabel(
                    selectedEvent,
                  )
                }}
              </h3>
            </div>

            <el-tag
              :type="
                eventStatusType(
                  selectedEvent.status,
                )
              "
            >
              {{ label(selectedEvent.status) }}
            </el-tag>
          </div>

          <div class="event-info">
            <div>
              <span>
                {{ t('interface.eventType') }}
              </span>

              <strong>
                {{ label(selectedEvent
                    .event_type) }}
              </strong>
            </div>

            <div>
              <span>
                {{ t('interface.node') }}
              </span>

              <strong>
                {{ label(selectedEvent
                    .node_name ||
                  '—') }}
              </strong>
            </div>

            <div>
              <span>
                {{ t('interface.category') }}
              </span>

              <strong>
                {{
                  categoryLabel(
                    eventCategory(
                      selectedEvent,
                    ),
                  )
                }}
              </strong>
            </div>

            <div>
              <span>
                {{ t('interface.createdAt270') }}
              </span>

              <strong>
                {{
                  formatDate(
                    selectedEvent
                      .created_at,
                  )
                }}
              </strong>
            </div>
          </div>

          <div class="event-summary">
            <span>
              {{ t('interface.summary') }}
            </span>

            <p>
              {{
                selectedEvent.summary ||
                t('interface.noSummaryRecorded')
              }}
            </p>
          </div>

          <template
            v-if="
              selectedEvent
                .event_metadata
            "
          >
            <template
              v-if="
                isResearchEvent &&
                hasStructuredResearchMetadata
              "
            >
              <div class="research-provenance">
                <section class="provenance-section">
                  <div class="provenance-section-heading">
                    <div>
                      <span class="provenance-kicker">
                        {{ t('interface.ragRetrieval') }}
                      </span>

                      <strong>
                        {{ t('interface.securityKnowledgeSearch') }}
                      </strong>
                    </div>

                    <el-tag
                      size="small"
                      type="info"
                    >
                      {{
                        researchMetadata
                          .retrieval_strategy ||
                        'retrieval'
                      }}
                    </el-tag>
                  </div>

                  <div class="retrieval-grid">
                    <div>
                      <span>{{ t('interface.topK') }}</span>
                      <strong>
                        {{
                          researchMetadata
                            .top_k ?? '—'
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>{{ t('interface.retrieved') }}</span>
                      <strong>
                        {{
                          researchMetadata
                            .retrieved_count ??
                          researchEvidence.length
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>{{ t('interface.ragUsed') }}</span>
                      <strong>
                        {{
                          researchMetadata
                            .rag_used
                            ? t('interface.yes')
                            : t('interface.no')
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>{{ t('interface.intelUsed') }}</span>
                      <strong>
                        {{
                          researchMetadata
                            .intelligence_used
                            ? t('interface.yes')
                            : t('interface.no')
                        }}
                      </strong>
                    </div>
                  </div>

                  <div
                    v-if="researchSources.length"
                    class="source-tags"
                  >
                    <span>{{ t('interface.sources') }}</span>

                    <div>
                      <el-tag
                        v-for="source in researchSources"
                        :key="source"
                        size="small"
                        effect="plain"
                      >
                        {{ source }}
                      </el-tag>
                    </div>
                  </div>

                  <div class="provenance-query">
                    <span>{{ t('interface.query') }}</span>

                    <div class="query-block">
                      {{
                        researchMetadata
                          .rag_query ||
                        t('interface.noRagQueryRecorded')
                      }}
                    </div>
                  </div>

                  <div class="provenance-index">
                    <span>{{ t('interface.index') }}</span>
                    <code>
                      {{
                        researchMetadata
                          .rag_index_path ||
                        '—'
                      }}
                    </code>
                  </div>
                </section>

                <section class="provenance-section">
                  <div class="provenance-section-heading">
                    <div>
                      <span class="provenance-kicker">
                        {{ t('interface.retrievedEvidence') }}
                      </span>

                      <strong>
                        {{ t('interface.auditableKnowledgeEvidence') }}
                      </strong>
                    </div>

                    <el-tag
                      size="small"
                      type="success"
                    >
                      {{ researchEvidence.length }}
                    </el-tag>
                  </div>

                  <div
                    v-if="researchEvidence.length"
                    class="evidence-list"
                  >
                    <article
                      v-for="(
                        evidence,
                        index
                      ) in researchEvidence"
                      :key="
                        evidence.document_id ||
                        `${evidence.source_id}-${index}`
                      "
                      class="evidence-card"
                    >
                      <div class="evidence-head">
                        <div class="evidence-number">
                          {{ index + 1 }}
                        </div>

                        <div class="evidence-title">
                          <strong>
                            {{
                              evidence.title ||
                              evidence.source_id ||
                              t('interface.knowledgeEvidence')
                            }}
                          </strong>

                          <span>
                            {{
                              evidence.source ||
                              t('interface.unknownSource')
                            }}
                            ·
                            {{
                              evidence.category ||
                              'uncategorized'
                            }}
                          </span>
                        </div>
                      </div>

                      <div class="evidence-badges">
                        <el-tag
                          size="small"
                          :type="
                            matchTypeTagType(
                              evidence.match_type,
                            )
                          "
                        >
                          {{
                            matchTypeLabel(
                              evidence.match_type,
                            )
                          }}
                        </el-tag>

                        <span class="score-pill">
                          {{ t('interface.score') }}
                          {{
                            formatScore(
                              evidence.score,
                            )
                          }}
                        </span>
                      </div>

                      <div class="evidence-fields">
                        <div>
                          <span>{{ t('interface.sourceId') }}</span>
                          <strong>
                            {{
                              evidence.source_id ||
                              '—'
                            }}
                          </strong>
                        </div>

                        <div>
                          <span>{{ t('interface.chunk') }}</span>
                          <strong>
                            {{
                              evidence.chunk_index ??
                              '—'
                            }}
                          </strong>
                        </div>

                        <div class="wide-field">
                          <span>{{ t('interface.documentId') }}</span>
                          <code>
                            {{
                              evidence.document_id ||
                              '—'
                            }}
                          </code>
                        </div>

                        <div class="wide-field">
                          <span>{{ t('interface.parentId') }}</span>
                          <code>
                            {{
                              evidence.parent_id ||
                              '—'
                            }}
                          </code>
                        </div>

                        <div class="wide-field">
                          <span>{{ t('interface.sourceUrl') }}</span>

                          <a
                            v-if="evidence.source_url"
                            :href="evidence.source_url"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {{ t('interface.openAuthoritativeSource') }}
                          </a>

                          <strong v-else>
                            —
                          </strong>
                        </div>

                        <div class="wide-field">
                          <span>{{ t('interface.contentSha256') }}</span>
                          <code
                            :title="
                              evidence.content_sha256 ||
                              ''
                            "
                          >
                            {{
                              compactHash(
                                evidence.content_sha256,
                              )
                            }}
                          </code>
                        </div>
                      </div>
                    </article>
                  </div>

                  <el-empty
                    v-else
                    :image-size="48"
                    :description="t('interface.noProvenanceEvidenceRecordedForThisRun')"
                  />
                </section>

                <section
                  v-if="researchIntelligence"
                  class="provenance-section"
                >
                  <div class="provenance-section-heading">
                    <div>
                      <span class="provenance-kicker">
                        {{ t('interface.structuredIntelligence') }}
                      </span>

                      <strong>
                        {{ t('interface.threatIntelligenceSignals') }}
                      </strong>
                    </div>
                  </div>

                  <div class="intel-grid">
                    <div>
                      <span>{{ t('interface.template') }}</span>
                      <strong>
                        {{
                          researchIntelligence
                            .template_id ||
                          '—'
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>{{ t('interface.cisaKev') }}</span>
                      <strong>
                        {{
                          booleanLabel(
                            researchIntelligence
                              .kev_matched,
                          )
                        }}
                      </strong>
                      <small>
                        {{
                          researchIntelligence
                            .kev_record_count ??
                          0
                        }} {{ t('interface.recordS') }}
                      </small>
                    </div>

                    <div>
                      <span>{{ t('interface.nvd') }}</span>
                      <strong>
                        {{
                          booleanLabel(
                            researchIntelligence
                              .nvd_matched,
                          )
                        }}
                      </strong>
                      <small>
                        {{
                          researchIntelligence
                            .nvd_record_count ??
                          0
                        }} {{ t('interface.recordS') }}
                      </small>
                    </div>
                  </div>

                  <div class="intel-identifiers">
                    <div>
                      <span>{{ t('interface.cveIds') }}</span>

                      <div
                        v-if="
                          normalizeList(
                            researchIntelligence
                              .cve_ids,
                          ).length
                        "
                        class="identifier-tags"
                      >
                        <el-tag
                          v-for="item in normalizeList(
                            researchIntelligence
                              .cve_ids,
                          )"
                          :key="item"
                          size="small"
                          effect="plain"
                        >
                          {{ item }}
                        </el-tag>
                      </div>

                      <strong v-else>
                        —
                      </strong>
                    </div>

                    <div>
                      <span>{{ t('interface.cweIds') }}</span>

                      <div
                        v-if="
                          normalizeList(
                            researchIntelligence
                              .cwe_ids,
                          ).length
                        "
                        class="identifier-tags"
                      >
                        <el-tag
                          v-for="item in normalizeList(
                            researchIntelligence
                              .cwe_ids,
                          )"
                          :key="item"
                          size="small"
                          type="warning"
                          effect="plain"
                        >
                          {{ item }}
                        </el-tag>
                      </div>

                      <strong v-else>
                        —
                      </strong>
                    </div>
                  </div>
                </section>


              </div>
            </template>
            <template
  v-else-if="
    isResponseEvent
  "
>
  <div class="research-provenance">
    <section class="provenance-section">
      <div
        class="provenance-section-heading"
      >
        <div>
          <span
            class="provenance-kicker"
          >
            {{ t('interface.responsePlan304') }}
          </span>

          <strong>
            {{ t('interface.governedResponseProposal') }}
          </strong>
        </div>

        <el-tag
          :type="
            responsePlan.dry_run
              ? 'warning'
              : 'success'
          "
        >
          {{ label(responsePlan.dry_run
              ? t('interface.dryRun306')
              : t('interface.live')) }}
        </el-tag>
      </div>

      <div class="retrieval-grid">
        <div>
          <span>
            {{ t('interface.finding259') }}
          </span>

          <strong>
            #{{
              responsePlan
                .finding_id ||
              selectedRun
                ?.finding_id ||
              '—'
            }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.verdict') }}
          </span>

          <strong>
            {{ label(responsePlan
                .grounded_verdict ||
              '—') }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.action') }}
          </span>

          <strong>
            {{ label(responsePlan
                .decision_action ||
              '—') }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.priority309') }}
          </span>

          <strong>
            {{ label(responsePlan
                .priority ||
              '—') }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.humanReview') }}
          </span>

          <strong>
            {{
              yesNoLabel(
                responsePlan
                  .requires_human_review,
              )
            }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.toolRequests') }}
          </span>

          <strong>
            {{
              responseToolRequests
                .length
            }}
          </strong>
        </div>
      </div>

      <div
        v-if="
          responsePlan.summary
        "
        class="governance-note"
      >
        <span>
          {{ t('interface.responseSummary') }}
        </span>

        <p>
          {{
            responsePlan.summary
          }}
        </p>
      </div>
    </section>

    <section
      v-if="
        normalizeList(
          responsePlan
            .containment_plan,
        ).length ||
        normalizeList(
          responsePlan
            .remediation_plan,
        ).length ||
        normalizeList(
          responsePlan
            .verification_plan,
        ).length
      "
      class="provenance-section"
    >
      <div
        class="provenance-section-heading"
      >
        <div>
          <span
            class="provenance-kicker"
          >
            {{ t('interface.responseSteps') }}
          </span>

          <strong>
            {{ t('interface.containRemediateVerify') }}
          </strong>
        </div>
      </div>

      <div class="plan-grid">
        <div class="plan-card">
          <span>
            {{ t('interface.containment') }}
          </span>

          <ul
            v-if="
              normalizeList(
                responsePlan
                  .containment_plan,
              ).length
            "
          >
            <li
              v-for="(
                item,
                index
              ) in normalizeList(
                responsePlan
                  .containment_plan,
              )"
              :key="index"
            >
              {{ item }}
            </li>
          </ul>

          <small v-else>
            {{ t('interface.noContainmentAction') }}
          </small>
        </div>

        <div class="plan-card">
          <span>
            {{ t('interface.remediation') }}
          </span>

          <ul
            v-if="
              normalizeList(
                responsePlan
                  .remediation_plan,
              ).length
            "
          >
            <li
              v-for="(
                item,
                index
              ) in normalizeList(
                responsePlan
                  .remediation_plan,
              )"
              :key="index"
            >
              {{ item }}
            </li>
          </ul>

          <small v-else>
            {{ t('interface.noRemediationStep') }}
          </small>
        </div>

        <div class="plan-card">
          <span>
            {{ t('interface.verification') }}
          </span>

          <ul
            v-if="
              normalizeList(
                responsePlan
                  .verification_plan,
              ).length
            "
          >
            <li
              v-for="(
                item,
                index
              ) in normalizeList(
                responsePlan
                  .verification_plan,
              )"
              :key="index"
            >
              {{ item }}
            </li>
          </ul>

          <small v-else>
            {{ t('interface.noVerificationStep') }}
          </small>
        </div>
      </div>
    </section>

    <section
      v-if="
        responseToolRequests
          .length
      "
      class="provenance-section"
    >
      <div
        class="provenance-section-heading"
      >
        <div>
          <span
            class="provenance-kicker"
          >
            {{ t('interface.toolRequests319') }}
          </span>

          <strong>
            {{ t('interface.proposedAgentActions') }}
          </strong>
        </div>
      </div>

      <div class="request-stack">
        <article
          v-for="(
            request,
            index
          ) in responseToolRequests"
          :key="
            `${request.tool_name}-${index}`
          "
          class="evidence-card"
        >
          <div
            class="evidence-card-heading"
          >
            <div>
              <strong>
                {{ label(request
                    .tool_name ||
                  t('interface.unknownTool')) }}
              </strong>

              <small>
                {{
                  request.target ||
                  t('interface.noTarget')
                }}
              </small>
            </div>

            <el-tag
              type="warning"
              size="small"
            >
              {{ t('interface.request') }}{{ index }}
            </el-tag>
          </div>

          <div
            v-if="request.reason"
            class="governance-note"
          >
            <span>
              {{ t('interface.reason') }}
            </span>

            <p>
              {{ request.reason }}
            </p>
          </div>

          <pre
            v-if="
              request.parameters &&
              Object.keys(
                request.parameters,
              ).length
            "
            class="mini-metadata"
          >{{
            JSON.stringify(
              request.parameters,
              null,
              2,
            )
          }}</pre>
        </article>
      </div>
    </section>
  </div>
</template>
<template
  v-else-if="
    isPolicyEvent
  "
>
  <div class="research-provenance">
    <section class="provenance-section">
      <div
        class="provenance-section-heading"
      >
        <div>
          <span
            class="provenance-kicker"
          >
            {{ t('interface.policyDecision325') }}
          </span>

          <strong>
            {{ t('interface.governanceEvaluation') }}
          </strong>
        </div>

        <el-tag type="info">
          {{ label(policyEvaluation
              .dry_run
              ? t('interface.dryRun306')
              : t('interface.policy')) }}
        </el-tag>
      </div>

      <div class="retrieval-grid">
        <div>
          <span>
            {{ t('interface.finding259') }}
          </span>

          <strong>
            #{{
              policyEvaluation
                .finding_id ||
              selectedRun
                ?.finding_id ||
              '—'
            }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.verdict') }}
          </span>

          <strong>
            {{ label(policyEvaluation
                .grounded_verdict ||
              '—') }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.allow') }}
          </span>

          <strong>
            {{
              policyEvaluation
                .allow_count ?? 0
            }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.deny') }}
          </span>

          <strong>
            {{
              policyEvaluation
                .deny_count ?? 0
            }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.requireApproval') }}
          </span>

          <strong>
            {{
              policyEvaluation
                .approval_count ??
              0
            }}
          </strong>
        </div>

        <div>
          <span>
            {{ t('interface.evaluatedRequests') }}
          </span>

          <strong>
            {{
              policyResults.length
            }}
          </strong>
        </div>
      </div>
    </section>

    <section
      v-if="
        policyResults.length
      "
      class="provenance-section"
    >
      <div
        class="provenance-section-heading"
      >
        <div>
          <span
            class="provenance-kicker"
          >
            {{ t('interface.decisionRecords') }}
          </span>

          <strong>
            {{ t('interface.perRequestPolicyResults') }}
          </strong>
        </div>
      </div>

      <div class="request-stack">
        <article
          v-for="result in policyResults"
          :key="
            result.request_index
          "
          class="evidence-card"
        >
          <div
            class="evidence-card-heading"
          >
            <div>
              <strong>
                {{ label(result
                    .tool_request
                    ?.tool_name ||
                  t('interface.unknownTool')) }}
              </strong>

              <small>
                {{ t('interface.request332') }}{{
                  result
                    .request_index
                }}
                ·
                {{
                  result
                    .tool_request
                    ?.target ||
                  t('interface.noTarget')
                }}
              </small>
            </div>

            <el-tag
              :type="
                decisionTagType(
                  result.decision,
                )
              "
            >
              {{ label(result.decision) }}
            </el-tag>
          </div>

          <div class="governance-note">
            <span>
              {{ t('interface.policyReason') }}
            </span>

            <p>
              {{
                result.reason ||
                t('interface.noPolicyReasonRecorded')
              }}
            </p>
          </div>

          <div
            class="governance-flags"
          >
            <span>
              {{ t('interface.humanApproval') }}
            </span>

            <strong>
              {{
                yesNoLabel(
                  result
                    .requires_human_approval,
                )
              }}
            </strong>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
  <template
    v-else-if="
      isApprovalEvent
    "
  >
    <div class="research-provenance">
      <section class="provenance-section">
        <div
          class="provenance-section-heading"
        >
          <div>
            <span
              class="provenance-kicker"
            >
              {{ t('interface.humanApproval335') }}
            </span>

            <strong>
              {{ t('interface.governanceCheckpoint') }}
            </strong>
          </div>

          <el-tag
            :type="
              approvalStatusTagType(
                approvalRecord
                  .status ||
                approvalRecord
                  .approval_status,
              )
            "
          >
            {{ label((
                approvalRecord
                  .status ||
                approvalRecord
                  .approval_status ||
                'unknown'
              ).toUpperCase()) }}
          </el-tag>
        </div>

        <div class="retrieval-grid">
          <div>
            <span>
              {{ t('interface.finding259') }}
            </span>

            <strong>
              #{{
                approvalRecord
                  .finding_id ||
                selectedRun
                  ?.finding_id ||
                '—'
              }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.requestIndex') }}
            </span>

            <strong>
              {{
                approvalRecord
                  .request_index ??
                '—'
              }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.reviewer') }}
            </span>

            <strong>
              {{
                approvalRecord
                  .reviewer ||
                '—'
              }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.tool') }}
            </span>

            <strong>
              {{ label(approvalToolRequest
                  ?.tool_name ||
                '—') }}
            </strong>
          </div>
        </div>

        <div class="governance-note">
          <span>
            {{ t('interface.policyReason') }}
          </span>

          <p>
            {{
              approvalRecord
                .policy_reason ||
              '—'
            }}
          </p>
        </div>

        <div
          v-if="
            approvalRecord
              .review_reason
          "
          class="governance-note"
        >
          <span>
            {{ t('interface.reviewReason') }}
          </span>

          <p>
            {{
              approvalRecord
                .review_reason
            }}
          </p>
        </div>
      </section>

      <section
        v-if="
          approvalToolRequest
        "
        class="provenance-section"
      >
        <div
          class="provenance-section-heading"
        >
          <div>
            <span
              class="provenance-kicker"
            >
              {{ t('interface.approvalSubject') }}
            </span>

            <strong>
              {{ t('interface.requestedToolAction') }}
            </strong>
          </div>
        </div>

        <article class="evidence-card">
          <div
            class="evidence-card-heading"
          >
            <div>
              <strong>
                {{ label(approvalToolRequest
                    .tool_name) }}
              </strong>

              <small>
                {{
                  approvalToolRequest
                    .target ||
                  t('interface.noTarget')
                }}
              </small>
            </div>
          </div>

          <div
            v-if="
              approvalToolRequest
                .reason
            "
            class="governance-note"
          >
            <span>
              {{ t('interface.requestReason') }}
            </span>

            <p>
              {{
                approvalToolRequest
                  .reason
              }}
            </p>
          </div>
        </article>
      </section>
    </div>
  </template>
  <template
    v-else-if="
      isToolExecutionEvent
    "
  >
    <div class="research-provenance">
      <section class="provenance-section">
        <div
          class="provenance-section-heading"
        >
          <div>
            <span
              class="provenance-kicker"
            >
              {{ t('interface.toolBroker344') }}
            </span>

            <strong>
              {{ t('interface.governedToolExecution') }}
            </strong>
          </div>

          <el-tag
            :type="
              executionStatusTagType(
                executionRecord
                  .status ||
                executionRecord
                  .broker_status,
              )
            "
          >
            {{ label((
                executionRecord
                  .status ||
                executionRecord
                  .broker_status ||
                'unknown'
              ).toUpperCase()) }}
          </el-tag>
        </div>

        <div class="retrieval-grid">
          <div>
            <span>
              {{ t('interface.tool') }}
            </span>

            <strong>
              {{ label(executionToolRequest
                  ?.tool_name ||
                selectedMetadata
                  .tool_name ||
                '—') }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.target') }}
            </span>

            <strong>
              {{
                executionToolRequest
                  ?.target ||
                selectedMetadata
                  .target ||
                '—'
              }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.policy346') }}
            </span>

            <strong>
              {{ label(executionRecord
                  .policy_decision ||
                '—') }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.authorized') }}
            </span>

            <strong>
              {{
                yesNoLabel(
                  executionRecord
                    .authorized,
                )
              }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.executed') }}
            </span>

            <strong>
              {{
                yesNoLabel(
                  executionRecord
                    .executed,
                )
              }}
            </strong>
          </div>

          <div>
            <span>
              {{ t('interface.dryRun349') }}
            </span>

            <strong>
              {{
                yesNoLabel(
                  executionRecord
                    .dry_run,
                )
              }}
            </strong>
          </div>
        </div>

        <div
          v-if="
            executionRecord.message
          "
          class="governance-note"
        >
          <span>
            {{ t('interface.brokerMessage') }}
          </span>

          <p>
            {{
              executionRecord
                .message
            }}
          </p>
        </div>
      </section>

      <section
        v-if="
          executionRecord.output &&
          Object.keys(
            executionRecord.output,
          ).length
        "
        class="provenance-section"
      >
        <div
          class="provenance-section-heading"
        >
          <div>
            <span
              class="provenance-kicker"
            >
              {{ t('interface.executionOutput') }}
            </span>

            <strong>
              {{ t('interface.toolResult') }}
            </strong>
          </div>
        </div>

        <pre class="mini-metadata">{{
          JSON.stringify(
            executionRecord.output,
            null,
            2,
          )
        }}</pre>
      </section>
    </div>
  </template>

            <template v-else>
              <div class="metadata-title">
                {{ t('interface.eventMetadata') }}
              </div>

              <pre class="metadata-block">{{
                JSON.stringify(
                  selectedEvent
                    .event_metadata,
                  null,
                  2,
                )
              }}</pre>
            </template>
            <el-collapse
  v-if="
    isStructuredAuditEvent
  "
  class="raw-metadata-collapse"
>
  <el-collapse-item
    name="raw-metadata"
  >
    <template #title>
      <span
        class="raw-metadata-title"
      >
        {{ t('interface.rawAuditMetadata') }}
      </span>
    </template>

    <pre class="metadata-block">{{
      JSON.stringify(
        selectedEvent
          .event_metadata,
        null,
        2,
      )
    }}</pre>
  </el-collapse-item>
</el-collapse>
          </template>
        </section>

        <section
          v-if="
            trace?.run
              ?.error_message
          "
          class="panel error-panel"
        >
          <span class="section-label">
            {{ t('interface.failureRecord') }}
          </span>

          <h3>
            {{ t('interface.investigationError') }}
          </h3>

          <pre>{{
            trace.run
              .error_message
          }}</pre>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.audit-page {
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

.eyebrow,
.section-label {
  color: #299dbc;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.3px;
}

.summary-grid {
  display: grid;
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card > span {
  display: block;
  color: #94a3b8;
  font-size: 10px;
}

.summary-card > strong {
  display: block;
  margin: 8px 0 5px;
  color: #26364a;
  font-size: 24px;
}

.summary-card small {
  color: #94a3b8;
  font-size: 9px;
}

.audit-workspace {
  display: grid;
  grid-template-columns:
    minmax(250px, 0.72fr)
    minmax(390px, 1.15fr)
    minmax(330px, 1fr);
  gap: 18px;
  align-items: start;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 15px;
}

.panel-heading h3 {
  margin: 3px 0 0;
  color: #334155;
  font-size: 15px;
}

.run-filters {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.run-list {
  display: flex;
  max-height: 720px;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

.run-item {
  width: 100%;
  padding: 12px;
  border: 1px solid #e7edf2;
  border-radius: 9px;
  outline: none;
  text-align: left;
  cursor: pointer;
  background: #fff;
}

.run-item:hover,
.run-item.active {
  border-color: #bcdce6;
  background: #f4fafc;
}

.run-item.failed {
  border-color: #f0cfd2;
}

.run-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.run-item-top strong {
  color: #334155;
  font-size: 11px;
}

.run-finding {
  margin-top: 6px;
  color: #6f7f91;
  font-size: 10px;
}

.run-verdict {
  margin-top: 4px;
  overflow: hidden;
  color: #526377;
  font-size: 10px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-footer {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 9px;
  color: #a0a9b6;
  font-size: 8px;
}

.run-overview {
  display: grid;
  grid-template-columns:
    repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.run-overview > div {
  padding: 10px;
  border: 1px solid #edf0f4;
  border-radius: 8px;
  background: #fafbfc;
}

.run-overview span,
.workflow-meta span,
.event-info span,
.event-summary > span {
  display: block;
  color: #94a3b8;
  font-size: 8px;
  text-transform: uppercase;
}

.run-overview strong {
  display: block;
  margin-top: 5px;
  color: #475569;
  font-size: 10px;
  word-break: break-word;
}

.event-filters {
  display: grid;
  grid-template-columns:
    minmax(130px, 1fr)
    135px
    120px;
  gap: 7px;
  margin-bottom: 15px;
}

.timeline {
  position: relative;
  display: flex;
  max-height: 620px;
  flex-direction: column;
  overflow-y: auto;
}

.timeline::before {
  position: absolute;
  top: 18px;
  bottom: 18px;
  left: 17px;
  width: 1px;
  content: "";
  background: #dce5ed;
}

.timeline-event {
  position: relative;
  z-index: 1;
  display: flex;
  width: 100%;
  gap: 11px;
  padding: 9px 7px;
  border: 0;
  border-radius: 8px;
  outline: none;
  text-align: left;
  cursor: pointer;
  background: transparent;
}

.timeline-event:hover,
.timeline-event.active {
  background: #f4f9fb;
}

.timeline-event.failed {
  background: #fff7f7;
}

.timeline-icon {
  display: flex;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  align-items: center;
  justify-content: center;
  border: 3px solid #fff;
  border-radius: 50%;
}

.category-investigation {
  color: #277e96;
  background: #ddf1f5;
}

.category-response {
  color: #546aa1;
  background: #e8edf8;
}

.category-governance {
  color: #9a751c;
  background: #fff3cf;
}

.category-execution {
  color: #39765b;
  background: #e2f3e9;
}

.category-system {
  color: #64748b;
  background: #e9edf2;
}

.timeline-main {
  min-width: 0;
  flex: 1;
  padding: 3px 0 8px;
}

.timeline-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.timeline-header strong {
  color: #334155;
  font-size: 11px;
}

.event-category {
  display: block;
  margin-top: 2px;
  color: #97a3b2;
  font-size: 8px;
}

.timeline-main p {
  margin: 5px 0;
  overflow: hidden;
  color: #718095;
  font-size: 9px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #a0aab7;
  font-size: 8px;
}

.detail-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.finding-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px;
  border: 1px solid #e6edf2;
  border-radius: 8px;
  background: #fafcfd;
}

.finding-card span {
  color: #299dbc;
  font-size: 9px;
}

.finding-card strong {
  color: #334155;
  font-size: 11px;
}

.finding-card small {
  color: #94a3b8;
}

.workflow-meta {
  display: grid;
  grid-template-columns:
    repeat(3, 1fr);
  gap: 7px;
  margin-top: 10px;
}

.workflow-meta div {
  padding: 9px;
  border: 1px solid #edf0f4;
  border-radius: 7px;
}

.workflow-meta strong {
  display: block;
  margin-top: 4px;
  color: #475569;
  font-size: 9px;
  word-break: break-word;
}

.navigation-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.navigation-actions .el-button {
  flex: 1;
}

.event-info {
  display: grid;
  grid-template-columns:
    repeat(2, 1fr);
  gap: 8px;
}

.event-info div {
  padding: 9px;
  border: 1px solid #edf0f4;
  border-radius: 7px;
  background: #fafbfc;
}

.event-info strong {
  display: block;
  margin-top: 4px;
  color: #475569;
  font-size: 9px;
  word-break: break-word;
}

.event-summary {
  margin-top: 13px;
}

.event-summary p {
  margin: 6px 0 0;
  color: #66778b;
  font-size: 10px;
  line-height: 1.7;
}

.metadata-title {
  margin: 16px 0 7px;
  color: #94a3b8;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.research-provenance {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.provenance-section {
  padding: 12px;
  border: 1px solid #e5edf3;
  border-radius: 9px;
  background: #fbfdfe;
}

.provenance-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 11px;
}

.provenance-section-heading > div {
  min-width: 0;
}

.provenance-section-heading strong {
  display: block;
  margin-top: 3px;
  color: #334155;
  font-size: 10px;
  line-height: 1.45;
}

.provenance-kicker {
  display: block;
  color: #299dbc;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 1px;
}

.retrieval-grid,
.intel-grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 7px;
}

.retrieval-grid > div,
.intel-grid > div {
  padding: 8px;
  border: 1px solid #edf0f4;
  border-radius: 7px;
  background: #fff;
}

.retrieval-grid span,
.intel-grid span,
.source-tags > span,
.provenance-query > span,
.provenance-index > span,
.evidence-fields span,
.intel-identifiers > div > span {
  display: block;
  color: #94a3b8;
  font-size: 7px;
  font-weight: 600;
  letter-spacing: 0.45px;
  text-transform: uppercase;
}

.retrieval-grid strong,
.intel-grid strong {
  display: block;
  margin-top: 4px;
  color: #475569;
  font-size: 9px;
  word-break: break-word;
}

.intel-grid small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
  font-size: 7px;
}

.source-tags,
.provenance-query,
.provenance-index {
  margin-top: 10px;
}

.source-tags > div,
.identifier-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 6px;
}

.query-block {
  max-height: 120px;
  margin-top: 6px;
  padding: 9px;
  overflow: auto;
  border: 1px solid #e8eef3;
  border-radius: 7px;
  color: #5e7085;
  font-size: 8px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  background: #fff;
}

.provenance-index code {
  display: block;
  margin-top: 6px;
  color: #526377;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  font-size: 8px;
  line-height: 1.5;
  word-break: break-all;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-card {
  padding: 10px;
  border: 1px solid #e4ebf1;
  border-radius: 8px;
  background: #fff;
}

.evidence-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.evidence-card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.evidence-card-heading > div {
  min-width: 0;
}

.evidence-card-heading strong {
  display: block;
  color: #334155;
  font-size: 10px;
  line-height: 1.5;
  word-break: break-word;
}

.evidence-card-heading small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
  font-size: 8px;
}

.evidence-number {
  display: flex;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #247e97;
  font-size: 8px;
  font-weight: 700;
  background: #ddf1f5;
}

.evidence-title {
  min-width: 0;
  flex: 1;
}

.evidence-title strong {
  display: block;
  color: #334155;
  font-size: 9px;
  line-height: 1.5;
  word-break: break-word;
}

.evidence-title span {
  display: block;
  margin-top: 3px;
  color: #8b98a8;
  font-size: 7px;
}

.evidence-badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 9px;
}

.score-pill {
  padding: 3px 7px;
  border-radius: 999px;
  color: #596b80;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  font-size: 7px;
  background: #edf2f6;
}

.evidence-fields {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin-top: 9px;
}

.evidence-fields > div {
  min-width: 0;
  padding: 7px;
  border-radius: 6px;
  background: #f8fafc;
}

.evidence-fields strong,
.evidence-fields code,
.evidence-fields a {
  display: block;
  margin-top: 4px;
  color: #4c6075;
  font-size: 8px;
  line-height: 1.5;
  word-break: break-word;
}

.evidence-fields code {
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  word-break: break-all;
}

.evidence-fields a {
  color: #258eaa;
  text-decoration: none;
}

.evidence-fields a:hover {
  text-decoration: underline;
}

.wide-field {
  grid-column: 1 / -1;
}

.intel-identifiers {
  display: grid;
  gap: 8px;
  margin-top: 9px;
}

.intel-identifiers > div {
  padding: 8px;
  border: 1px solid #edf0f4;
  border-radius: 7px;
  background: #fff;
}

.intel-identifiers strong {
  display: block;
  margin-top: 5px;
  color: #475569;
  font-size: 9px;
}

.raw-metadata-collapse {
  border-top: 0;
  border-bottom: 0;
}

.raw-metadata-title {
  color: #718095;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

:deep(.raw-metadata-collapse .el-collapse-item__header) {
  height: 34px;
  border-bottom: 0;
  color: #718095;
  background: transparent;
}

:deep(.raw-metadata-collapse .el-collapse-item__wrap) {
  border-bottom: 0;
  background: transparent;
}

:deep(.raw-metadata-collapse .el-collapse-item__content) {
  padding-bottom: 0;
}

.metadata-block,
.error-panel pre {
  max-height: 390px;
  margin: 0;
  padding: 13px;
  overflow: auto;
  border-radius: 8px;
  color: #cbd8e6;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  font-size: 9px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  background: #182332;
}

.error-panel {
  border-color: #f0cfd2;
}

.error-panel h3 {
  color: #9d3f4d;
  font-size: 13px;
}

@media (max-width: 1380px) {
  .audit-workspace {
    grid-template-columns:
      300px 1fr;
  }

  .detail-column {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns:
      repeat(2, 1fr);
  }
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns:
      repeat(2, 1fr);
  }

  .audit-workspace {
    grid-template-columns: 1fr;
  }

  .detail-column {
    grid-column: auto;
    display: flex;
  }

  .event-filters,
  .run-overview,
  .workflow-meta,
  .retrieval-grid,
  .intel-grid,
  .evidence-fields {
    grid-template-columns: 1fr;
  }

  .wide-field {
    grid-column: auto;
  }
}

  .plan-grid {
  display: grid;
  grid-template-columns:
    repeat(
      3,
      minmax(0, 1fr)
    );
  gap: 12px;
  margin-top: 16px;
}

.plan-card {
  min-width: 0;
  padding: 14px;
  border: 1px solid
    var(--el-border-color-lighter);
  border-radius: 10px;
  background:
    var(--el-fill-color-light);
}

.plan-card > span {
  display: block;
  margin-bottom: 10px;
  color:
    var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.plan-card ul {
  margin: 0;
  padding-left: 18px;
}

.plan-card li + li {
  margin-top: 6px;
}

.plan-card small {
  color:
    var(--el-text-color-secondary);
}

.request-stack {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}

.governance-note {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 8px;
  background:
    var(--el-fill-color-light);
}

.governance-note > span {
  display: block;
  margin-bottom: 6px;
  color:
    var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.governance-note p {
  margin: 0;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.governance-flags {
  display: flex;
  align-items: center;
  justify-content:
    space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid
    var(--el-border-color-lighter);
}

.governance-flags span {
  color:
    var(--el-text-color-secondary);
}

.mini-metadata {
  margin: 12px 0 0;
  padding: 12px;
  overflow: auto;
  border-radius: 8px;
  background:
    var(--el-fill-color);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@media (
  max-width: 1200px
) {
  .plan-grid {
    grid-template-columns:
      1fr;
  }
}
</style>
