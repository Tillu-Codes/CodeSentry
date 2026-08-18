from engines.bandit_engine import run_bandit
from engines.detect_secrets_engine import run_detect_secrets


def test_bandit_catches_eval():
    code = '''def run(user_input):
    return eval(user_input)
'''
    findings = run_bandit(code)
    assert any(f.type == "B307" for f in findings)
    assert all(f.source == "bandit" for f in findings)


def test_bandit_clean_code():
    code = "x = 1 + 1\nprint(x)\n"
    assert run_bandit(code) == []


def test_detect_secrets_catches_keys():
    code = '''AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
STRIPE = "sk_live_4eC39HqLyjWDarjtT1zdp7dc"
'''
    findings = run_detect_secrets(code)
    assert len(findings) >= 2
    assert all(f.severity == "Critical" for f in findings)
    assert all(f.source == "detect-secrets" for f in findings)
    assert all(f.confidence == "high" for f in findings)


def test_detect_secrets_clean_code():
    code = "def add(a, b):\n    return a + b\n"
    assert run_detect_secrets(code) == []