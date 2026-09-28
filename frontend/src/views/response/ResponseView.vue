<script setup>
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
  ElMessageBox,
} from 'element-plus'

import {
  Check,
  Close,
  Cpu,
  DocumentChecked,
  Refresh,
  Search,
  SetUp,
  User,
  WarningFilled,
} from '@element-plus/icons-vue'

import {
  approveInvestigationAction,
  executeInvestigationTools,
  getFinding,
  getInvestigationRun,
  getInvestigationTrace,
  rejectInvestigationAction,
} from '../../api'

const route = useRoute()
const router = useRouter()

const workflow = ref(null)
const finding = ref(null)
const trace = ref(null)
const brokerResult = ref(null)

const runIdInput = ref('')

const loading = ref(false)
const reviewing = ref(false)
const executing = ref(false)

const reviewDialogVisible = ref(false)
const reviewMode = ref('approve')
const selectedApproval = ref(null)

const reviewForm = reactive({
  reviewer: 'security-analyst',
  reason: '',
})

const approvals = computed(
  () => workflow.value?.approvals || [],
)

const policy = computed(
  () =>
    workflow.value?.policy_evaluation ||
    null,
)

const responsePlan = computed(
  () =>
    workflow.value?.response_plan ||
    null,
)

const policyResults = computed(
  () =>
    policy.value?.results || [],
)

const traceEvents = computed(
  () => trace.value?.events || [],
)

const governanceEvents = computed(() => {
  const acceptedTypes = new Set([
    'response_planned',
    'policy_evaluated',
    'approval_requested',
    'approval_resolved',
    'tool_execution_simulated',
    'tool_execution_completed',
    'tool_execution_failed',
  ])

  return traceEvents.value.filter(
    (item) =>
      acceptedTypes.has(
        item.event_type,
      ),
  )
})

const pendingApprovals = computed(
  () =>
    approvals.value.filter(
      (item) =>
        item.status === 'pending',
    ),
)

const approvedApprovals = computed(
  () =>
    approvals.value.filter(
      (item) =>
        item.status === 'approved',
    ),
)

const rejectedApprovals = computed(
  () =>
    approvals.value.filter(
      (item) =>
        item.status === 'rejected',
    ),
)
const brokerDisplay = computed(() => {
  if (brokerResult.value) {
    const results =
      brokerResult.value.results || []

    return {
      results,

      simulated_count:
        brokerResult.value
          .simulated_count ??
        results.filter(
          (item) =>
            item.status ===
            'simulated',
        ).length,

      blocked_count:
        brokerResult.value
          .blocked_count ??
        results.filter(
          (item) =>
            item.status ===
            'blocked',
        ).length,

      failed_count:
        brokerResult.value
          .failed_count ??
        results.filter(
          (item) =>
            item.status ===
            'failed',
        ).length,
    }
  }

  const results =
    workflow.value?.tool_results || []

  return {
    results,

    simulated_count:
      results.filter(
        (item) =>
          item.status ===
          'simulated',
      ).length,

    blocked_count:
      results.filter(
        (item) =>
          item.status ===
          'blocked',
      ).length,

    failed_count:
      results.filter(
        (item) =>
          item.status ===
          'failed',
      ).length,
  }
})

const canExecute = computed(() => {
  if (!workflow.value) {
    return false
  }

  if (
    pendingApprovals.value.length > 0
  ) {
    return false
  }

  return (
    workflow.value
      .workflow_status ===
    'ready_for_execution'
  )
})

const workflowStatusLabel = computed(() => {
  const status =
    workflow.value?.workflow_status

  const labels = {
    failed:
      'Workflow Failed',

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

  if (
    Number.isNaN(date.getTime())
  ) {
    return value
  }

  return date.toLocaleString()
}

function workflowTagType(status) {
  if (
    status ===
      'ready_for_execution' ||
    status ===
      'dry_run_executed'
  ) {
    return 'success'
  }

  if (
    status ===
    'awaiting_approval'
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

function policyTagType(decision) {
  if (decision === 'ALLOW') {
    return 'success'
  }

  if (decision === 'DENY') {
    return 'danger'
  }

  return 'warning'
}

function approvalTagType(status) {
  if (status === 'approved') {
    return 'success'
  }

  if (status === 'rejected') {
    return 'danger'
  }

  return 'warning'
}

function brokerTagType(status) {
  if (status === 'simulated') {
    return 'success'
  }

  if (
    status === 'blocked' ||
    status === 'failed'
  ) {
    return 'danger'
  }

  return 'info'
}

function toolName(value) {
  if (!value) {
    return 'Unknown Tool'
  }

  const labels = {
    manual_review:
      'Manual Review',

    create_ticket:
      'Create Ticket',

    notify:
      'Notify',

    block_ip:
      'Block IP',
  }

  return labels[value] || value
}

function eventLabel(type) {
  const labels = {
    response_planned:
      'Response Agent',

    policy_evaluated:
      'Policy Engine',

    approval_requested:
      'Approval Requested',

    approval_resolved:
      'Human Review',

    tool_execution_simulated:
      'Tool Broker',

    tool_execution_completed:
      'Tool Broker',

    tool_execution_failed:
      'Tool Broker Failed',
  }

  return labels[type] || type
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
  } catch (error) {
    console.error(error)
  }
}

async function loadFinding(id) {
  if (!id) {
    return
  }

  try {
    finding.value =
      await getFinding(
        id,
        {
          silent: true,
        },
      )
  } catch (error) {
    console.error(error)
  }
}

async function loadRun(runId) {
  const id = Number(runId)

  if (!id) {
    ElMessage.warning(
      '请输入有效 Run ID',
    )

    return
  }

  loading.value = true

  try {
    const result =
      await getInvestigationRun(
        id,
        {
          silent: true,
        },
      )

    workflow.value = result

    runIdInput.value =
      String(result.run_id)

    brokerResult.value = null

    await Promise.all([
      loadFinding(
        result.finding_id,
      ),
      loadTrace(
        result.run_id,
      ),
    ])

    await router.replace({
      name: 'response',

      query: {
        run_id: result.run_id,
        finding_id:
          result.finding_id,
      },
    })
  } catch (error) {
    console.error(error)

    ElMessage.error(
      'Response Run 加载失败',
    )
  } finally {
    loading.value = false
  }
}

async function searchRun() {
  await loadRun(
    runIdInput.value,
  )
}

async function refreshRun() {
  if (!workflow.value?.run_id) {
    return
  }

  await loadRun(
    workflow.value.run_id,
  )
}

function openReview(
  approval,
  mode,
) {
  selectedApproval.value =
    approval

  reviewMode.value = mode

  reviewForm.reviewer =
    'security-analyst'

  reviewForm.reason =
    mode === 'approve'
      ? 'Evidence reviewed and action approved.'
      : 'Action rejected after security review.'

  reviewDialogVisible.value = true
}

async function submitReview() {
  if (
    !reviewForm.reviewer.trim()
  ) {
    ElMessage.warning(
      'Reviewer 不能为空',
    )

    return
  }

  if (
    !reviewForm.reason.trim()
  ) {
    ElMessage.warning(
      'Review reason 不能为空',
    )

    return
  }

  if (
    !selectedApproval.value ||
    !workflow.value
  ) {
    return
  }

  reviewing.value = true

  try {
    const payload = {
      reviewer:
        reviewForm.reviewer.trim(),

      reason:
        reviewForm.reason.trim(),
    }

    let result

    if (
      reviewMode.value ===
      'approve'
    ) {
      result =
        await approveInvestigationAction(
          workflow.value.run_id,
          selectedApproval.value
            .request_index,
          payload,
        )
    } else {
      result =
        await rejectInvestigationAction(
          workflow.value.run_id,
          selectedApproval.value
            .request_index,
          payload,
        )
    }

    workflow.value = result

    reviewDialogVisible.value =
      false

    await loadTrace(
      workflow.value.run_id,
    )

    ElMessage.success(
      reviewMode.value ===
        'approve'
        ? 'Action 已批准，但尚未执行'
        : 'Action 已拒绝',
    )
  } catch (error) {
    console.error(error)
  } finally {
    reviewing.value = false
  }
}

async function executeTools() {
  if (!workflow.value) {
    return
  }

  if (
    pendingApprovals.value.length
  ) {
    ElMessage.warning(
      '仍有待审批 Action，不能进入 Tool Broker',
    )

    return
  }

  try {
    await ElMessageBox.confirm(
      '当前 Tool Broker 为 DRY-RUN / Mock 模式，不会产生真实外部副作用。是否继续执行授权动作？',
      'Execute Authorized Actions',
      {
        confirmButtonText:
          '执行 Dry-run',
        cancelButtonText:
          '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  executing.value = true

  try {
    brokerResult.value =
      await executeInvestigationTools(
        workflow.value.run_id,
      )

    workflow.value =
      await getInvestigationRun(
        workflow.value.run_id,
        {
          silent: true,
        },
      )

    await loadTrace(
      workflow.value.run_id,
    )

    ElMessage.success(
      'Tool Broker Dry-run 已完成',
    )
  } catch (error) {
    console.error(error)
  } finally {
    executing.value = false
  }
}

onMounted(async () => {
  const queryRun =
    Number(route.query.run_id)

  if (queryRun) {
    await loadRun(queryRun)
  }
})
</script>

<template>
  <div class="response-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">
          RESPONSE GOVERNANCE
        </div>

        <h2>
          Response Center
        </h2>

        <p>
          Policy、Human Approval 与 Tool Broker
          安全响应工作台
        </p>
      </div>

      <el-button
        v-if="workflow"
        :icon="Refresh"
        :loading="loading"
        @click="refreshRun"
      >
        刷新状态
      </el-button>
    </div>

    <section class="panel run-loader">
      <div>
        <label>
          Investigation Run ID
        </label>

        <div class="run-search">
          <el-input
            v-model="runIdInput"
            placeholder="例如 31"
            @keyup.enter="searchRun"
          />

          <el-button
            type="primary"
            :icon="Search"
            :loading="loading"
            @click="searchRun"
          >
            加载 Response
          </el-button>
        </div>
      </div>

      <div class="safety-notice">
        <el-icon>
          <DocumentChecked />
        </el-icon>

        <div>
          <strong>
            Safe Execution Boundary
          </strong>

          <span>
            当前 Tool Broker
            仅执行 Dry-run / Mock，
            不产生真实 SOAR 副作用。
          </span>
        </div>
      </div>
    </section>

    <template v-if="workflow">
      <div class="summary-grid">
        <section class="panel summary-card">
          <span>
            Workflow Run
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
              workflowTagType(
                workflow.workflow_status,
              )
            "
          >
            {{
              workflow.workflow_status
            }}
          </el-tag>
        </section>

        <section class="panel summary-card">
          <span>
            Pending Approval
          </span>

          <strong>
            {{
              pendingApprovals.length
            }}
          </strong>

          <small>
            {{
              approvedApprovals.length
            }}
            approved ·
            {{
              rejectedApprovals.length
            }}
            rejected
          </small>
        </section>

        <section class="panel summary-card">
          <span>
            Tool Broker
          </span>
          <strong class="summary-text">
            {{
              brokerDisplay.results.length
                ? 'Executed'
                : 'Not Executed'
            }}
          </strong>

          <small>
            Dry-run only
          </small>
        </section>
      </div>

      <section
        v-if="finding"
        class="panel finding-banner"
      >
        <div>
          <span class="section-label">
            SECURITY FINDING
          </span>

          <h3>
            #{{ finding.id }}
            ·
            {{ finding.title }}
          </h3>

          <div class="tag-row">
            <el-tag effect="plain">
              {{ finding.source }}
            </el-tag>

            <el-tag
              type="info"
              effect="plain"
            >
              {{ finding.severity }}
            </el-tag>

            <el-tag
              effect="plain"
            >
              Risk:
              {{
                finding.risk_level
              }}
            </el-tag>

            <el-tag
              type="danger"
              effect="plain"
            >
              {{
                workflow.final_verdict
              }}
            </el-tag>
          </div>
        </div>

        <el-button
          @click="
            router.push({
              name: 'investigations',
              query: {
                finding_id:
                  workflow.finding_id,
                run_id:
                  workflow.run_id,
              },
            })
          "
        >
          查看 Investigation
        </el-button>
      </section>

      <div class="main-grid">
        <div class="main-column">
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

              <div class="tag-row">
                <el-tag
                  :type="
                    responsePlan
                      .requires_human_review
                      ? 'warning'
                      : 'success'
                  "
                >
                  {{
                    responsePlan
                      .requires_human_review
                      ? 'Human Review'
                      : 'No Review'
                  }}
                </el-tag>

                <el-tag
                  type="info"
                  effect="plain"
                >
                  Dry-run
                </el-tag>
              </div>
            </div>

            <div class="response-overview">
              <div>
                <span>
                  Grounded Verdict
                </span>

                <strong>
                  {{
                    responsePlan
                      .grounded_verdict
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Decision Action
                </span>

                <strong>
                  {{
                    responsePlan
                      .decision_action
                  }}
                </strong>
              </div>

              <div>
                <span>
                  Priority
                </span>

                <strong>
                  {{
                    responsePlan.priority
                  }}
                </strong>
              </div>
            </div>

            <div class="response-summary">
              <span>
                Analyst Summary
              </span>

              <p>
                {{
                  responsePlan.summary
                }}
              </p>
            </div>

            <template
              v-for="section in [
                {
                  title:
                    'Containment Plan',
                  value:
                    responsePlan
                      .containment_plan,
                },
                {
                  title:
                    'Remediation Plan',
                  value:
                    responsePlan
                      .remediation_plan,
                },
                {
                  title:
                    'Verification Plan',
                  value:
                    responsePlan
                      .verification_plan,
                },
              ]"
              :key="section.title"
            >
              <div
                v-if="
                  section.value?.length
                "
                class="plan-section"
              >
                <span>
                  {{ section.title }}
                </span>

                <ul>
                  <li
                    v-for="(
                      item,
                      index
                    ) in section.value"
                    :key="index"
                  >
                    {{ item }}
                  </li>
                </ul>
              </div>
            </template>
          </section>

          <section class="panel">
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  REQUESTED ACTIONS
                </span>

                <h3>
                  Tool Requests
                </h3>
              </div>

              <el-tag
                effect="plain"
              >
                {{
                  responsePlan
                    ?.tool_requests
                    ?.length || 0
                }}
                requests
              </el-tag>
            </div>

            <div
              v-if="
                responsePlan
                  ?.tool_requests
                  ?.length
              "
              class="tool-request-list"
            >
              <div
                v-for="(
                  request,
                  index
                ) in responsePlan
                  .tool_requests"
                :key="index"
                class="tool-request-card"
              >
                <div class="tool-icon">
                  <el-icon>
                    <SetUp />
                  </el-icon>
                </div>

                <div class="tool-main">
                  <div class="tool-title">
                    <strong>
                      {{
                        toolName(
                          request.tool_name,
                        )
                      }}
                    </strong>

                    <el-tag
                      v-if="
                        policyResults[
                          index
                        ]
                      "
                      size="small"
                      :type="
                        policyTagType(
                          policyResults[
                            index
                          ].decision,
                        )
                      "
                    >
                      {{
                        policyResults[
                          index
                        ].decision
                      }}
                    </el-tag>
                  </div>

                  <span class="target">
                    {{
                      request.target
                    }}
                  </span>

                  <p>
                    {{
                      request.reason
                    }}
                  </p>

                  <pre
                    v-if="
                      request.parameters
                    "
                  >{{
                    JSON.stringify(
                      request.parameters,
                      null,
                      2,
                    )
                  }}</pre>
                </div>
              </div>
            </div>

            <el-empty
              v-else
              description="No Tool Requests"
            />
          </section>

          <section
            v-if="brokerDisplay.results.length"
            class="panel broker-panel"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  TOOL BROKER
                </span>

                <h3>
                  Execution Results
                </h3>
              </div>

              <el-tag
                type="success"
              >
                Dry-run Complete
              </el-tag>
            </div>

            <div class="broker-counts">
              <div>
                <span>
                  SIMULATED
                </span>

                <strong>
                  {{
                    brokerDisplay
                      .simulated_count
                  }}
                </strong>
              </div>

              <div>
                <span>
                  BLOCKED
                </span>

                <strong>
                  {{
                    brokerDisplay
                      .blocked_count
                  }}
                </strong>
              </div>

              <div>
                <span>
                  FAILED
                </span>

                <strong>
                  {{
                    brokerDisplay
                      .failed_count
                  }}
                </strong>
              </div>
            </div>

            <div
              class="broker-result-list"
            >
              <div
                v-for="item in
                  brokerDisplay.results"
                :key="
                  item.request_index
                "
                class="broker-result"
              >
                <div>
                  <strong>
                    {{
                      toolName(
                        item
                          .tool_request
                          .tool_name,
                      )
                    }}
                  </strong>

                  <span>
                    Request
                    #{{
                      item.request_index
                    }}
                  </span>
                </div>

                <el-tag
                  :type="
                    brokerTagType(
                      item.status,
                    )
                  "
                >
                  {{ item.status }}
                </el-tag>

                <p>
                  {{ item.message }}
                </p>

                <div class="broker-flags">
                  <span>
                    Authorized:
                    {{
                      item.authorized
                    }}
                  </span>

                  <span>
                    Executed:
                    {{
                      item.executed
                    }}
                  </span>

                  <span>
                    Dry-run:
                    {{
                      item.dry_run
                    }}
                  </span>
                </div>

                <pre
                  v-if="
                    item.output &&
                    Object.keys(
                      item.output,
                    ).length
                  "
                >{{
                  JSON.stringify(
                    item.output,
                    null,
                    2,
                  )
                }}</pre>
              </div>
            </div>
          </section>
        </div>

        <div class="side-column">
          <section
            v-if="policy"
            class="panel"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  POLICY ENGINE
                </span>

                <h3>
                  Governance Decision
                </h3>
              </div>
            </div>

            <div class="policy-counts">
              <div class="allow">
                <span>
                  ALLOW
                </span>

                <strong>
                  {{
                    policy.allow_count
                  }}
                </strong>
              </div>

              <div class="deny">
                <span>
                  DENY
                </span>

                <strong>
                  {{
                    policy.deny_count
                  }}
                </strong>
              </div>

              <div class="approval">
                <span>
                  APPROVAL
                </span>

                <strong>
                  {{
                    policy
                      .approval_count
                  }}
                </strong>
              </div>
            </div>

            <div class="policy-list">
              <div
                v-for="item in
                  policyResults"
                :key="
                  item.request_index
                "
                class="policy-item"
              >
                <div class="policy-item-top">
                  <strong>
                    Request
                    #{{
                      item.request_index
                    }}
                  </strong>

                  <el-tag
                    size="small"
                    :type="
                      policyTagType(
                        item.decision,
                      )
                    "
                  >
                    {{
                      item.decision
                    }}
                  </el-tag>
                </div>

                <p>
                  {{ item.reason }}
                </p>
              </div>
            </div>
          </section>

          <section
            v-if="approvals.length"
            class="panel"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  HUMAN IN THE LOOP
                </span>

                <h3>
                  Human Approval
                </h3>
              </div>

              <el-icon
                class="approval-icon"
              >
                <User />
              </el-icon>
            </div>

            <div class="approval-list">
              <div
                v-for="approval in
                  approvals"
                :key="
                  approval.request_index
                "
                class="approval-item"
              >
                <div class="approval-head">
                  <div>
                    <strong>
                      {{
                        toolName(
                          approval
                            .tool_request
                            .tool_name,
                        )
                      }}
                    </strong>

                    <small>
                      Request
                      #{{
                        approval
                          .request_index
                      }}
                    </small>
                  </div>

                  <el-tag
                    :type="
                      approvalTagType(
                        approval.status,
                      )
                    "
                  >
                    {{
                      approval.status
                    }}
                  </el-tag>
                </div>

                <p>
                  {{
                    approval
                      .policy_reason
                  }}
                </p>

                <div
                  v-if="
                    approval.status !==
                    'pending'
                  "
                  class="review-record"
                >
                  <div>
                    <span>
                      Reviewer
                    </span>

                    <strong>
                      {{
                        approval.reviewer ||
                        '—'
                      }}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Reason
                    </span>

                    <strong>
                      {{
                        approval
                          .review_reason ||
                        '—'
                      }}
                    </strong>
                  </div>
                </div>

                <div
                  v-if="
                    approval.status ===
                    'pending'
                  "
                  class="approval-actions"
                >
                  <el-button
                    :icon="Close"
                    @click="
                      openReview(
                        approval,
                        'reject',
                      )
                    "
                  >
                    Reject
                  </el-button>

                  <el-button
                    type="primary"
                    :icon="Check"
                    @click="
                      openReview(
                        approval,
                        'approve',
                      )
                    "
                  >
                    Approve
                  </el-button>
                </div>
              </div>
            </div>
          </section>

          <section class="panel execution-card">
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  EXECUTION BOUNDARY
                </span>

                <h3>
                  Tool Broker
                </h3>
              </div>

              <el-icon>
                <Cpu />
              </el-icon>
            </div>

            <div
              v-if="
                pendingApprovals.length
              "
              class="execution-warning"
            >
              <el-icon>
                <WarningFilled />
              </el-icon>

              <span>
                {{
                  pendingApprovals.length
                }}
                个动作仍等待人工审批。
              </span>
            </div>

            <div
              v-else
              class="execution-ready"
            >
              <el-icon>
                <Check />
              </el-icon>

              <span>
                所有审批已处理，
                可以进入 Tool Broker。
              </span>
            </div>

            <p>
              Tool Broker
              是所有响应动作的唯一执行边界。
              当前仅执行模拟动作，
              不会产生真实外部副作用。
            </p>

            <el-button
              type="primary"
              class="execute-button"
              :disabled="!canExecute"
              :loading="executing"
              @click="executeTools"
            >
              Execute Authorized Actions
            </el-button>
          </section>

          <section
            v-if="
              governanceEvents.length
            "
            class="panel"
          >
            <div class="panel-heading">
              <div>
                <span class="section-label">
                  GOVERNANCE TRACE
                </span>

                <h3>
                  Response Timeline
                </h3>
              </div>
            </div>

            <div class="governance-trace">
              <div
                v-for="event in
                  governanceEvents"
                :key="event.id"
                class="governance-event"
              >
                <span class="trace-dot">
                </span>

                <div>
                  <strong>
                    {{
                      eventLabel(
                        event.event_type,
                      )
                    }}
                  </strong>

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
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>

    <section
      v-else
      class="panel empty-state"
    >
      <el-empty
        description="加载一个 Investigation Run 开始响应治理"
      >
        <p class="empty-help">
          可以使用昨天生成的
          Run #31 进行测试。
        </p>
      </el-empty>
    </section>

    <el-dialog
      v-model="reviewDialogVisible"
      :title="
        reviewMode === 'approve'
          ? 'Approve Security Action'
          : 'Reject Security Action'
      "
      width="520px"
      destroy-on-close
    >
      <el-alert
        :type="
          reviewMode === 'approve'
            ? 'warning'
            : 'error'
        "
        :closable="false"
        show-icon
      >
        <template #title>
          {{
            reviewMode === 'approve'
              ? '批准只代表授权，不会立即执行工具。'
              : '拒绝后该 Action 将不会被授权执行。'
          }}
        </template>
      </el-alert>

      <el-form
        label-position="top"
        class="review-form"
      >
        <el-form-item
          label="Reviewer"
          required
        >
          <el-input
            v-model="
              reviewForm.reviewer
            "
            maxlength="100"
            placeholder="例如 security-analyst"
          />
        </el-form-item>

        <el-form-item
          label="Review Reason"
          required
        >
          <el-input
            v-model="
              reviewForm.reason
            "
            type="textarea"
            :rows="4"
            maxlength="1000"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button
          @click="
            reviewDialogVisible =
              false
          "
        >
          Cancel
        </el-button>

        <el-button
          :type="
            reviewMode === 'approve'
              ? 'primary'
              : 'danger'
          "
          :loading="reviewing"
          @click="submitReview"
        >
          {{
            reviewMode === 'approve'
              ? 'Confirm Approval'
              : 'Confirm Rejection'
          }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.response-page {
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

.run-loader {
  display: grid;
  grid-template-columns:
    minmax(300px, 0.75fr)
    minmax(360px, 1fr);
  gap: 28px;
  align-items: end;
}

.run-loader label {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
}

.run-search {
  display: flex;
  gap: 8px;
}

.safety-notice {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 42px;
  padding: 10px 14px;
  border: 1px solid #d9edf2;
  border-radius: 9px;
  color: #477685;
  background: #f4fbfc;
}

.safety-notice .el-icon {
  font-size: 20px;
}

.safety-notice div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.safety-notice strong {
  font-size: 11px;
}

.safety-notice span {
  font-size: 10px;
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

.finding-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.finding-banner h3 {
  margin: 5px 0 9px;
  color: #334155;
  font-size: 17px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.main-grid {
  display: grid;
  grid-template-columns:
    minmax(0, 1.45fr)
    minmax(320px, 0.75fr);
  gap: 18px;
  align-items: start;
}

.main-column,
.side-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.response-overview {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.response-overview div {
  padding: 12px;
  border: 1px solid #edf0f4;
  border-radius: 8px;
  background: #fafbfc;
}

.response-overview span,
.response-summary > span,
.plan-section > span {
  display: block;
  color: #94a3b8;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.response-overview strong {
  display: block;
  margin-top: 6px;
  color: #334155;
  font-size: 11px;
  word-break: break-word;
}

.response-summary {
  margin-top: 16px;
}

.response-summary p {
  margin: 7px 0 0;
  color: #64748b;
  font-size: 11px;
  line-height: 1.75;
}

.plan-section {
  margin-top: 16px;
}

.plan-section ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #64748b;
  font-size: 11px;
  line-height: 1.8;
}

.tool-request-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-request-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  border: 1px solid #e8edf2;
  border-radius: 10px;
  background: #fbfcfd;
}

.tool-icon {
  display: flex;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  color: #288ba6;
  background: #e4f5f8;
}

.tool-main {
  min-width: 0;
  flex: 1;
}

.tool-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.tool-title strong {
  color: #334155;
  font-size: 12px;
}

.target {
  display: block;
  margin-top: 3px;
  color: #95a1b1;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  font-size: 9px;
}

.tool-main p {
  margin: 8px 0;
  color: #64748b;
  font-size: 10px;
  line-height: 1.65;
}

.tool-main pre,
.broker-result pre {
  margin: 8px 0 0;
  padding: 10px;
  overflow: auto;
  border-radius: 7px;
  color: #cbd8e6;
  font-family:
    "Cascadia Code",
    Consolas,
    monospace;
  font-size: 9px;
  line-height: 1.55;
  background: #182332;
}

.policy-counts,
.broker-counts {
  display: grid;
  grid-template-columns:
    repeat(3, 1fr);
  gap: 8px;
}

.policy-counts > div,
.broker-counts > div {
  padding: 12px 6px;
  border: 1px solid #edf0f4;
  border-radius: 8px;
  text-align: center;
}

.policy-counts span,
.broker-counts span {
  display: block;
  color: #94a3b8;
  font-size: 8px;
}

.policy-counts strong,
.broker-counts strong {
  display: block;
  margin-top: 6px;
  color: #334155;
  font-size: 19px;
}

.policy-counts .allow {
  background: #f5fbf8;
}

.policy-counts .deny {
  background: #fff8f8;
}

.policy-counts .approval {
  background: #fffaf0;
}

.policy-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-top: 14px;
}

.policy-item {
  padding: 11px;
  border: 1px solid #edf0f4;
  border-radius: 8px;
}

.policy-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.policy-item-top strong {
  color: #475569;
  font-size: 10px;
}

.policy-item p {
  margin: 7px 0 0;
  color: #78879a;
  font-size: 10px;
  line-height: 1.6;
}

.approval-icon {
  color: #a98122;
  font-size: 20px;
}

.approval-list {
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.approval-item {
  padding: 13px;
  border: 1px solid #eee1bc;
  border-radius: 9px;
  background: #fffdf7;
}

.approval-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.approval-head strong {
  display: block;
  color: #475569;
  font-size: 11px;
}

.approval-head small {
  color: #9a8b69;
  font-size: 9px;
}

.approval-item p {
  margin: 9px 0;
  color: #786c55;
  font-size: 10px;
  line-height: 1.6;
}

.approval-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.review-record {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.review-record div {
  padding: 9px;
  border-radius: 7px;
  background: #fff;
}

.review-record span {
  display: block;
  color: #9a8b69;
  font-size: 8px;
}

.review-record strong {
  display: block;
  margin-top: 3px;
  color: #5c6470;
  font-size: 10px;
}

.execution-card p {
  color: #77869a;
  font-size: 10px;
  line-height: 1.7;
}

.execution-warning,
.execution-ready {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px;
  border-radius: 8px;
  font-size: 10px;
}

.execution-warning {
  color: #92711a;
  background: #fff8e7;
}

.execution-ready {
  color: #347a5c;
  background: #edf9f3;
}

.execute-button {
  width: 100%;
  margin-top: 12px;
}

.broker-counts {
  margin-bottom: 14px;
}

.broker-result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.broker-result {
  padding: 13px;
  border: 1px solid #e5ebf0;
  border-radius: 9px;
}

.broker-result > div:first-child {
  display: inline-flex;
  flex-direction: column;
  margin-right: 8px;
}

.broker-result strong {
  color: #334155;
  font-size: 11px;
}

.broker-result span {
  color: #94a3b8;
  font-size: 9px;
}

.broker-result p {
  color: #64748b;
  font-size: 10px;
  line-height: 1.6;
}

.broker-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
}

.broker-flags span {
  color: #718096;
  font-size: 9px;
}

.governance-trace {
  display: flex;
  flex-direction: column;
}

.governance-event {
  position: relative;
  display: flex;
  gap: 10px;
  padding-bottom: 15px;
}

.governance-event:not(:last-child)::before {
  position: absolute;
  top: 12px;
  bottom: 0;
  left: 4px;
  width: 1px;
  content: "";
  background: #dce5ed;
}

.trace-dot {
  z-index: 1;
  width: 9px;
  height: 9px;
  flex: 0 0 9px;
  margin-top: 3px;
  border-radius: 50%;
  background: #55a8bc;
}

.governance-event strong {
  color: #475569;
  font-size: 10px;
}

.governance-event p {
  margin: 4px 0;
  color: #7d8999;
  font-size: 9px;
  line-height: 1.5;
}

.governance-event small {
  color: #a3acb9;
  font-size: 8px;
}

.review-form {
  margin-top: 18px;
}

.empty-state {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-help {
  margin: 0;
  color: #94a3b8;
  font-size: 11px;
}

@media (max-width: 1180px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns:
      repeat(2, 1fr);
  }
}

@media (max-width: 800px) {
  .page-heading,
  .finding-banner {
    flex-direction: column;
  }

  .run-loader {
    grid-template-columns: 1fr;
  }

  .summary-grid,
  .response-overview {
    grid-template-columns: 1fr;
  }
}
</style>