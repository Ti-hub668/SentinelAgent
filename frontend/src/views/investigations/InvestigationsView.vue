<script setup>
import {
  computed,
  onBeforeUnmount,
  watch,
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
const polling = ref(false)
const pollError = ref('')
const lastUpdated = ref(null)
let generation = 0
let controller = null
let pollTimer = null

const runStatus = computed(() => workflow.value?.run_status || trace.value?.run?.status)
const busy = computed(() => investigating.value || polling.value || runStatus.value === 'running')
const failureMessage = computed(() => trace.value?.run?.error_message ||
  events.value.findLast(event => event.status === 'failed')?.summary || '调查执行失败，请查看审计事件。')

function validId(value) {
  return /^\d+$/.test(String(value)) && Number.isSafeInteger(Number(value)) && Number(value) > 0
}

// Run completion precedes the response pipeline in the existing backend.
// Wait for policy and all requested approvals before stopping the live view.
function isSettled(run) {
  if (run.run_status === 'failed') return true
  if (run.run_status !== 'completed' || !run.policy_evaluation) return false
  return (run.approvals?.length || 0) >= (run.policy_evaluation.approval_count || 0)
}

function cancelRequests() {
  generation += 1
  clearTimeout(pollTimer)
  controller?.abort()
  controller = new AbortController()
  polling.value = false
  investigating.value = false
  loadingFinding.value = false
  loadingRun.value = false
  return generation
}

function clearRun() {
  workflow.value = null
  trace.value = null
  selectedEvent.value = null
  runIdInput.value = ''
  pollError.value = ''
  lastUpdated.value = null
}

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
    running: 'Running',
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

    tool_execution_executed:
      'Tool Broker · Executed',

    tool_execution_replayed:
      'Tool Broker · Replay',

    tool_execution_blocked:
      'Tool Broker · Blocked',

    tool_execution_failed:
      'Tool Broker · Failed',

    tool_reconciliation_started:
      'Reconciliation Started',

    tool_reconciliation_confirmed:
      'Reconciliation Confirmed',

    tool_reconciliation_unresolved:
      'Reconciliation Unresolved',

    tool_reconciliation_failed:
      'Reconciliation Failed',

    investigation_failed: 'Investigation Failed',
    workflow_failed: 'Workflow Failed',
    stale_run_recovered: 'Stale Run Recovered',
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

async function loadFinding(id, token = generation) {
  loadingFinding.value = true
  try {
    const result = await getFinding(id, { silent: true, signal: controller.signal })
    if (token !== generation) return
    finding.value = result
    findingIdInput.value = String(id)
  } catch (error) {
    if (token === generation) ElMessage.error('Finding 加载失败，请重新加载')
  } finally {
    if (token === generation) loadingFinding.value = false
  }
}

async function pollRun(runId, token, failures = 0) {
  if (token !== generation) return
  loadingRun.value = true
  polling.value = true
  let retry = true
  let nextFailures = 0
  try {
    const config = { silent: true, signal: controller.signal }
    const result = await getInvestigationRun(runId, config)
    if (token !== generation) return
    workflow.value = result
    // Fetch trace after the summary so a terminal summary has its final events.
    const latestTrace = await getInvestigationTrace(runId, config)
    if (token !== generation) return
    trace.value = latestTrace
    selectedEvent.value = latestTrace.events.find(event => event.id === selectedEvent.value?.id)
      || latestTrace.events.at(-1) || null
    lastUpdated.value = new Date().toISOString()
    pollError.value = ''
    retry = !isSettled(result)
    if (finding.value?.id !== result.finding_id) {
      finding.value = null
      await loadFinding(result.finding_id, token)
    }
  } catch (error) {
    if (token !== generation) return
    nextFailures = failures + 1
    retry = nextFailures < 3 && ![401, 403, 404].includes(error.response?.status)
    pollError.value = retry
      ? '进度获取失败，正在自动重试；后台任务不会因此停止。'
      : '进度刷新已暂停，请点击刷新 Run 重试；这不代表后台任务失败。'
  } finally {
    if (token === generation) {
      loadingRun.value = false
      polling.value = retry
      if (retry) pollTimer = setTimeout(() => pollRun(runId, token, nextFailures), 2500)
    }
  }
}

async function loadRun(runId) {
  if (!validId(runId)) return
  const token = cancelRequests()
  if (workflow.value?.run_id !== Number(runId)) {
    clearRun()
    finding.value = null
  }
  runIdInput.value = String(runId)
  await pollRun(Number(runId), token)
}

async function investigate() {
  if (busy.value || loadingFinding.value) return
  const id = finding.value?.id
  if (!validId(id)) {
    ElMessage.warning('请先加载有效 Finding')
    return
  }
  const token = cancelRequests()
  clearRun()
  investigating.value = true
  try {
    const started = await startInvestigation(id, { signal: controller.signal })
    if (token !== generation) return
    workflow.value = started
    runIdInput.value = String(started.run_id)
    ElMessage.success('Investigation Run #' + started.run_id + ' 已启动')
    await router.replace({ name: 'investigations', query: { finding_id: id, run_id: started.run_id } })
  } catch (error) {
    // The shared request interceptor displays submission errors.
    if (token === generation) console.error(error)
  } finally {
    if (token === generation) investigating.value = false
  }
}

async function searchFinding() {
  if (!validId(findingIdInput.value)) {
    ElMessage.warning('请输入有效 Finding ID')
    return
  }
  const id = Number(findingIdInput.value)
  if (!route.query.run_id && Number(route.query.finding_id) === id) {
    const token = cancelRequests()
    clearRun()
    finding.value = null
    await loadFinding(id, token)
  } else {
    await router.replace({ name: 'investigations', query: { finding_id: id } })
  }
}

async function searchRun() {
  if (!validId(runIdInput.value)) {
    ElMessage.warning('请输入有效 Run ID')
    return
  }
  const id = Number(runIdInput.value)
  if (Number(route.query.run_id) === id) await loadRun(id)
  else await router.replace({ name: 'investigations', query: { run_id: id } })
}

function refreshCurrentRun() {
  return loadRun(workflow.value?.run_id || route.query.run_id)
}

watch(() => [route.query.finding_id, route.query.run_id], async ([findingId, runId]) => {
  if (validId(runId)) {
    await loadRun(runId)
  } else {
    const token = cancelRequests()
    clearRun()
    finding.value = null
    findingIdInput.value = ''
    if (validId(findingId)) await loadFinding(Number(findingId), token)
    if (runId || (findingId && !validId(findingId))) ElMessage.warning('链接中的 ID 无效')
  }
}, { immediate: true })

onBeforeUnmount(cancelRequests)
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
        v-if="workflow || route.query.run_id"
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
        :disabled="busy || loadingFinding"
        @click="investigate"
      >
        {{
          investigating
            ? '正在提交...'
            : '启动 AI Investigation'
        }}
      </el-button>
    </section>

    <el-alert v-if="pollError" :title="pollError" type="warning" :closable="false" show-icon />

    <template v-if="workflow">
      <div class="run-progress" role="status" aria-live="polite">
        <el-tag :type="statusType(runStatus)">Run: {{ runStatus }}</el-tag>
        <span>{{ polling ? (runStatus === 'completed' ? '调查分析已完成，正在同步 Response / Policy / Approval…' : '正在实时更新调查进度…') : (pollError ? '自动刷新已暂停' : '本次执行已结束，自动刷新已停止') }}</span>
        <small v-if="lastUpdated">最近同步：{{ formatDate(lastUpdated) }}</small>
      </div>
      <el-alert v-if="runStatus === 'failed'" :title="failureMessage" type="error" :closable="false" show-icon />
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
            {{ events.length }}
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
            :description="polling ? '任务已受理，等待首条 Ledger 事件…' : '暂无 Trace Events'"
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

            <div class="approval-footer">
            <small>
              审批、拒绝与 Tool Broker 执行
              请在 Response Center 完成。
            </small>

            <el-button
              type="primary"
              plain
              @click="
                router.push({
                  name: 'response',
                  query: {
                    run_id: workflow.run_id,
                    finding_id: workflow.finding_id,
                  },
                })
              "
            >
              进入 Response Center
            </el-button>
          </div>
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
.investigations-page > .panel,
.summary-card,
.trace-panel,
.detail-column > .panel { padding: 20px; }
.investigations-page .panel-heading { padding: 0; }
.run-progress { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; color: #64748b; }
.run-progress small { margin-left: auto; color: #94a3b8; }
.timeline-item:focus-visible { outline: 2px solid #078fb9; }

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

.approval-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 14px;
}

.approval-footer small {
  flex: 1;
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
