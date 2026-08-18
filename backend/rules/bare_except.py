import ast

from models import Finding
from rules.base import make_finding

BROAD_EXCEPTIONS = {"Exception", "BaseException", "StandardError", "OSError"}


def _is_pass_only(body: list[ast.stmt]) -> bool:
    if not body:
        return True
    if len(body) > 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return True
    if isinstance(stmt, (ast.Continue, ast.Break)):
        return True
    return False


def _is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    for t in types:
        if isinstance(t, ast.Name) and t.id in BROAD_EXCEPTIONS:
            return True
        if isinstance(t, ast.Attribute) and t.attr in BROAD_EXCEPTIONS:
            return True
    return False


class _ExceptVisitor(ast.NodeVisitor):
    def __init__(self, code: str, filename: str):
        self.code = code
        self.filename = filename
        self.findings: list[Finding] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.findings.append(
                make_finding(
                    finding_type="Bare Except",
                    severity="Medium",
                    filename=self.filename,
                    line=node.lineno,
                    code=self.code,
                    explanation=(
                        "A bare `except:` catches every exception, including "
                        "KeyboardInterrupt and SystemExit, and makes debugging hard. "
                        "Catch specific exceptions (ValueError, KeyError, ...) instead."
                    ),
                    suggested_fix=(
                        "except ValueError as e:\n"
                        "    # handle a specific, expected failure\n"
                    ),
                    source="ast.bare_except",
                )
            )
        elif _is_broad(node):
            if _is_pass_only(node.body):
                self.findings.append(
                    make_finding(
                        finding_type="Unhandled Exception",
                        severity="Medium",
                        filename=self.filename,
                        line=node.lineno,
                        code=self.code,
                        explanation=(
                            "An overly broad `except Exception:` block swallows the error "
                            "silently (empty/pass body). Failures disappear without trace, "
                            "making bugs very hard to find. Catch specific exceptions and "
                            "log or re-raise them."
                        ),
                        suggested_fix=(
                            "except SomeSpecificError as e:\n"
                            "    logger.exception('context message')\n"
                            "    raise\n"
                        ),
                        source="ast.bare_except",
                    )
                )
            else:
                self.findings.append(
                    make_finding(
                        finding_type="Overly Broad Except",
                        severity="Low",
                        filename=self.filename,
                        line=node.lineno,
                        code=self.code,
                        explanation=(
                            "Catching broad `Exception` hides unexpected errors and may "
                            "mask programming bugs. Narrow the caught types to what you "
                            "can actually handle."
                        ),
                        source="ast.bare_except",
                    )
                )
        self.generic_visit(node)


def detect_bare_except(code: str, filename: str = "main.py") -> list[Finding]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    visitor = _ExceptVisitor(code, filename)
    visitor.visit(tree)
    return visitor.findings