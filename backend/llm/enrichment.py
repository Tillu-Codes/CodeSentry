import json
import re

from models import Finding
from llm.base import LLMClient

SEVERITY_VALUES = {"Critical", "High", "Medium", "Low"}
SYSTEM_PROMPT = (
    "You are a precise Python code reviewer. You only explain and fix findings; "
    "you never decide severity for rule-based findings. Keep answers concise and concrete."
)


def _extract_json(text: str):
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _code_line(code: str, lineno: int) -> str:
    lines = code.splitlines()
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def build_enrichment_prompt(code: str, findings: list[Finding]) -> str:
    annotated = []
    for i, line in enumerate(code.splitlines(), start=1):
        markers = [f"{f.source}:{f.type}" for f in findings if f.line == i]
        suffix = f"   # <-- {', '.join(markers)}" if markers else ""
        annotated.append(f"{i:>4} | {line}{suffix}")
    finding_json = json.dumps(
        [
            {"index": i, "type": f.type, "severity": f.severity, "line": f.line, "source": f.source}
            for i, f in enumerate(findings)
        ],
        indent=1,
    )
    return "\n".join(
        [
            "You are a Python code reviewer. Below is a source file with line numbers, followed by",
            "findings already detected by deterministic rules (relevant lines are marked `# <--`).",
            "",
            "Return a JSON array with the SAME length and SAME indices as the findings list:",
            '[{"index": 0, "explanation": "...", "suggested_fix": "..."}]',
            "",
            "Constraints:",
            "- explanation: 1-3 plain-language sentences explaining why it is a problem.",
            "- suggested_fix: a short corrected snippet or actionable instruction, never the whole file.",
            "- Do not add, remove, or reorder entries; do not invent new findings.",
            "- Output ONLY the JSON array.",
            "",
            "FINDINGS:",
            finding_json,
            "",
            "CODE:",
            "\n".join(annotated),
        ]
    )


def build_missed_issues_prompt(code: str, filename: str) -> str:
    return "\n".join(
        [
            "You are a Python code reviewer. Review this file for bugs, security vulnerabilities,",
            "and inefficiencies that static-analysis rules commonly MISS (logic errors, wrong",
            "comparisons, off-by-one, unsafe deserialization, API misuse, race conditions).",
            "",
            'Return a JSON array (possibly empty) of issues, each like:',
            '{"type": "...", "severity": "Critical|High|Medium|Low", "line": <1-based int>, "explanation": "...", "suggested_fix": "..."}',
            "",
            "Constraints:",
            "- Only report issues you are genuinely confident about; quality over quantity.",
            "- line must be a valid line number in the file.",
            "- suggested_fix must be a short corrected snippet or clear instruction.",
            "- Output ONLY the JSON array.",
            "",
            f"FILE: {filename}",
            "CODE:",
            "\n".join(f"{i:>4} | {line}" for i, line in enumerate(code.splitlines(), start=1)),
        ]
    )


def enrich_findings(findings: list[Finding], code: str, client: LLMClient) -> list[Finding]:
    """Rewrite explanation + suggested_fix for rule findings. Never changes type/severity."""
    if not client.is_available or not findings or not code.strip():
        return findings
    try:
        text = client.generate(build_enrichment_prompt(code, findings), system=SYSTEM_PROMPT)
        data = _extract_json(text)
        if not isinstance(data, list):
            return findings
        by_index = {}
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("index"), int):
                by_index[item["index"]] = item
        for i, finding in enumerate(findings):
            item = by_index.get(i)
            if not isinstance(item, dict):
                continue
            explanation = item.get("explanation")
            fix = item.get("suggested_fix")
            if isinstance(explanation, str) and explanation.strip():
                finding.explanation = explanation.strip()
            if isinstance(fix, str) and fix.strip():
                finding.suggested_fix = fix.strip()
    except Exception:
        pass
    return findings


def suggest_missed_issues(code: str, filename: str, client: LLMClient) -> list[Finding]:
    """Ask the LLM for anything rules missed. Tagged ai-suggested, never affect risk score."""
    if not client.is_available or not code.strip():
        return []
    try:
        text = client.generate(build_missed_issues_prompt(code, filename), system=SYSTEM_PROMPT)
        data = _extract_json(text)
        if not isinstance(data, list):
            return []
    except Exception:
        return []

    line_count = len(code.splitlines())
    out: list[Finding] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            line = int(item.get("line", 0) or 0)
        except (TypeError, ValueError):
            continue
        if not 1 <= line <= line_count:
            continue
        severity = item.get("severity", "Medium")
        if severity not in SEVERITY_VALUES:
            severity = "Medium"
        fix = item.get("suggested_fix")
        out.append(
            Finding(
                type=str(item.get("type") or "Potential Issue"),
                severity=severity,
                file=filename,
                line=line,
                explanation=str(item.get("explanation") or "AI-suggested issue."),
                suggested_fix=str(fix) if fix else None,
                confidence="ai-suggested",
                source="llm",
                code_snippet=_code_line(code, line),
            )
        )
    return out