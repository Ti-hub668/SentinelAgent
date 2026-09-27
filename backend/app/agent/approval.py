from app.schemas.policy import (
    HumanApprovalRequest,
)


def approve_request(
    approval: HumanApprovalRequest,
    *,
    reviewer: str,
    reason: str,
) -> HumanApprovalRequest:
    """
    Explicitly approve one policy-gated ToolRequest.
    """

    if approval.status != "pending":
        raise ValueError(
            "Only pending approval requests "
            "can be approved."
        )

    return approval.model_copy(
        update={
            "status": "approved",
            "reviewer": reviewer,
            "review_reason": reason,
        }
    )


def reject_request(
    approval: HumanApprovalRequest,
    *,
    reviewer: str,
    reason: str,
) -> HumanApprovalRequest:
    """
    Explicitly reject one policy-gated ToolRequest.
    """

    if approval.status != "pending":
        raise ValueError(
            "Only pending approval requests "
            "can be rejected."
        )

    return approval.model_copy(
        update={
            "status": "rejected",
            "reviewer": reviewer,
            "review_reason": reason,
        }
    )