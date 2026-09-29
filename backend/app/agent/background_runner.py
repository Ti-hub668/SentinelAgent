from app.agent.ledger import (
    fail_investigation_run,
    record_investigation_event,
)
from app.agent.orchestrator import (
    run_existing_agent_workflow,
)
from app.db.database import SessionLocal


def run_agent_workflow_background(
    *,
    run_id: int,
    finding_id: int,
) -> None:
    """
    Execute one Agent workflow outside the
    request-scoped SQLAlchemy session.

    FastAPI BackgroundTasks runs after the HTTP
    response has been returned, so the background
    workflow must own its database session.
    """

    db = SessionLocal()

    try:
        run_existing_agent_workflow(
            db,
            finding_id=finding_id,
            run_id=run_id,
        )

    except Exception as exc:
        db.rollback()

        error_message = (
            f"{type(exc).__name__}: {exc}"
        )

        try:
            record_investigation_event(
                db,
                run_id=run_id,
                event_type="workflow_failed",
                node_name="background_runner",
                status="failed",
                summary=error_message,
                event_metadata={
                    "finding_id": finding_id,
                    "execution_mode": (
                        "fastapi_background_task"
                    ),
                },
            )

            fail_investigation_run(
                db,
                run_id=run_id,
                error_message=error_message,
            )

        except Exception:
            db.rollback()
            raise

    finally:
        db.close()