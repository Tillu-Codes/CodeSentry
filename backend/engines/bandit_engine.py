import json
import os
import subprocess
import sys
import tempfile

from models import Finding, Severity

SEVERITY_MAP = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}
CRITICAL_TEST_IDS = {"B105", "B106", "B107", "B608"}
DEFAULT_SKIPS = {"B101", "B110"}


def bandit_skips() -> set[str]:
    extra = os.getenv("BANDIT_SKIPS", "")
    return DEFAULT_SKIPS | {s.strip() for s in extra.split(",") if s.strip()}


def run_bandit(code: str, filename: str = "main.py") -> list[Finding]:
    safe_name = os.path.basename(filename) or "main.py"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, safe_name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            args = [sys.executable, "-m", "bandit", "-f", "json", "-q", "--exit-zero"]
            skips = bandit_skips()
            if skips:
                args += ["--skip", ",".join(sorted(skips))]
            args.append(path)
            proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
            data = json.loads(proc.stdout)
    except Exception:
        return []

    findings: list[Finding] = []
    for res in data.get("results", []):
        test_id = str(res.get("test_id", "B000"))
        raw_severity = str(res.get("issue_severity", "")).upper()
        if test_id in CRITICAL_TEST_IDS:
            severity: Severity = "Critical"
        else:
            severity = SEVERITY_MAP.get(raw_severity, "Medium")
        findings.append(
            Finding(
                type=test_id,
                severity=severity,
                file=filename,
                line=int(res.get("line_number", 0) or 0),
                explanation=str(res.get("issue_text", "")),
                confidence=str(res.get("issue_confidence", "")).lower() or "high",
                source="bandit",
                code_snippet=(res.get("code") or "").strip() or None,
            )
        )
    return findings