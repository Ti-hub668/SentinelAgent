import json
from pathlib import Path

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.finding import Finding


OUTPUT_PATH = Path(
    "evals/real_findings_raw.json"
)


def export_real_findings() -> None:
    """
    从 SentinelAgent 数据库导出真实 Finding，
    生成待人工标注的评测原始数据。
    """

    db = SessionLocal()

    try:
        statement = (
            select(Finding)
            .order_by(Finding.id.asc())
        )

        findings = (
            db.execute(statement)
            .scalars()
            .all()
        )

        cases = []

        for index, finding in enumerate(
            findings,
            start=1
        ):
            case = {
                "id": (
                    f"real_{index:04d}"
                ),
                "finding_id": finding.id,
                "source": finding.source,
                "finding_type": (
                    finding.finding_type
                ),
                "title": finding.title,
                "severity": finding.severity,
                "target": finding.target,
                "description": (
                    finding.description
                ),
                "evidence": finding.evidence,
                "remediation": (
                    finding.remediation
                ),
                "risk_score": (
                    finding.risk_score
                ),
                "risk_level": (
                    finding.risk_level
                ),
                "risk_reason": (
                    finding.risk_reason
                ),

                # 暂时不让 AI 自动打标签。
                # Day 12 后面由人工完成。
                "expected_verdict": None
            }

            cases.append(case)

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            OUTPUT_PATH,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                cases,
                file,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"Exported findings: "
            f"{len(cases)}"
        )

        print(
            f"Saved to: "
            f"{OUTPUT_PATH}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    export_real_findings()