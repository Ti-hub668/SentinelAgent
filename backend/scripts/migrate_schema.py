from app.db.database import engine
from app.db.schema_migrations import (
    ensure_execution_claim_tool_name,
)


def main():
    result = (
        ensure_execution_claim_tool_name(
            engine
        )
    )

    print(
        "SentinelAgent schema migration"
    )

    print(
        "execution_claims.tool_name:",
        (
            "created"
            if result[
                "column_created"
            ]
            else "already present"
        ),
    )

    print(
        "historical claims backfilled:",
        result["backfilled"],
    )


if __name__ == "__main__":
    main()