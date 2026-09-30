<script setup>
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
      return `${seconds}s`
    }

    const minutes =
      Math.floor(
        seconds / 60,
      )

    const remain =
      seconds % 60

    return `${minutes}m ${remain}s`
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
      'Canonical Exact',
    relationship:
      'Relationship',
    semantic:
      'Semantic',
  }

  return (
    labels[value] ||
    value ||
    'Unknown'
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
    return 'Matched'
  }

  if (value === false) {
    return 'No match'
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

  return date.toLocaleString()
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

  return date.toLocaleTimeString()
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
      'Investigation',

    response:
      'Response',

    governance:
      'Governance',

    execution:
      'Execution',

    system:
      'System',
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
      'Context Builder',

    triage_completed:
      'Triage',

    research_completed:
      'Research · RAG / Intel',

    evidence_assessed:
      'Evidence Assessment',

    risk_enriched:
      'Risk Synthesis',

    grounding_validated:
      'Grounding Validator',

    response_planned:
      'Response Agent',

    policy_evaluated:
      'Policy Engine',

    approval_requested:
      'Approval Requested',

    approval_resolved:
      'Approval Resolved',

    tool_execution_simulated:
      'Tool Broker · Simulated',

    tool_execution_completed:
      'Tool Broker',

    tool_execution_failed:
      'Tool Broker Failed',
  }

  return (
    labels[
      event?.event_type
    ] ||
    event?.node_name ||
    event?.event_type ||
    'Audit Event'
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
      'Investigation Runs 加载失败',
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
      'Audit Trace 加载失败',
    )
  } finally {
    loadingTrace.value = false
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
          INVESTIGATION LEDGER
        </div>

        <h2>
          Audit Center
        </h2>

        <p>
          Agent 调查、治理审批与
          Tool Broker 的全链路审计追踪
        </p>
      </div>

      <el-button
        :icon="Refresh"
        :loading="loadingRuns"
        @click="refreshAll"
      >
        刷新审计数据
      </el-button>
    </div>

    <div class="summary-grid">
      <section class="panel summary-card">
        <span>
          Investigation Runs
        </span>

        <strong>
          {{ runStats.total }}
        </strong>

        <small>
          Ledger records
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          Completed
        </span>

        <strong>
          {{ runStats.completed }}
        </strong>

        <small>
          Completed runs
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          Failed
        </span>

        <strong>
          {{ runStats.failed }}
        </strong>

        <small>
          Failed runs
        </small>
      </section>

      <section class="panel summary-card">
        <span>
          Audit Events
        </span>

        <strong>
          {{ runStats.events }}
        </strong>

        <small>
          Recorded events
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
              RUN QUEUE
            </span>

            <h3>
              Investigation Runs
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
            placeholder="Run / Finding / Verdict"
          />

          <el-select
            v-model="
              runStatusFilter
            "
            clearable
            placeholder="Run Status"
          >
            <el-option
              label="Completed"
              value="completed"
            />

            <el-option
              label="Running"
              value="running"
            />

            <el-option
              label="Failed"
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
                Run #{{ run.id }}
              </strong>

              <el-tag
                size="small"
                :type="
                  runStatusType(
                    run.status,
                  )
                "
              >
                {{ run.status }}
              </el-tag>
            </div>

            <div class="run-finding">
              Finding
              #{{ run.finding_id }}
            </div>

            <div class="run-verdict">
              {{
                run.final_verdict ||
                'No verdict'
              }}
            </div>

            <div class="run-footer">
              <span>
                {{
                  run.event_count
                }}
                events
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
          description="No matching runs"
        />
      </section>

      <section
        class="panel timeline-panel"
        v-loading="loadingTrace"
      >
        <div class="panel-heading">
          <div>
            <span class="section-label">
              AUDIT TIMELINE
            </span>

            <h3>
              {{
                selectedRun
                  ? `Run #${selectedRun.id}`
                  : 'Select Run'
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
            events
          </el-tag>
        </div>

        <template v-if="trace">
          <div class="run-overview">
            <div>
              <span>
                Finding
              </span>

              <strong>
                #{{ trace.run.finding_id }}
              </strong>
            </div>

            <div>
              <span>
                Final Verdict
              </span>

              <strong>
                {{
                  trace.run
                    .final_verdict ||
                  '—'
                }}
              </strong>
            </div>

            <div>
              <span>
                Duration
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
              placeholder="Search events"
            />

            <el-select
              v-model="
                eventCategoryFilter
              "
              clearable
              placeholder="Category"
            >
              <el-option
                label="Investigation"
                value="investigation"
              />

              <el-option
                label="Response"
                value="response"
              />

              <el-option
                label="Governance"
                value="governance"
              />

              <el-option
                label="Execution"
                value="execution"
              />
            </el-select>

            <el-select
              v-model="
                eventStatusFilter
              "
              clearable
              placeholder="Status"
            >
              <el-option
                label="Completed"
                value="completed"
              />

              <el-option
                label="Started"
                value="started"
              />

              <el-option
                label="Failed"
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
                    {{
                      event.status
                    }}
                  </el-tag>
                </div>

                <p>
                  {{
                    event.summary ||
                    event.event_type
                  }}
                </p>

                <div class="timeline-meta">
                  <span>
                    {{
                      event.node_name ||
                      'system'
                    }}
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
            description="No matching events"
          />
        </template>

        <el-empty
          v-else
          description="Select an Investigation Run"
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
                WORKFLOW STATE
              </span>

              <h3>
                Run Summary
              </h3>
            </div>

            <el-tag
              :type="
                runStatusType(
                  trace?.run?.status,
                )
              "
            >
              {{
                workflow
                  .workflow_status
              }}
            </el-tag>
          </div>

          <div
            v-if="finding"
            class="finding-card"
          >
            <span>
              Finding
              #{{ finding.id }}
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
                Verdict
              </span>

              <strong>
                {{
                  workflow
                    .final_verdict ||
                  '—'
                }}
              </strong>
            </div>

            <div>
              <span>
                Ledger Events
              </span>

              <strong>
                {{ events.length }}
              </strong>
            </div>

            <div>
              <span>
                Tool Results
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
              Investigation
            </el-button>

            <el-button
              type="primary"
              plain
              @click="goResponse"
            >
              Response
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
                EVENT INSPECTOR
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
              {{
                selectedEvent.status
              }}
            </el-tag>
          </div>

          <div class="event-info">
            <div>
              <span>
                Event Type
              </span>

              <strong>
                {{
                  selectedEvent
                    .event_type
                }}
              </strong>
            </div>

            <div>
              <span>
                Node
              </span>

              <strong>
                {{
                  selectedEvent
                    .node_name ||
                  '—'
                }}
              </strong>
            </div>

            <div>
              <span>
                Category
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
                Created At
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
              Summary
            </span>

            <p>
              {{
                selectedEvent.summary ||
                'No summary recorded.'
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
                        RAG RETRIEVAL
                      </span>

                      <strong>
                        Security Knowledge Search
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
                      <span>Top K</span>
                      <strong>
                        {{
                          researchMetadata
                            .top_k ?? '—'
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>Retrieved</span>
                      <strong>
                        {{
                          researchMetadata
                            .retrieved_count ??
                          researchEvidence.length
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>RAG Used</span>
                      <strong>
                        {{
                          researchMetadata
                            .rag_used
                            ? 'Yes'
                            : 'No'
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>Intel Used</span>
                      <strong>
                        {{
                          researchMetadata
                            .intelligence_used
                            ? 'Yes'
                            : 'No'
                        }}
                      </strong>
                    </div>
                  </div>

                  <div
                    v-if="researchSources.length"
                    class="source-tags"
                  >
                    <span>Sources</span>

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
                    <span>Query</span>

                    <div class="query-block">
                      {{
                        researchMetadata
                          .rag_query ||
                        'No RAG query recorded.'
                      }}
                    </div>
                  </div>

                  <div class="provenance-index">
                    <span>Index</span>
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
                        RETRIEVED EVIDENCE
                      </span>

                      <strong>
                        Auditable Knowledge Evidence
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
                              'Knowledge Evidence'
                            }}
                          </strong>

                          <span>
                            {{
                              evidence.source ||
                              'Unknown source'
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
                          score
                          {{
                            formatScore(
                              evidence.score,
                            )
                          }}
                        </span>
                      </div>

                      <div class="evidence-fields">
                        <div>
                          <span>Source ID</span>
                          <strong>
                            {{
                              evidence.source_id ||
                              '—'
                            }}
                          </strong>
                        </div>

                        <div>
                          <span>Chunk</span>
                          <strong>
                            {{
                              evidence.chunk_index ??
                              '—'
                            }}
                          </strong>
                        </div>

                        <div class="wide-field">
                          <span>Document ID</span>
                          <code>
                            {{
                              evidence.document_id ||
                              '—'
                            }}
                          </code>
                        </div>

                        <div class="wide-field">
                          <span>Parent ID</span>
                          <code>
                            {{
                              evidence.parent_id ||
                              '—'
                            }}
                          </code>
                        </div>

                        <div class="wide-field">
                          <span>Source URL</span>

                          <a
                            v-if="evidence.source_url"
                            :href="evidence.source_url"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Open authoritative source ↗
                          </a>

                          <strong v-else>
                            —
                          </strong>
                        </div>

                        <div class="wide-field">
                          <span>Content SHA-256</span>
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
                    description="No provenance evidence recorded for this run"
                  />
                </section>

                <section
                  v-if="researchIntelligence"
                  class="provenance-section"
                >
                  <div class="provenance-section-heading">
                    <div>
                      <span class="provenance-kicker">
                        STRUCTURED INTELLIGENCE
                      </span>

                      <strong>
                        Threat Intelligence Signals
                      </strong>
                    </div>
                  </div>

                  <div class="intel-grid">
                    <div>
                      <span>Template</span>
                      <strong>
                        {{
                          researchIntelligence
                            .template_id ||
                          '—'
                        }}
                      </strong>
                    </div>

                    <div>
                      <span>CISA KEV</span>
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
                        }} record(s)
                      </small>
                    </div>

                    <div>
                      <span>NVD</span>
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
                        }} record(s)
                      </small>
                    </div>
                  </div>

                  <div class="intel-identifiers">
                    <div>
                      <span>CVE IDs</span>

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
                      <span>CWE IDs</span>

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

                <el-collapse class="raw-metadata-collapse">
                  <el-collapse-item name="raw-metadata">
                    <template #title>
                      <span class="raw-metadata-title">
                        Raw Audit Metadata
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
              </div>
            </template>

            <template v-else>
              <div class="metadata-title">
                Event Metadata
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
            FAILURE RECORD
          </span>

          <h3>
            Investigation Error
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
</style>
