from app.agent.context_builder import build_investigation_context
from app.db.database import SessionLocal


def main():
    db = SessionLocal()

    try:
        # --------------------------------------------------
        # Case 1: real finding should build successfully
        # --------------------------------------------------

        context = build_investigation_context(
            db,
            finding_id=62,
        )

        assert context.finding_id == 62
        assert context.finding.title == "OpenAPI - Detect"

        assert context.asset.id == context.finding.asset_id

        assert (
            context.scan_task.id
            == context.finding.scan_task_id
        )

        assert isinstance(
            context.open_ports,
            list,
        )

        assert isinstance(
            context.related_findings,
            list,
        )

        print(
            "[PASS] real finding context build"
        )

        # --------------------------------------------------
        # Case 2: nonexistent finding should fail fast
        # --------------------------------------------------

        try:
            build_investigation_context(
                db,
                finding_id=999999,
            )

        except ValueError:
            print(
                "[PASS] nonexistent finding rejected"
            )

        else:
            raise AssertionError(
                "Missing finding was not rejected."
            )

        print(
            "\nContextBuilder evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()