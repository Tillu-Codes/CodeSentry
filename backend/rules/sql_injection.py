import ast

from models import Finding
from rules.base import make_finding

EXECUTE_METHODS = {"execute", "executemany", "executescript", "raw", "extra"}
SQL_TEXT_WRAPPERS = {"text", "raw", "sql"}


class _TaintTracker(ast.NodeVisitor):
    """Lightweight taint tracking: which names hold non-constant string expressions."""

    def __init__(self):
        self.string_names: set[str] = set()
        self.tainted: set[str] = set()

    def _is_stringish(self, node) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return True
        if isinstance(node, ast.JoinedStr):
            return True
        if isinstance(node, ast.Name):
            return node.id in self.string_names or node.id in self.tainted
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
            return self._is_stringish(node.left) or self._is_stringish(node.right)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
        ):
            return True
        return False

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.string_names.add(target.id)
                elif self._is_stringish(node.value):
                    self.tainted.add(target.id)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if (
            isinstance(node.op, ast.Add)
            and isinstance(node.target, ast.Name)
            and (node.target.id in self.tainted or self._is_stringish(node.value))
        ):
            self.tainted.add(node.target.id)
        self.generic_visit(node)


class _SQLInjectionVisitor(ast.NodeVisitor):
    def __init__(self, code: str, filename: str):
        self.code = code
        self.filename = filename
        self.findings: list[Finding] = []
        self.taint = _TaintTracker()

    def _interpolated_names(self, node) -> list[str]:
        return [n.id for n in ast.walk(node) if isinstance(n, ast.Name)]

    def _is_dynamic(self, arg) -> bool:
        if isinstance(arg, ast.Constant):
            return False
        if isinstance(arg, ast.JoinedStr):
            return True
        if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Mod)):
            return True
        if (
            isinstance(arg, ast.Call)
            and isinstance(arg.func, ast.Attribute)
            and arg.func.attr == "format"
        ):
            return True
        if isinstance(arg, ast.Name) and arg.id in self.taint.tainted:
            return True
        return False

    def _iter_members(self, node) -> list[ast.AST]:
        if isinstance(node, ast.List):
            return list(node.elts)
        if isinstance(node, ast.Dict):
            return [k for k in node.keys if k is not None]
        return []

    def _check_argument(self, call_node: ast.Call, arg: ast.AST) -> None:
        if self._is_dynamic(arg):
            names = [n for n in self._interpolated_names(arg) if n != "self"]
            var = names[0] if names else "user_input"
            param_tpl = "(" + ", ".join(f"{n}," for n in names[:2]) + ")"
            if not names:
                param_tpl = "(user_input,)"
            self.findings.append(
                make_finding(
                    finding_type="SQL Injection",
                    severity="Critical",
                    filename=self.filename,
                    line=call_node.lineno,
                    code=self.code,
                    explanation=(
                        "SQL is built by concatenating or interpolating a value into the "
                        "query string. If that value comes from user input, an attacker can "
                        "inject SQL (e.g. ' OR '1'='1) and read or modify arbitrary data. "
                        "Use a parameterized query so values are sent as data, never as code."
                    ),
                    suggested_fix=(
                        'cursor.execute("SELECT ... WHERE col = %s", ' + param_tpl + ")\n"
                        "# Pass values as separate parameters instead of interpolation."
                    ),
                    source="ast.sql_injection",
                )
            )

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            attr = func.attr
        elif isinstance(func, ast.Name):
            attr = func.id
        else:
            attr = ""

        if attr in EXECUTE_METHODS or attr in SQL_TEXT_WRAPPERS:
            if node.args:
                first = node.args[0]
                if isinstance(first, (ast.List, ast.Dict)):
                    for member in self._iter_members(first):
                        self._check_argument(node, member)
                else:
                    self._check_argument(node, first)
            for kw in node.keywords:
                if kw.arg in ("params", "parameters", "args"):
                    continue
                if isinstance(kw.value, (ast.List, ast.Dict)):
                    for member in self._iter_members(kw.value):
                        self._check_argument(node, member)
                else:
                    self._check_argument(node, kw.value)
        self.generic_visit(node)


def detect_sql_injection(code: str, filename: str = "main.py") -> list[Finding]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    visitor = _SQLInjectionVisitor(code, filename)
    visitor.taint.visit(tree)
    visitor.visit(tree)
    return visitor.findings