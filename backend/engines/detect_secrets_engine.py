import os
import tempfile

from models import Finding


def run_detect_secrets(code: str, filename: str = "main.py") -> list[Finding]:
    safe_name = os.path.basename(filename) or "main.py"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, safe_name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            from detect_secrets import SecretsCollection
            from detect_secrets.settings import default_settings

            with default_settings():
                secrets = SecretsCollection()
                secrets.scan_file(path)
    except Exception:
        return []

    findings: list[Finding] = []
    for _fname, secret_list in secrets.data.items():
        for secret in secret_list:
            if getattr(secret, "is_secret", None) is False:
                continue
            secret_type = str(getattr(secret, "type", "unknown"))
            findings.append(
                Finding(
                    type=f"Hardcoded Secret ({secret_type})",
                    severity="Critical",
                    file=filename,
                    line=int(getattr(secret, "line_number", 0) or 0),
                    explanation=(
                        f"A potential {secret_type} was found on this line. Committing real "
                        "credentials to source code leaks them to anyone with repo access. "
                        "Use an environment variable or a secrets manager instead."
                    ),
                    suggested_fix=(
                        "import os\n"
                        f"value = os.environ['{secret_type.upper().replace(' ', '_')}_KEY']\n"
                        "# Keep secrets out of the codebase entirely."
                    ),
                    confidence="high",
                    source="detect-secrets",
                )
            )
    return findings