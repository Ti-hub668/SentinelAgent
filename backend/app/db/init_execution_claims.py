"""Additive Day43 schema initialization; does not alter or delete existing data."""
from app.db.database import engine
from app.models.investigation_run import InvestigationRun  # noqa: F401
from app.models.investigation_event import InvestigationEvent  # noqa: F401
from app.models.execution_claim import ExecutionClaim


def main():
    ExecutionClaim.__table__.create(engine, checkfirst=True)
    print("execution_claims table is available")


if __name__ == "__main__":
    main()
