from datetime import datetime

from models import Finding
from storage.base import ScanRecord, ScanStore

_VALID_SEVERITIES = {"Critical", "High", "Medium", "Low"}


def _sev(value) -> str:
    return value if value in _VALID_SEVERITIES else "Medium"


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class SupabaseStore(ScanStore):
    """Persists scans via the Supabase Postgres REST API (service role key)."""

    def __init__(self, url: str, service_role_key: str):
        from supabase import create_client

        self.client = create_client(url, service_role_key)

    def save_scan(
        self,
        user_id: str,
        scan_id: str,
        filename: str,
        source_type: str,
        findings: list[Finding],
        risk_score: int,
    ) -> None:
        res = self.client.table("scans").insert(
            {
                "scan_id": scan_id,
                "user_id": user_id,
                "filename": filename,
                "source_type": source_type,
                "total_issues": len(findings),
                "risk_score": risk_score,
            }
        ).execute()
        scan_pk = res.data[0]["id"]
        if findings:
            self.client.table("findings").insert(
                [
                    {
                        "scan_id": scan_pk,
                        "user_id": user_id,
                        "type": f.type,
                        "severity": f.severity,
                        "file": f.file,
                        "line": f.line,
                        "explanation": f.explanation,
                        "suggested_fix": f.suggested_fix,
                        "confidence": f.confidence,
                        "source": f.source,
                        "code_snippet": f.code_snippet,
                        "finding_order": i,
                    }
                    for i, f in enumerate(findings)
                ]
            ).execute()

    def list_scans(self, user_id: str) -> list[ScanRecord]:
        res = (
            self.client.table("scans")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return [
            ScanRecord(
                scan_id=r["scan_id"],
                filename=r.get("filename") or "",
                source_type=r.get("source_type") or "snippet",
                total_issues=r.get("total_issues", 0),
                risk_score=r.get("risk_score", 0),
                created_at=_parse_dt(r["created_at"]),
            )
            for r in res.data
        ]

    def get_scan(self, user_id: str, scan_id: str) -> ScanRecord | None:
        res = (
            self.client.table("scans")
            .select("*")
            .eq("user_id", user_id)
            .eq("scan_id", scan_id)
            .execute()
        )
        if not res.data:
            return None
        row = res.data[0]
        findings: list[Finding] = []
        fres = (
            self.client.table("findings")
            .select("*")
            .eq("scan_id", row["id"])
            .order("finding_order")
            .execute()
        )
        for fr in fres.data:
            findings.append(
                Finding(
                    type=fr.get("type") or "Unknown",
                    severity=_sev(fr.get("severity")),
                    file=fr.get("file") or "",
                    line=fr.get("line", 0),
                    explanation=fr.get("explanation") or "",
                    suggested_fix=fr.get("suggested_fix"),
                    confidence=fr.get("confidence") or "high",
                    source=fr.get("source") or "unknown",
                    code_snippet=fr.get("code_snippet"),
                )
            )
        return ScanRecord(
            scan_id=row["scan_id"],
            filename=row.get("filename") or "",
            source_type=row.get("source_type") or "snippet",
            total_issues=row.get("total_issues", 0),
            risk_score=row.get("risk_score", 0),
            created_at=_parse_dt(row["created_at"]),
            findings=findings,
        )

    def delete_scan(self, user_id: str, scan_id: str) -> bool:
        res = (
            self.client.table("scans")
            .delete()
            .eq("user_id", user_id)
            .eq("scan_id", scan_id)
            .execute()
        )
        return bool(res.data)