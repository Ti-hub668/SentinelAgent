from pydantic import ValidationError

from app.agent.tool_broker import (
    execute_policy_result,
)
from app.agent.tool_registry import (
    TOOL_REGISTRY,
    validate_tool_request_parameters,
)
from app.schemas.policy import (
    ToolPolicyResult,
)
from app.schemas.response_plan import (
    ToolRequest,
)


EXPECTED_TOOLS = {
    "create_ticket",
    "notify",
    "block_ip",
    "manual_review",
}


def make_allow_result(
    request: ToolRequest,
) -> ToolPolicyResult:
    return ToolPolicyResult(
        request_index=0,
        tool_request=request,
        decision="ALLOW",
        reason="Evaluator ALLOW decision.",
        requires_human_approval=False,
    )


def test_registry_complete():
    assert (
        set(TOOL_REGISTRY.keys())
        == EXPECTED_TOOLS
    )

    print(
        "[PASS] registry contains all "
        "expected tools"
    )


def test_empty_parameter_contracts():
    for tool_name in (
        "create_ticket",
        "notify",
        "block_ip",
    ):
        request = ToolRequest(
            tool_name=tool_name,
            target="finding:62",
            reason="Contract evaluator.",
        )

        validated = (
            validate_tool_request_parameters(
                request
            )
        )

        assert (
            validated.parameters
            == {}
        )

    print(
        "[PASS] target-based tools preserve "
        "empty parameter contracts"
    )


def test_manual_review_contract():
    request = ToolRequest(
        tool_name="manual_review",
        target="finding:62",
        reason="Manual review evaluator.",
        parameters={
            "finding_id": 62,
            "grounded_verdict":
                "likely_true_positive",
        },
    )

    validated = (
        validate_tool_request_parameters(
            request
        )
    )

    assert (
        validated.parameters[
            "finding_id"
        ]
        == 62
    )

    print(
        "[PASS] manual_review typed "
        "parameters accepted"
    )


def test_extra_parameter_rejected():
    request = ToolRequest(
        tool_name="create_ticket",
        target="finding:62",
        reason="Extra parameter evaluator.",
        parameters={
            "dangerous_option": True,
        },
    )

    try:
        validate_tool_request_parameters(
            request
        )

    except ValidationError:
        print(
            "[PASS] unexpected parameter "
            "rejected"
        )
        return

    raise AssertionError(
        "Unexpected parameter was accepted."
    )


def test_wrong_type_rejected():
    request = ToolRequest(
        tool_name="manual_review",
        target="finding:62",
        reason="Strict type evaluator.",
        parameters={
            "finding_id": "62",
            "grounded_verdict":
                "likely_true_positive",
        },
    )

    try:
        validate_tool_request_parameters(
            request
        )

    except ValidationError:
        print(
            "[PASS] wrong parameter type "
            "rejected"
        )
        return

    raise AssertionError(
        "Wrong parameter type was accepted."
    )


def test_valid_request_reaches_executor():
    request = ToolRequest(
        tool_name="create_ticket",
        target="finding:62",
        reason="Create evaluator ticket.",
    )

    policy_result = (
        make_allow_result(
            request
        )
    )

    result = execute_policy_result(
        policy_result,
        finding_id=62,
        approvals=[],
    )

    assert result.status == "simulated"
    assert result.authorized is True
    assert result.executed is True

    print(
        "[PASS] validated request reached "
        "dry-run adapter"
    )


def test_invalid_request_blocked():
    request = ToolRequest(
        tool_name="create_ticket",
        target="finding:62",
        reason="Invalid evaluator request.",
        parameters={
            "dangerous_option": True,
        },
    )

    policy_result = (
        make_allow_result(
            request
        )
    )

    result = execute_policy_result(
        policy_result,
        finding_id=62,
        approvals=[],
    )

    assert result.status == "blocked"
    assert result.authorized is False
    assert result.executed is False

    assert (
        "parameter validation failed"
        in result.message.lower()
    )

    print(
        "[PASS] invalid request blocked "
        "before adapter"
    )


def main():
    test_registry_complete()

    test_empty_parameter_contracts()

    test_manual_review_contract()

    test_extra_parameter_rejected()

    test_wrong_type_rejected()

    test_valid_request_reaches_executor()

    test_invalid_request_blocked()

    print(
        "\nTool Registry evaluation PASSED"
    )


if __name__ == "__main__":
    main()