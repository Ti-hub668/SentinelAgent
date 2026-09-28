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
  .workflow-meta {
    grid-template-columns: 1fr;
  }
}
</style>