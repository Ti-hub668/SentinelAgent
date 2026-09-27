from app.agent.context_builder import build_investigation_context
from app.agent.tools.intelligence_tool import (
    lookup_context_intelligence,
)
from app.agent.tools.rag_tool import (
    retrieve_context_knowledge,
)
from app.db.database import SessionLocal


TEST_FINDING_ID = 62


def main():
    db = SessionLocal()

    try:
        context = build_investigation_context(
            db,
            finding_id=TEST_FINDING_ID,
        )

        # --------------------------------------------------
        # RAG Tool
        # --------------------------------------------------

        rag_result = retrieve_context_knowledge(
            context,
            top_k=3,
        )

        assert rag_result.finding_id == TEST_FINDING_ID
        assert rag_result.query.strip()
        assert isinstance(rag_result.results, list)
        assert isinstance(rag_result.prompt_context, str)

        print(
            "[PASS] typed RAG tool"
        )

        # --------------------------------------------------
        # Structured Intelligence Tool
        # --------------------------------------------------

        intelligence_result = lookup_context_intelligence(
            context
        )

        assert (
            intelligence_result.finding_id
            == TEST_FINDING_ID
        )

        assert isinstance(
            intelligence_result.cve_ids,
            list,
        )

        assert isinstance(
            intelligence_result.cwe_ids,
            list,
        )

        assert isinstance(
            intelligence_result.kev_records,
            list,
        )

        assert isinstance(
            intelligence_result.nvd_records,
            list,
        )

        print(
            "[PASS] typed intelligence tool"
        )

        print(
            "\nAgent Tools evaluation PASSED"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()