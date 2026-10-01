"""Day45 offline broker real-mode integration checks; never contacts GitHub."""
import os
from unittest.mock import patch
from sqlalchemy import select
from app.evaluation.execution_idempotency_evaluator import isolated_ledger, make_request, make_evaluation, execute_with_ledger
from app.agent.ledger import start_investigation_run, get_investigation_trace
from app.agent.tool_broker import execute_policy_result
from app.agent.adapters.github_client import GitHubIssue, GitHubIssueResult
from app.agent.orchestrator import _determine_workflow_status
from app.models.execution_claim import ExecutionClaim

ENV = {
    "SENTINEL_EXTERNAL_TOOL_EXECUTION_ENABLED": "true",
    "SENTINEL_GITHUB_TICKET_ENABLED": "true",
    "SENTINEL_GITHUB_OWNER": "test-owner",
    "SENTINEL_GITHUB_REPO": "test-repo",
    "SENTINEL_GITHUB_TOKEN": "secret-day45-test-token",
}

def main():
    with patch.dict(os.environ, ENV), isolated_ledger() as db, patch("app.agent.adapters.ticket.GitHubIssueClient") as client:
        client.return_value.create_issue.return_value = GitHubIssueResult(GitHubIssue(7, "https://github.com/test-owner/test-repo/issues/7", "test"), True)
        policy = make_evaluation(make_request()).results[0]
        with patch.dict(os.environ, {"SENTINEL_EXTERNAL_TOOL_EXECUTION_ENABLED": "false"}):
            default = execute_policy_result(policy, finding_id=62, approvals=[])
            assert default.status == "simulated" and default.dry_run
        client.assert_not_called()
        assert execute_policy_result(policy, finding_id=62, approvals=[]).status == "blocked"
        for name in ("notify", "block_ip", "manual_review"):
            denied = make_evaluation(make_request(tool_name=name)).results[0].model_copy(update={"decision": "ALLOW"})
            result = execute_policy_result(denied, finding_id=62, approvals=[])
            assert result.status == "blocked" and not result.executed
        assert execute_policy_result(policy, finding_id=62, approvals=[], db=db, run_id=999999).status == "blocked"
        run = start_investigation_run(db, 62)
        for settings in ({"SENTINEL_GITHUB_TOKEN": ""}, {"SENTINEL_GITHUB_TICKET_ENABLED": "false"}, {"SENTINEL_GITHUB_TIMEOUT_SECONDS": "invalid"}):
            with patch.dict(os.environ, settings):
                blocked = execute_with_ledger(db, run_id=run.id, request=make_request())
                assert blocked.blocked_count == 1
        client.assert_not_called()
        from app.agent.policy_engine import build_approval_requests
        review = make_evaluation(make_request(), requires_human_review=True)
        approvals = build_approval_requests(review)
        pending = execute_policy_result(review.results[0], finding_id=62, approvals=approvals, db=db, run_id=run.id)
        assert pending.status == "blocked"
        client.assert_not_called()
        approved_run = start_investigation_run(db, 62)
        approved = [a.model_copy(update={"status": "approved", "reviewer": ENV["SENTINEL_GITHUB_TOKEN"]}) for a in approvals]
        granted = execute_policy_result(review.results[0], finding_id=62, approvals=approved, db=db, run_id=approved_run.id)
        assert granted.status == "executed" and not granted.dry_run
        assert ENV["SENTINEL_GITHUB_TOKEN"] not in granted.model_dump_json()
        assert ENV["SENTINEL_GITHUB_TOKEN"] not in get_investigation_trace(db, approved_run.id).model_dump_json()
        client.reset_mock()
        first = execute_with_ledger(db, run_id=run.id, request=make_request())
        result = first.results[0]
        conflict = execute_with_ledger(db, run_id=run.id, request=make_request(target="finding:63"))
        assert conflict.blocked_count == 1
        assert first.executed_count == 1 and first.simulated_count == 0
        assert result.status == "executed" and not result.dry_run and result.executed
        assert result.execution_receipt.outcome == "executed" and result.execution_receipt.executor_invoked
        claim = db.scalar(select(ExecutionClaim).where(ExecutionClaim.run_id == run.id))
        assert claim.status == "completed" and claim.receipt["outcome"] == "executed"
        with patch.dict(os.environ, {"SENTINEL_EXTERNAL_TOOL_EXECUTION_ENABLED": "false"}):
            replay = execute_with_ledger(db, run_id=run.id, request=make_request())
        again = replay.results[0]
        assert again.replayed and again.status == "executed" and not again.dry_run and not again.executed
        assert replay.executed_count == 0 and replay.replayed_count == 1
        assert again.execution_receipt.outcome == "replayed" and not again.execution_receipt.executor_invoked
        with patch.dict(os.environ, {"SENTINEL_GITHUB_TOKEN": "", "SENTINEL_GITHUB_TICKET_ENABLED": "false"}):
            revoked = execute_with_ledger(db, run_id=run.id, request=make_request()).results[0]
            assert revoked.replayed and revoked.status == "executed" and not revoked.dry_run
        client.return_value.create_issue.assert_called_once()
        assert _determine_workflow_status(run_status="completed", policy=None, approvals=[], tool_results=[again]) == "executed"
        from app.agent.ledger import complete_investigation_run
        from app.agent.orchestrator import get_workflow_summary
        complete_investigation_run(db, run_id=run.id, final_verdict="likely_true_positive")
        assert get_workflow_summary(db, run.id).workflow_status == "executed"
        trace = get_investigation_trace(db, run.id)
        assert sum(e.event_type == "tool_execution_executed" for e in trace.events) == 1
        assert ENV["SENTINEL_GITHUB_TOKEN"] not in trace.model_dump_json()
        failed_run = start_investigation_run(db, 62)
        client.return_value.create_issue.side_effect = RuntimeError(ENV["SENTINEL_GITHUB_TOKEN"])
        failed = execute_with_ledger(db, run_id=failed_run.id, request=make_request())
        assert failed.failed_count == 1 and not failed.results[0].dry_run
        assert ENV["SENTINEL_GITHUB_TOKEN"] not in get_investigation_trace(db, failed_run.id).model_dump_json()
        failed_claim = db.scalar(select(ExecutionClaim).where(ExecutionClaim.run_id == failed_run.id))
        assert failed_claim.status == "failed"
        client.return_value.create_issue.side_effect = None
        client.return_value.create_issue.return_value = GitHubIssueResult(GitHubIssue(8, "https://example/" + ENV["SENTINEL_GITHUB_TOKEN"], "test"), True)
        safe_run = start_investigation_run(db, 62)
        safe = execute_with_ledger(db, run_id=safe_run.id, request=make_request())
        assert ENV["SENTINEL_GITHUB_TOKEN"] not in safe.model_dump_json()
        assert ENV["SENTINEL_GITHUB_TOKEN"] not in get_investigation_trace(db, safe_run.id).model_dump_json()
    print("Day45 Broker real-mode evaluation PASSED")

if __name__ == "__main__":
    main()
