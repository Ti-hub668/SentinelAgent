from sqlalchemy import (
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine

from app.models.execution_claim import (
    ExecutionClaim,
)
from app.models.investigation_event import (
    InvestigationEvent,
)


ALLOWED_TOOL_NAMES = {
    "create_ticket",
    "notify",
    "block_ip",
    "manual_review",
}


def ensure_execution_claim_tool_name(
    engine: Engine,
) -> dict:
    """
    Ensure execution_claims.tool_name exists and
    safely backfill historical claims when an
    existing ledger event proves the tool name.

    This migration intentionally uses SQLAlchemy
    Core instead of ORM mutation so it does not
    depend on loading the complete model graph.
    """

    inspector = inspect(engine)

    columns = {
        column["name"]
        for column in inspector.get_columns(
            "execution_claims"
        )
    }

    column_created = False

    if "tool_name" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE execution_claims "
                    "ADD COLUMN tool_name "
                    "VARCHAR(64) NULL"
                )
            )

        column_created = True

    claim_table = (
        ExecutionClaim.__table__
    )

    event_table = (
        InvestigationEvent.__table__
    )

    backfilled = 0

    with engine.begin() as connection:
        claims = (
            connection.execute(
                select(
                    claim_table.c.id,
                    claim_table.c.event_id,
                ).where(
                    claim_table.c.tool_name.is_(
                        None
                    )
                )
            )
            .mappings()
            .all()
        )

        for claim in claims:
            event_id = claim["event_id"]

            if event_id is None:
                continue

            metadata = connection.execute(
                select(
                    event_table.c.event_metadata
                ).where(
                    event_table.c.id
                    == event_id
                )
            ).scalar_one_or_none()

            if not isinstance(
                metadata,
                dict,
            ):
                continue

            tool_name = metadata.get(
                "tool_name"
            )

            if (
                tool_name
                not in ALLOWED_TOOL_NAMES
            ):
                continue

            connection.execute(
                update(
                    claim_table
                )
                .where(
                    claim_table.c.id
                    == claim["id"]
                )
                .values(
                    tool_name=tool_name
                )
            )

            backfilled += 1

    return {
        "column_created":
            column_created,
        "backfilled":
            backfilled,
    }