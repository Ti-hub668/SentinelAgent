"""Offline Day41 regression checks; no LLM, network, or application DB writes."""
import json
from dataclasses import replace
from unittest.mock import Mock, patch

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent.ledger import get_investigation_trace, start_investigation_run
from app.agent.policy_engine import build_approval_requests, evaluate_response_plan
from app.agent.response_prompt_builder import build_response_prompt
from app.agent.tool_broker import execute_policy_evaluation_with_ledger, execute_policy_result
from app.agent.tool_registry import (
    TOOL_REGISTRY, get_tool_capability, list_tool_capabilities,
    validate_tool_request_parameters,
)
from app.evaluation.tool_broker_evaluator import make_plan
from app.evaluation.tool_registry_evaluator import EXPECTED_TOOLS, make_allow_result
from app.models.investigation_event import InvestigationEvent
from app.models.investigation_run import InvestigationRun
from app.schemas.agent_decision import AgentDecisionOutput
from app.schemas.response_plan import ToolRequest
from app.schemas.tool_broker import ToolExecutionResult
from app.schemas.tool_capability import ToolCapabilityDescriptor


def request(name="create_ticket", **updates):
    values = dict(tool_name=name, target="finding:62", reason="Offline Day41 check.")
    if name == "manual_review":
        values["parameters"] = dict(finding_id=62, grounded_verdict="likely_true_positive")
    values.update(updates)
    return ToolRequest(**values)


def execute(item):
    return execute_policy_result(make_allow_result(item), finding_id=62, approvals=[])


def test_discovery():
    with patch.dict(TOOL_REGISTRY, {
        name: replace(value, executor=Mock(side_effect=AssertionError("discovery executed")))
        for name, value in TOOL_REGISTRY.items()
    }):
        descriptors = list_tool_capabilities()
        assert [item.name for item in descriptors] == sorted(EXPECTED_TOOLS)
        for item in descriptors:
            assert item == get_tool_capability(item.name)
            assert item.description and item.governance_notes and item.capabilities and item.tags
            assert item.requires_target and item.dry_run
            assert item.requires_approval == (item.name in {"block_ip", "manual_review"})
            assert item.risk_level == ("high" if item.name == "block_ip" else "low")
            payload = item.model_dump_json()
            assert ToolCapabilityDescriptor.model_validate_json(payload) == item
            assert not any(token in payload for token in ("executor", "simulate_", "mock_", "app.agent"))
            assert item.parameters_schema["additionalProperties"] is False
        # Returned nested schema is detached, even though dicts themselves are mutable.
        descriptors[0].parameters_schema.clear()
        assert get_tool_capability(descriptors[0].name).parameters_schema
        assert get_tool_capability("unknown_tool") is None
        assert "finding_id" in get_tool_capability("manual_review").parameters_schema["required"]


def test_fail_closed_and_four_tools():
    for name in sorted(EXPECTED_TOOLS):
        result = execute(request(name))
        assert result.status == "simulated" and result.executed and result.dry_run
        assert result.registry_metadata.validated_contract == TOOL_REGISTRY[name].parameter_schema.__name__
        spy = Mock()
        with patch.dict(TOOL_REGISTRY, {name: replace(TOOL_REGISTRY[name], executor=spy)}):
            result = execute(request(name, parameters={"dangerous_option": True}))
            assert result.status == "blocked" and not result.authorized and not result.executed
            assert result.registry_metadata.validated_contract is None
            spy.assert_not_called()
    result = execute(request("manual_review", parameters={"finding_id": "62", "grounded_verdict": "x"}))
    assert result.status == "blocked"
    # Exercise Broker's defensive path below the Literal input boundary.
    unknown = request().model_copy(update={"tool_name": "unknown_tool"})
    result = execute(unknown)
    assert result.status == "blocked" and result.registry_metadata is None
    try:
        validate_tool_request_parameters(unknown)
    except LookupError:
        pass
    else:
        raise AssertionError("Unknown contract accepted")
    try:
        request("unknown_tool")
    except ValidationError:
        pass
    else:
        raise AssertionError("Unknown tool accepted at input boundary")
    with patch.dict(TOOL_REGISTRY, {}, clear=True):
        assert list_tool_capabilities() == []
        assert execute(request()).status == "blocked"


def test_prompt():
    args = dict(
        finding_id=62, title="Test finding", severity="high", target="finding:62",
        grounded_verdict="likely_true_positive", grounding_status="grounded",
        grounding_reason="Test evidence", risk_summary="Test risk", recommended_action="review",
        decision=AgentDecisionOutput(action="recommend_remediation", priority="medium",
            reason="Test", requires_human_review=False, recommended_next_step="review"),
    )
    plain = build_response_prompt(**args)
    assert "Registered Tool Capabilities" not in plain
    enabled = build_response_prompt(**args, include_tool_capabilities=True)
    assert "Metadata does not authorize execution" in enabled
    payload = enabled.split("remain authoritative; all tools are dry-run.\n", 1)[1].split("\nReturn ONLY", 1)[0]
    assert json.loads(payload) == [item.model_dump(mode="json") for item in list_tool_capabilities()]
    assert not any(token in payload for token in ("executor", "simulate_", "mock_"))


def test_ledger_and_governance():
    engine = create_engine("sqlite:///:memory:")
    InvestigationRun.__table__.create(engine)
    InvestigationEvent.__table__.create(engine)
    try:
        with Session(engine) as db:
            run = start_investigation_run(db, 62)
            cases = [
                (request(), "simulated"),
                (request(parameters={"dangerous_option": True}), "blocked"),
                (request("block_ip"), "blocked"),
            ]
            for item, expected in cases:
                evaluation = evaluate_response_plan(make_plan(request=item))
                batch = execute_policy_evaluation_with_ledger(db, run_id=run.id,
                    evaluation=evaluation, approvals=build_approval_requests(evaluation))
                assert batch.results[0].status == expected
            # Failed executor still has a successfully validated contract.
            definition = TOOL_REGISTRY["create_ticket"]
            with patch.dict(TOOL_REGISTRY, {"create_ticket": replace(definition,
                    executor=Mock(side_effect=RuntimeError("test failure")))}):
                failure_evaluation = evaluate_response_plan(
                    make_plan(request=request(target="finding:63")))
                # A new action needs a new slot; changing slot 0 is correctly blocked.
                failure_evaluation.results[0].request_index = 1
                failed_batch = execute_policy_evaluation_with_ledger(
                    db, run_id=run.id, evaluation=failure_evaluation, approvals=[])
                assert failed_batch.results[0].status == "failed"
                TOOL_REGISTRY["create_ticket"].executor.assert_called_once()
            trace = get_investigation_trace(db, run.id)
            assert [event.event_type for event in trace.events] == [
                "tool_execution_simulated", "tool_execution_blocked",
                "tool_execution_blocked", "tool_execution_failed",
            ]
            legacy_keys = {"finding_id", "request_index", "tool_name", "target", "policy_decision",
                "authorized", "executed", "dry_run", "broker_status", "message", "output", "execution_result"}
            for index, event in enumerate(trace.events):
                data = event.event_metadata
                assert legacy_keys <= data.keys()
                assert data["tool_registry"]["tool_name"] == data["tool_name"]
                assert bool(data["tool_registry"]["validated_contract"]) == (index in {0, 3})
                parsed = ToolExecutionResult.model_validate(data["execution_result"])
                assert parsed.registry_metadata.model_dump() == data["tool_registry"]
                legacy = dict(data["execution_result"])
                legacy.pop("registry_metadata")
                assert ToolExecutionResult.model_validate(legacy).registry_metadata is None
            # Descriptive governance cannot override existing Policy/Approval rules.
            with patch.dict(TOOL_REGISTRY, {"block_ip": replace(TOOL_REGISTRY["block_ip"], requires_approval=False)}):
                evaluation = evaluate_response_plan(make_plan(request=request("block_ip")))
                assert evaluation.results[0].decision == "REQUIRE_APPROVAL"
                assert execute_policy_result(evaluation.results[0], finding_id=62, approvals=[]).status == "blocked"
    finally:
        engine.dispose()


def main():
    for check in (test_discovery, test_fail_closed_and_four_tools, test_prompt, test_ledger_and_governance):
        check()
        print(f"[PASS] {check.__name__}")
    print("\nTool Capability evaluation PASSED")


if __name__ == "__main__":
    main()
