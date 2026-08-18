from models import Finding, Severity


def line_snippet(code: str, lineno: int) -> str:
    lines = code.splitlines()
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def make_finding(
    *,
    finding_type: str,
    severity: Severity,
    filename: str,
    line: int,
    explanation: str,
    code: str,
    suggested_fix: str | None = None,
    source: str,
    confidence: str = "high",
) -> Finding:
    return Finding(
        type=finding_type,
        severity=severity,
        file=filename,
        line=line,
        explanation=explanation,
        suggested_fix=suggested_fix,
        confidence=confidence,
        source=source,
        code_snippet=line_snippet(code, line),
    )