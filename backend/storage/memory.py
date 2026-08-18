import threading
from collections import defaultdict

from storage.base import ScanRecord, ScanStore


class MemoryStore(ScanStore):
    """In-memory fallback so auth + history work locally without Supabase."""

    MAX_SCANS_PER_USER = 50

    def __init__(self):
        self._lock = threading.Lock()
        self._scans: dict[str, list[ScanRecord]] = defaultdict(list)

    def save_scan(
        self,
        user_id: str,
        scan_id: str,
        filename: str,
        source_type: str,
        findings,
        risk_score: int,
    ) -> None:
        record = ScanRecord(
            scan_id=scan_id,
            filename=filename,
            source_type=source_type,
            total_issues=len(findings),
            risk_score=risk_score,
            findings=findings,
        )
        with self._lock:
            bucket = self._scans[user_id]
            bucket.insert(0, record)
            del bucket[self.MAX_SCANS_PER_USER :]

    def list_scans(self, user_id: str) -> list[ScanRecord]:
        with self._lock:
            return [
                ScanRecord(
                    scan_id=r.scan_id,
                    filename=r.filename,
                    source_type=r.source_type,
                    total_issues=r.total_issues,
                    risk_score=r.risk_score,
                    created_at=r.created_at,
                )
                for r in self._scans.get(user_id, [])
            ]

    def get_scan(self, user_id: str, scan_id: str) -> ScanRecord | None:
        with self._lock:
            for r in self._scans.get(user_id, []):
                if r.scan_id == scan_id:
                    return r.model_copy(deep=True)
        return None

    def delete_scan(self, user_id: str, scan_id: str) -> bool:
        with self._lock:
            bucket = self._scans.get(user_id, [])
            for i, r in enumerate(bucket):
                if r.scan_id == scan_id:
                    del bucket[i]
                    return True
        return False