import ast

from models import Finding
from rules.base import make_finding


def detect_syntax_error(code: str, filename: str = "main.py") -> list[Finding]:
    """Report Python files that fail to parse, so broken code never passes silently."""
    try:
        ast.parse(code, filename=filename, mode="exec")
    except SyntaxError as exc:
        line = exc.lineno or 1
        offset = exc.offset or 0
        explanation = (
            f"Python could not parse this file: {exc.msg}"
            + (f" (line {line}" + (f", column {offset}" if offset else "") + ")" if line else "")
            + ". The code will not run."
        )
        return [
            make_finding(
                finding_type="Syntax Error",
                severity="High",
                filename=filename,
                line=line,
                code=code,
                explanation=explanation,
                suggested_fix=(
                    "Fix the reported line, then re-check the code right after it — a syntax "
                    "error often masks further issues on subsequent lines. Look for unbalanced "
                    "brackets/parentheses, missing colons, mismatched quotes, or inconsistent "
                    "indentation."
                ),
                source="ast.syntax",
            )
        ]
    except Exception:
        return []
    return []