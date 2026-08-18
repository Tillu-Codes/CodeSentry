from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from models import Finding


class ScanRecord(BaseModel):
    scan_id: str
    filename: str = ""
    source_type: str = "snippet"
    total_issues: int = 0
    risk_score: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    findings: list[Finding] | None = None


class ScanStore(ABC):
    """Persistence interface for scan history. Implementations: Supabase / in-memory."""

    @abstractmethod
    def save_scan(
        self,
        user_id: str,
        scan_id: str,
        filename: str,
        source_type: str,
        findings: list[Finding],
        risk_score: int,
    ) -> None: ...

    @abstractmethod
    def list_scans(self, user_id: str) -> list[ScanRecord]: ...

    @abstractmethod
    def get_scan(self, user_id: str, scan_id: str) -> ScanRecord | None: ...

    @abstractmethod
    def delete_scan(self, user_id: str, scan_id: str) -> bool: ...