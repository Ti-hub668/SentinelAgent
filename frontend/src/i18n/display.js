import { useI18n } from 'vue-i18n'

// Translate display values only; retain unknown backend values for auditability.
export function useDisplayLabels() {
  const { t, te } = useI18n()
  const events = {
  "context_built": "interface.contextBuilder",
  "triage_completed": "interface.triage",
  "research_completed": "interface.researchRagIntel",
  "evidence_assessed": "interface.evidenceAssessment",
  "risk_enriched": "interface.riskSynthesis",
  "grounding_validated": "interface.groundingValidator",
  "response_planned": "interface.responseAgent",
  "policy_evaluated": "interface.policyEngine",
  "approval_requested": "interface.approvalRequested",
  "approval_resolved": "interface.humanReview",
  "tool_execution_simulated": "interface.toolBroker",
  "tool_execution_executed": "interface.toolBrokerExecuted",
  "tool_execution_replayed": "interface.toolBrokerReplay",
  "tool_execution_blocked": "interface.toolBrokerBlocked",
  "tool_execution_failed": "interface.toolBrokerFailed226",
  "tool_reconciliation_started": "interface.reconciliationStarted",
  "tool_reconciliation_confirmed": "interface.reconciliationConfirmed",
  "tool_reconciliation_unresolved": "interface.reconciliationUnresolved",
  "tool_reconciliation_failed": "interface.reconciliationFailed",
  "investigation_failed": "interface.investigationFailed",
  "workflow_failed": "interface.workflowFailed",
  "stale_run_recovered": "interface.staleRunRecovered",
  "tool_execution_completed": "interface.toolBroker"
}
  function label(value) {
    if (value == null || value === '') return '—'
    const normalized = String(value).toLowerCase()
    const key = events[normalized] || 'labels.' + normalized
    return te(key) ? t(key) : value
  }
  return { label }
}
