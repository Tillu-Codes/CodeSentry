from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["Critical", "High", "Medium", "Low"]

SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class Finding(BaseModel):
    type: str
    severity: Severity
    file: str
    line: int
    explanation: str
    suggested_fix: Optional[str] = None
    confidence: str = Field(default="high", description="high for deterministic rule hits")
    source: str = Field(description="which engine/rule produced this finding")
    code_snippet: Optional[str] = None


class ScanRequest(BaseModel):
    code: str = Field(..., description="Python source code to analyze")
    filename: str = Field(default="main.py", description="Name to attribute the code to")
    enrich: bool = Field(
        default=True,
        description="Use the LLM to rewrite explanations and suggest fixes for rule findings",
    )
    llm_missed_issues: bool = Field(
        default=True,
        description="Ask the LLM for issues rules may have missed (tagged ai-suggested)",
    )


class ScanResponse(BaseModel):
    scan_id: Optional[str] = Field(default=None, description="Persistent history id, only for authenticated scans")
    filename: str
    total_issues: int
    risk_score: int = Field(ge=0, le=100)
    findings: list[Finding]


class RepoScanRequest(BaseModel):
    github_url: Optional[str] = None
    branch: Optional[str] = None
    enrich: bool = True
    llm_missed_issues: bool = True


class FileResult(BaseModel):
    file: str
    total_issues: int


class ScanJob(BaseModel):
    scan_id: str
    status: Literal["queued", "running", "done", "failed"]
    total_files: int = 0
    scanned_files: int = 0
    total_issues: int = 0
    risk_score: int = 0
    findings: list[Finding] = Field(default_factory=list)
    per_file: list[FileResult] = Field(default_factory=list)
    error: Optional[str] = None
    user_id: Optional[str] = None
    label: str = ""
    source_type: str = "repo"


class ScanListResponse(BaseModel):
    scans: list[dict]
    storage: str