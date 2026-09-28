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
  Cpu,
  Refresh,
  Search,
  WarningFilled,
  Check,
  Clock,
  Connection,
  Document,
} from '@element-plus/icons-vue'

import {
  getFinding,
  getInvestigationRun,
  getInvestigationTrace,
  startInvestigation,
} from '../../api'

const route = useRoute()
const router = useRouter()

const finding = ref(null)
const workflow = ref(null)
const trace = ref(null)

const findingIdInput = ref('')

const loadingFinding = ref(false)
const investigating = ref(false)
const loadingRun = ref(false)

const runIdInput = ref('')

const selectedEvent = ref(null)

const findingId = computed(() => {
  const value =
    finding.value?.id ||
    route.query.finding_id

  if (!value) {
    return null
  }

  return Number(value)
})

const events = computed(
  () => trace.value?.events || [],
)

const approvals = computed(
  () => workflow.value?.approvals || [],
)

const responsePlan = computed(
  () => workflow.value?.response_plan || null,
)

const policyEvaluation = computed(
  () =>
    workflow.value?.policy_evaluation ||
    null,
)

const workflowStatusLabel = computed(() => {
  const status =
    workflow.value?.workflow_status

  const labels = {
    failed: 'Failed',
    investigation_completed:
      'Investigation Completed',
    awaiting_approval:
      'Awaiting Approval',
    policy_blocked:
      'Policy Blocked',
    ready_for_execution:
      'Ready for Execution',
    dry_run_executed:
      'Dry-run Executed',
  }

  return labels[status] || status || '—'
})

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
  if (
    status === 'completed' ||
    status === 'dry_run_executed'
  ) {
    return 'success'
  }

  if (
    status === 'awaiting_approval' ||
    status === 'running'
  ) {
    return 'warning'
  }

  if (
    status === 'failed' ||
    status === 'policy_blocked'
  ) {
    return 'danger'
  }

  return 'info'
}

function verdictType(verdict) {
  if (
    verdict === 'likely_true_positive'
  ) {
    return 'danger'
  }

  if (
    verdict === 'likely_false_positive'
  ) {
    return 'success'
  }

  if (
    verdict === 'informational'
  ) {
    return 'info'
  }

  return 'warning'
}

function eventLabel(event) {
  const type = event?.event_type

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
      'Human Approval',

    approval_resolved:
      'Approval Review',

    tool_execution_simulated:
      'Tool Broker',

    investigation_failed:
      'Investigation Failed',
  }

  return (
    labels[type] ||
    event?.node_name ||
    type ||
    'Agent Event'
  )
}

function eventIcon(event) {
  const type =
    event?.event_type || ''

  if (
    type.includes('ground') ||
    type.includes('evidence')
  ) {
    return Check
  }

  if (
    type.includes('research') ||
    type.includes('context')
  ) {
    return Connection
  }

  if (
    type.includes('policy') ||
    type.includes('approval')
  ) {
    return WarningFilled
  }

  if (
    type.includes('response') ||
    type.includes('tool')
  ) {
    return Cpu
  }

  return Document
}

function eventStatusClass(status) {
  return `event-${status || 'unknown'}`
}

async function loadFinding(id) {
  if (!id) {
    return
  }

  loadingFinding.value = true

  try {
    finding.value =
      await getFinding(id, {
        silent: true,
      })

    findingIdInput.value =
      String(id)
  } catch (error) {
    console.error(error)

    ElMessage.error(
      'Finding 加载失败',
    )
  } finally {
    loadingFinding.value = false
  }
}

async function loadTrace(runId) {
  try {
    trace.value =
      await getInvestigationTrace(
        runId,
        {
          silent: true,
        },
      )

    if (
      trace.value?.events?.length
    ) {
      selectedEvent.value =
        trace.value.events[
          trace.value.events.length - 1
        ]
    }
  } catch (error) {
    console.error(error)

    ElMessage.error(
      'Investigation Trace 加载失败',
    )
  }
}

async function loadRun(runId) {
  if (!runId) {
    return
  }

  loadingRun.value = true

  try {
    workflow.value =
      await getInvestigationRun(
        runId,
        {
          silent: true,
        },
      )

    runIdInput.value =
      String(runId)

    await loadTrace(runId)

    if (
      workflow.value?.finding_id &&
      !finding.value
    ) {
      await loadFinding(
        workflow.value.finding_id,
      )
    }
  } catch (error) {
    console.error(error)

    ElMessage.error(
      'Investigation Run 加载失败',
    )
  } finally {
    loadingRun.value = false
  }
}

async function investigate() {
  const id = Number(
    findingId.value ||
    findingIdInput.value,
  )

  if (!id) {
    ElMessage.warning(
      '请先选择 Finding',
    )

    return
  }

  investigating.value = true

  try {
    ElMessage.info(
      'Agent Investigation 已启动，本地模型分析可能需要一些时间',
    )

    workflow.value =
      await startInvestigation(
        id,
        {
          timeout: 600000,
        },
      )

    runIdInput.value =
      String(
        workflow.value.run_id,
      )

    await loadTrace(
      workflow.value.run_id,
    )

    await router.replace({
      name: 'investigations',

      query: {
        finding_id: id,
        run_id:
          workflow.value.run_id,
      },
    })

    ElMessage.success(
      `Investigation Run #${workflow.value.run_id} 已完成`,
    )
  } catch (error) {
    console.error(error)
  } finally {
    investigating.value = false
  }
}

async function searchFinding() {
  const id =
    Number(findingIdInput.value)

  if (!id) {
    ElMessage.warning(
      '请输入有效 Finding ID',
    )

    return
  }

  workflow.value = null
  trace.value = null
  selectedEvent.value = null

  await loadFinding(id)

  await router.replace({
    name: 'investigations',

    query: {
      finding_id: id,
    },
  })
}

async function searchRun() {
  const id =
    Number(runIdInput.value)

  if (!id) {
    ElMessage.warning(
      '请输入有效 Run ID',
    )

    return
  }

  await loadRun(id)

  await router.replace({
    name: 'investigations',

    query: {
      finding_id:
        workflow.value?.finding_id ||
        finding.value?.id,
      run_id: id,
    },
  })
}

async function refreshCurrentRun() {
  if (!workflow.value?.run_id) {
    return
  }

  await loadRun(
    workflow.value.run_id,
  )
}

onMounted(async () => {
  const queryFinding =
    Number(
      route.query.finding_id,
    )

  const queryRun =
    Number(
      route.query.run_id,
    )

  if (queryFinding) {
    await loadFinding(
      queryFinding,
    )
  }

  if (queryRun) {
    await loadRun(
      queryRun,
    )
  }
})
</script>

<template>
  <div class="investigations-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">
          AGENT INVESTIGATION
        </div>

        <h2>
          AI Investigation Center
        </h2>

        <p>
          LangGraph 驱动的安全调查、证据验证与响应决策工作台
        </p>
      </div>

      <el-button
        v-if="workflow"
        :icon="Refresh"
        :loading="loadingRun"
        @click="refreshCurrentRun"
      >
        刷新 Run
      </el-button>
    </div>

    <section class="panel control-panel">
      <div class="control-block">
        <label>
          Finding ID
        </label>

        <div class="control-row">
          <el-input
            v-model="findingIdInput"
            placeholder="例如 62"
            @keyup.enter="searchFinding"
          />

          <el-button
            :icon="Search"
            @click="searchFinding"
          >
            加载 Finding
          </el-button>
        </div>
      </div>

      <div class="control-divider"></div>

      <div class="control-block">
        <label>
          Existing Run ID
        </label>

        <div class="control-row">
          <el-input
            v-model="runIdInput"
            placeholder="例如 30"
            @keyup.enter="searchRun"
          />

          <el-button
            :icon="Search"
            @click="searchRun"
          >
            恢复 Run
          </el-button>
        </div>
      </div>
    </section>

    <section
      v-if="finding"
      class="panel finding-context"
      v-loading="loadingFinding"
    >
      <div class="finding-context-main">
        <div class="finding-id">
          FINDING #{{ finding.id }}
        </div>

        <h3>
          {{ finding.title }}
        </h3>

        <div class="finding-tags">
          <el-tag
            effect="plain"
          >
            {{ finding.source }}
          </el-tag>

          <el-tag
            type="info"
            effect="plain"
          >
            {{ finding.severity }}
          </el-tag>

          <el-tag
            :type="
              finding.risk_level === 'high' ||
              finding.risk_level === 'critical'
                ? 'danger'
                : finding.risk_level === 'medium'
                  ? 'warning'
                  : 'success'
            "
          >
            Risk:
            {{ finding.risk_level }}
          </el-tag>

          <span class="finding-target">
            {{ finding.target }}
          </span>
        </div>
      </div>

      <el-button
        type="primary"
        :icon="Cpu"
        :loading="investigating"
        @click="investigate"
      >
        {{
          investigating
            ? 'Agent 调查中...'
            : '启动 AI Investigation'
        }}
      </el-button>
    </section>

    <template v-if="workflow">
      <div class="summary-grid">
        <section class="panel summary-card">
          <span>
            Run ID
          </span>

          <strong>
            #{{ workflow.run_id }}
          </strong>

          <small>
            Finding
            #{{ workflow.finding_id }}
          </small>
        </section>

        <section class="panel summary-card">
          <span>
            Workflow Status
          </span>

          <strong class="summary-text">
            {{ workflowStatusLabel }}
          </strong>

          <el-tag
            :type="
              statusType(
                workflow.workflow_status,
              )
            "
          >
            {{ workflow.workflow_status }}
          </el-tag>
        </section>

        <section class="panel summary-card">
          <span>
            Final Verdict
          </span>

          <strong class="summary-text">
            {{
              workflow.final_verdict ||
              '—'
            }}
          </strong>

          <el-tag
            :type="
              verdictType(
                workflow.final_verdict,
              )
            "
          >
            {{
              workflow.final_verdict ||
              'unknown'
            }}
          </el-tag>
        </section>

        <section class="panel summary-card">
          <span>
            Ledger Events
          </span>

          <strong>
            {{ workflow.event_count }}
          </strong>

          <small>
            Audit Trace
          </small>
        </section>
      </div>

      <div class="workspace-grid">
        <section class="panel trace-panel">
          <div class="panel-heading">
            <div>
              <h3>
                Agent Trace
              </h3>

              <p>
                Investigation Ledger
              </p>
            </div>

            <el-tag
              type="info"
              effect="plain"
            >
              {{ events.length }} events
            </el-tag>
          </div>

          <div
            v-if="events.length"
            class="timeline"
          >
            <button
              v-for="event in events"
              :key="event.id"
              type="button"
              class="timeline-item"
              :class="{
                active:
                  selectedEvent?.id ===
                  event.id,
              }"
              @click="
                selectedEvent = event
              "
            >
              <div
                class="timeline-dot"
                :class="
                  eventStatusClass(
                    event.status,
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

              <div class="timeline-content">
                <div class="timeline-top">
                  <strong>
                    {{ eventLabel(event) }}
                  </strong>

                  <span>
                    {{ event.status }}
                  </span>
                </div>

                <p>
                  {{
                    event.summary ||
                    event.event_type
                  }}
                </p>

                <small>
                  {{
                    formatDate(
                      event.created_at,
                    )
                  }}
                </small>
              </div>
            </button>
          </div>

          <el-empty
            v-else
            description="暂无 Trace Events"
          />
        </section>

        <div class="detail-column">
          <section
            v-if="selectedEvent"
            class="panel event-detail"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  LEDGER EVENT
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
                  statusType(
                    selectedEvent.status,
                  )
                "
              >
                {{
                  selectedEvent.status
                }}
              </el-tag>
            </div>

            <dl class="event-metadata">
              <div>
                <dt>
                  Event Type
                </dt>

                <dd>
                  {{
                    selectedEvent.event_type
                  }}
                </dd>
              </div>

              <div>
                <dt>
                  Node
                </dt>

                <dd>
                  {{
                    selectedEvent.node_name ||
                    '—'
                  }}
                </dd>
              </div>

              <div>
                <dt>
                  Created
                </dt>

                <dd>
                  {{
                    formatDate(
                      selectedEvent.created_at,
                    )
                  }}
                </dd>
              </div>
            </dl>

            <div class="event-summary">
              {{
                selectedEvent.summary ||
                'No event summary.'
              }}
            </div>

            <div
              v-if="
                selectedEvent.event_metadata
              "
              class="raw-heading"
            >
              Event Metadata
            </div>

            <pre
              v-if="
                selectedEvent.event_metadata
              "
              class="metadata-block"
            >{{
              JSON.stringify(
                selectedEvent.event_metadata,
                null,
                2,
              )
            }}</pre>
          </section>

          <section
            v-if="responsePlan"
            class="panel"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  RESPONSE AGENT
                </span>

                <h3>
                  Response Plan
                </h3>
              </div>

              <el-tag
                :type="
                  responsePlan.requires_human_review
                    ? 'warning'
                    : 'success'
                "
              >
                {{
                  responsePlan.requires_human_review
                    ? 'Human Review'
                    : 'Auto'
                }}
              </el-tag>
            </div>

            <div class="response-action">
              <span>
                Decision
              </span>

              <strong>
                {{
                  responsePlan.decision_action
                }}
              </strong>
            </div>

            <p class="response-summary">
              {{ responsePlan.summary }}
            </p>

            <div class="response-tags">
              <el-tag effect="plain">
                Priority:
                {{ responsePlan.priority }}
              </el-tag>

              <el-tag
                type="info"
                effect="plain"
              >
                Dry-run:
                {{ responsePlan.dry_run }}
              </el-tag>
            </div>
          </section>

          <section
            v-if="policyEvaluation"
            class="panel"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  POLICY ENGINE
                </span>

                <h3>
                  Policy Decision
                </h3>
              </div>
            </div>

            <div class="policy-counts">
              <div>
                <span>
                  ALLOW
                </span>

                <strong>
                  {{
                    policyEvaluation.allow_count
                  }}
                </strong>
              </div>

              <div>
                <span>
                  DENY
                </span>

                <strong>
                  {{
                    policyEvaluation.deny_count
                  }}
                </strong>
              </div>

              <div>
                <span>
                  APPROVAL
                </span>

                <strong>
                  {{
                    policyEvaluation.approval_count
                  }}
                </strong>
              </div>
            </div>
          </section>

          <section
            v-if="approvals.length"
            class="panel approval-card"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  HUMAN IN THE LOOP
                </span>

                <h3>
                  Pending Approval
                </h3>
              </div>

              <el-tag
                type="warning"
              >
                {{
                  approvals[0].status
                }}
              </el-tag>
            </div>

            <p>
              {{
                approvals[0]
                  .policy_reason
              }}
            </p>

            <small>
              Day32 将在 Response Center
              接入 Approve / Reject /
              Tool Broker。
            </small>
          </section>
        </div>
      </div>
    </template>

    <section
      v-else-if="!finding"
      class="panel empty-state"
    >
      <el-empty
        description="从 Findings 页面选择一个安全发现开始 AI Investigation"
      >
        <el-button
          type="primary"
          @click="
            router.push({
              name: 'findings',
            })
          "
        >
          前往 Findings
        </el-button>
      </el-empty>
    </section>
  </div>
</template>

<style scoped>
.investigations-page {
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

.control-panel {
  display: flex;
  align-items: flex-end;
  gap: 24px;
}

.control-block {
  flex: 1;
}

.control-block label {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
}

.control-row {
  display: flex;
  gap: 8px;
}

.control-divider {
  width: 1px;
  height: 58px;
  background: #edf0f4;
}

.finding-context {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.finding-context-main {
  min-width: 0;
}

.finding-id {
  color: #299dbc;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
}

.finding-context h3 {
  margin: 6px 0 10px;
  color: #334155;
  font-size: 19px;
}

.finding-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.finding-target {
  color: #7b899b;
  font-size: 11px;
}

.summary-grid {
  display: grid;
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card span {
  display: block;
  color: #94a3b8;
  font-size: 10px;
}

.summary-card > strong {
  display: block;
  margin: 8px 0 6px;
  color: #26364a;
  font-size: 23px;
}

.summary-card .summary-text {
  font-size: 14px;
  line-height: 1.5;
}

.summary-card small {
  color: #94a3b8;
}

.workspace-grid {
  display: grid;
  grid-template-columns:
    minmax(350px, 0.85fr)
    minmax(0, 1.4fr);
  gap: 18px;
  align-items: start;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-heading h3 {
  margin: 3px 0 0;
  color: #334155;
  font-size: 15px;
}

.panel-heading p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 10px;
}

.timeline {
  position: relative;
}

.timeline::before {
  position: absolute;
  top: 18px;
  bottom: 18px;
  left: 18px;
  width: 1px;
  content: "";
  background: #dce5ed;
}

.timeline-item {
  position: relative;
  display: flex;
  width: 100%;
  gap: 13px;
  padding: 10px 8px;
  border: 0;
  border-radius: 9px;
  outline: none;
  text-align: left;
  cursor: pointer;
  background: transparent;
}

.timeline-item:hover,
.timeline-item.active {
  background: #f4f9fb;
}

.timeline-dot {
  z-index: 1;
  display: flex;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  align-items: center;
  justify-content: center;
  border: 3px solid #fff;
  border-radius: 50%;
  color: #64748b;
  background: #e8edf2;
}

.timeline-dot.event-completed {
  color: #25839e;
  background: #dff3f8;
}

.timeline-dot.event-failed {
  color: #c2414e;
  background: #feecef;
}

.timeline-dot.event-started {
  color: #ad8510;
  background: #fff4cd;
}

.timeline-content {
  min-width: 0;
  flex: 1;
  padding: 4px 0 8px;
}

.timeline-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.timeline-top strong {
  color: #334155;
  font-size: 12px;
}

.timeline-top span {
  color: #8b98a8;
  font-size: 9px;
  text-transform: uppercase;
}

.timeline-content p {
  margin: 5px 0;
  overflow: hidden;
  color: #708094;
  font-size: 10px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-content small {
  color: #a1aab8;
  font-size: 9px;
}

.detail-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.event-metadata {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.event-metadata div {
  padding: 11px;
  border: 1px solid #edf0f4;
  border-radius: 8px;
  background: #fafbfc;
}

.event-metadata dt {
  color: #94a3b8;
  font-size: 9px;
}

.event-metadata dd {
  margin: 5px 0 0;
  color: #334155;
  font-size: 11px;
  word-break: break-word;
}

.event-summary {
  margin-top: 14px;
  color: #617185;
  font-size: 11px;
  line-height: 1.7;
}

.raw-heading {
  margin: 18px 0 8px;
  color: #94a3b8;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.metadata-block {
  max-height: 380px;
  margin: 0;
  padding: 15px;
  overflow: auto;
  border: 1px solid #26384d;
  border-radius: 9px;
  color: #cbd8e6;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  font-size: 10px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  background: #182332;
}

.response-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px;
  border-radius: 9px;
  background: #f8fafc;
}

.response-action span {
  color: #94a3b8;
  font-size: 10px;
}

.response-action strong {
  color: #334155;
  font-size: 12px;
}

.response-summary {
  margin: 14px 0;
  color: #64748b;
  font-size: 11px;
  line-height: 1.7;
}

.response-tags {
  display: flex;
  gap: 8px;
}

.policy-counts {
  display: grid;
  grid-template-columns:
    repeat(3, 1fr);
  gap: 10px;
}

.policy-counts div {
  padding: 13px;
  border: 1px solid #edf0f4;
  border-radius: 9px;
  text-align: center;
}

.policy-counts span {
  display: block;
  color: #94a3b8;
  font-size: 9px;
}

.policy-counts strong {
  display: block;
  margin-top: 6px;
  color: #334155;
  font-size: 20px;
}

.approval-card {
  border-color: #f3dfac;
  background:
    linear-gradient(
      135deg,
      #fffdf7,
      #fffaf0
    );
}

.approval-card p {
  color: #64748b;
  font-size: 11px;
  line-height: 1.7;
}

.approval-card small {
  color: #a28655;
}

.empty-state {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 1100px) {
  .summary-grid {
    grid-template-columns:
      repeat(2, 1fr);
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .page-heading,
  .finding-context {
    flex-direction: column;
  }

  .control-panel {
    flex-direction: column;
    align-items: stretch;
  }

  .control-divider {
    display: none;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .event-metadata {
    grid-template-columns: 1fr;
  }
}
</style>