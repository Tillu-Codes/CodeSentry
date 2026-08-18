from models import Finding
from llm.enrichment import (
    _extract_json,
    build_enrichment_prompt,
    enrich_findings,
    suggest_missed_issues,
)
from llm.factory import MockClient, NullClient, get_llm_client


class FakeClient:
    name = "fake"
    is_available = True

    def __init__(self, response: str):
        self.response = response

    def generate(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        return self.response


def _finding(fid, line=1):
    return Finding(
        type="SQL Injection",
        severity="Critical",
        file="x.py",
        line=line,
        explanation="rule explanation",
        source=fid,
    )


def test_extract_json_with_fences():
    text = '```json\n[{"index": 0, "explanation": "hi"}]\n```'
    assert _extract_json(text) == [{"index": 0, "explanation": "hi"}]


def test_extract_json_with_prose():
    text = 'Sure! Here you go:\n\n[{"index": 1, "explanation": "a", "suggested_fix": "b"}]'
    data = _extract_json(text)
    assert data == [{"index": 1, "explanation": "a", "suggested_fix": "b"}]


def test_extract_json_garbage():
    assert _extract_json("no json here") is None


def test_enrich_findings_updates_explanation_and_fix():
    findings = [_finding("ast.sql_injection", line=2)]
    code = 'cur.execute(f"SELECT * FROM t WHERE id = {uid}")\n'
    client = FakeClient(
        '[{"index": 0, "explanation": "LLM explanation.", "suggested_fix": "use_params()"}]'
    )
    enriched = enrich_findings(findings, code, client)
    assert enriched[0].explanation == "LLM explanation."
    assert enriched[0].suggested_fix == "use_params()"
    assert enriched[0].severity == "Critical"
    assert enriched[0].type == "SQL Injection"


def test_enrich_findings_keeps_rule_fields_on_bad_response():
    findings = [_finding("ast.sql_injection")]
    client = FakeClient("totally not json")
    enriched = enrich_findings(findings, "print(1)", client)
    assert enriched[0].explanation == "rule explanation"


def test_enrich_findings_noop_when_unavailable():
    findings = [_finding("ast.sql_injection")]
    enriched = enrich_findings(findings, "print(1)", NullClient())
    assert enriched[0].explanation == "rule explanation"


def test_suggest_missed_issues_tags_ai_suggested():
    code = "x = 1\nif x = 2:\n    pass\n"
    client = FakeClient(
        '[{"type": "Assignment in condition", "severity": "Medium", "line": 2, '
        '"explanation": "Likely meant ==", "suggested_fix": "if x == 2:"}]'
    )
    findings = suggest_missed_issues(code, "x.py", client)
    assert len(findings) == 1
    assert findings[0].confidence == "ai-suggested"
    assert findings[0].source == "llm"
    assert findings[0].severity == "Medium"
    assert findings[0].line == 2


def test_suggest_missed_issues_ignores_bad_lines_and_severity():
    code = "a = 1\n"
    client = FakeClient(
        '[{"type": "A", "severity": "Bogus", "line": 999, "explanation": "e", "suggested_fix": "f"},'
        '{"type": "B", "severity": "Bogus", "line": 1, "explanation": "e2", "suggested_fix": "f2"}]'
    )
    findings = suggest_missed_issues(code, "x.py", client)
    assert len(findings) == 1
    assert findings[0].severity == "Medium"
    assert findings[0].type == "B"


def test_get_llm_client_defaults_to_null(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert isinstance(get_llm_client(), NullClient)


def test_get_llm_client_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    client = get_llm_client()
    assert isinstance(client, MockClient)
    assert client.is_available


def test_mock_client_returns_canned_enrichment():
    client = MockClient()
    prompt = build_enrichment_prompt('cur.execute(f"SELECT * FROM t WHERE id = {uid}")', [_finding("ast.sql_injection")])
    import json

    data = json.loads(client.generate(prompt))
    assert data[0]["index"] == 0
    assert data[0]["explanation"].startswith("[mock]")