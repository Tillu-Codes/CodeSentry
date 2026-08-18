from engines.bandit_engine import run_bandit
from engines.detect_secrets_engine import run_detect_secrets
from llm.enrichment import enrich_findings, suggest_missed_issues
from llm.factory import get_llm_client
from models import SEVERITY_RANK, Finding
from rules.bare_except import detect_bare_except
from rules.inefficient_code import detect_inefficient_code
from rules.mutable_defaults import detect_mutable_defaults
from rules.sql_injection import detect_sql_injection
from rules.syntax_error import detect_syntax_error

RISK_WEIGHTS = {"Critical": 10, "High": 6, "Medium": 3, "Low": 1}


def compute_risk_score(findings: list[Finding]) -> int:
    score = sum(
        RISK_WEIGHTS[f.severity] for f in findings if f.confidence != "ai-suggested"
    )
    return min(100, max(0, score))


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen = set()
    unique = []
    for f in findings:
        key = (f.source, f.type, f.line)
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique


def drop_ai_duplicates(findings: list[Finding]) -> list[Finding]:
    rule_keys = {(f.type, f.line) for f in findings if f.source != "llm"}
    out = []
    for f in findings:
        if f.source == "llm" and (f.type, f.line) in rule_keys:
            continue
        out.append(f)
    return out


def analyze_code(
    code: str,
    filename: str,
    enrich: bool = True,
    llm_missed_issues: bool = True,
) -> list[Finding]:
    """Run the full detection pipeline over one file: rules -> LLM enrichment."""
    findings: list[Finding] = []
    findings += detect_syntax_error(code, filename)
    findings += run_bandit(code, filename)
    findings += run_detect_secrets(code, filename)
    findings += detect_sql_injection(code, filename)
    findings += detect_bare_except(code, filename)
    findings += detect_mutable_defaults(code, filename)
    findings += detect_inefficient_code(code, filename)

    findings = dedupe(findings)

    client = get_llm_client()
    if enrich:
        findings = enrich_findings(findings, code, client)
    if llm_missed_issues:
        findings += suggest_missed_issues(code, filename, client)

    findings = drop_ai_duplicates(findings)
    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.line))
    return findings