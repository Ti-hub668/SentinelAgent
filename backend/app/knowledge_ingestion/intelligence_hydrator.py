from typing import Any

from app.knowledge_ingestion.epss import (
    download_epss,
    save_epss,
)
from app.knowledge_ingestion.epss_lookup import (
    EPSSLookup,
)
from app.knowledge_ingestion.epss_normalizer import (
    normalize_epss,
    save_record as save_epss_record,
)
from app.knowledge_ingestion.nvd_cve import (
    download_cve,
    save_cve,
    validate_cve_id,
)
from app.knowledge_ingestion.nvd_lookup import (
    NVDLookup,
)
from app.knowledge_ingestion.nvd_normalizer import (
    normalize_nvd,
    save_record as save_nvd_record,
)


class IntelligenceHydrator:
    """
    Cache-first official intelligence hydration.

    Responsibilities:
    - use normalized local cache first
    - download missing NVD / FIRST EPSS data
    - normalize and persist downloaded data
    - fail open when an official source is unavailable

    This class never raises network errors back into
    the investigation workflow.
    """

    def __init__(
        self,
        timeout: float = 30.0,
    ) -> None:
        self.timeout = timeout

        self.nvd_lookup = NVDLookup()
        self.epss_lookup = EPSSLookup()

    @staticmethod
    def _result(
        *,
        status: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "error": error,
        }

    def ensure_nvd(
        self,
        cve_id: str,
    ) -> dict[str, Any]:
        """
        Ensure one normalized NVD record exists locally.
        """

        try:
            cve_id = validate_cve_id(
                cve_id
            )

        except ValueError as exc:
            return self._result(
                status="invalid",
                error=str(exc),
            )

        try:
            existing = (
                self.nvd_lookup.get(
                    cve_id
                )
            )

            if existing is not None:
                return self._result(
                    status="cached",
                )

        except Exception as exc:
            return self._result(
                status="unavailable",
                error=(
                    f"Local NVD cache error: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        try:
            raw_data = download_cve(
                cve_id,
                timeout=self.timeout,
            )

            save_cve(
                cve_id,
                raw_data,
            )

            record = normalize_nvd(
                raw_data
            )

            save_nvd_record(
                record
            )

            return self._result(
                status="downloaded",
            )

        except Exception as exc:
            return self._result(
                status="unavailable",
                error=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    def ensure_epss(
        self,
        cve_id: str,
    ) -> dict[str, Any]:
        """
        Ensure one normalized FIRST EPSS record exists locally.
        """

        try:
            cve_id = validate_cve_id(
                cve_id
            )

        except ValueError as exc:
            return self._result(
                status="invalid",
                error=str(exc),
            )

        try:
            existing = (
                self.epss_lookup.get(
                    cve_id
                )
            )

            if existing is not None:
                return self._result(
                    status="cached",
                )

        except Exception as exc:
            return self._result(
                status="unavailable",
                error=(
                    f"Local EPSS cache error: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        try:
            raw_data = download_epss(
                cve_id,
                timeout=self.timeout,
            )

            save_epss(
                cve_id,
                raw_data,
            )

            record = normalize_epss(
                raw_data
            )

            save_epss_record(
                record
            )

            return self._result(
                status="downloaded",
            )

        except Exception as exc:
            return self._result(
                status="unavailable",
                error=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    def ensure_cve(
        self,
        cve_id: str,
    ) -> dict[str, Any]:
        """
        Hydrate all supported structured intelligence
        sources for one CVE.

        CISA KEV is not hydrated here because SentinelAgent
        currently uses the complete local KEV catalog.
        """

        normalized = (
            str(cve_id)
            .strip()
            .upper()
        )

        return {
            "cve_id": normalized,

            "nvd": self.ensure_nvd(
                normalized
            ),

            "epss": self.ensure_epss(
                normalized
            ),
        }

    def ensure_many(
        self,
        cve_ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        Hydrate multiple CVEs independently.

        One failed source/CVE does not stop others.
        """

        results = []

        for cve_id in cve_ids:
            results.append(
                self.ensure_cve(
                    cve_id
                )
            )

        return results