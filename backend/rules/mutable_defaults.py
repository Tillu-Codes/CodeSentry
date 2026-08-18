import ast

from models import Finding
from rules.base import make_finding

MUTABLE_FACTORIES = {"list", "dict", "set", "bytearray", "Counter", "defaultdict"}


def _is_mutable_default(default: ast.AST) -> bool:
    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
        return True
    if isinstance(default, ast.Call):
        func = default.func
        if isinstance(func, ast.Name) and func.id in MUTABLE_FACTORIES:
            return True
        if isinstance(func, ast.Attribute) and func.attr in ("OrderedDict", "defaultdict"):
            return True
    return False


class _MutableDefaultsVisitor(ast.NodeVisitor):
    def __init__(self, code: str, filename: str):
        self.code = code
        self.filename = filename
        self.findings: list[Finding] = []

    def _check(self, node: ast.FunctionDef) -> None:
        positional = list(node.args.defaults)
        positional_names = [a.arg for a in node.args.args][-len(positional):] if positional else []
        kwonly_names = [
            a.arg for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is not None
        ]
        kwonly_defaults = [d for d in node.args.kw_defaults if d is not None]

        for arg_name, default in zip(positional_names, positional):
            self._flag(node, arg_name, default)
        for arg_name, default in zip(kwonly_names, kwonly_defaults):
            self._flag(node, arg_name, default)

    def _flag(self, node: ast.FunctionDef, arg_name: str, default: ast.AST) -> None:
        if not _is_mutable_default(default):
            return
        self.findings.append(
            make_finding(
                finding_type="Mutable Default Argument",
                severity="Medium",
                filename=self.filename,
                line=node.lineno,
                code=self.code,
                explanation=(
                    f"The default value of `{arg_name}` is a mutable object, created once "
                    "at function definition time and shared across all calls. Mutations "
                    "accumulate between calls, producing subtle bugs. Use None as the "
                    "sentinel and build the mutable inside the body."
                ),
                suggested_fix=(
                    f"def {node.name}({arg_name}=None):\n"
                    f"    if {arg_name} is None:\n"
                    f"        {arg_name} = []\n"
                ),
                source="ast.mutable_defaults",
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)


def detect_mutable_defaults(code: str, filename: str = "main.py") -> list[Finding]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    visitor = _MutableDefaultsVisitor(code, filename)
    visitor.visit(tree)
    return visitor.findings