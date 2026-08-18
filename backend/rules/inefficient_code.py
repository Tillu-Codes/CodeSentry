import ast

from models import Finding
from rules.base import make_finding

N_PLUS_ONE_METHODS = {"execute", "executemany", "fetchone", "fetchall", "raw"}
MATERIALIZED_CALLS = {"range", "map", "filter", "zip"}


class _StringNames(ast.NodeVisitor):
    def __init__(self):
        self.names: set[str] = set()

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.names.add(target.id)
        self.generic_visit(node)


class _InefficientVisitor(ast.NodeVisitor):
    def __init__(self, code: str, filename: str):
        self.code = code
        self.filename = filename
        self.findings: list[Finding] = []
        self.string_names: set[str] = set()

    def _concat_finding(self, node: ast.AST) -> None:
        self.findings.append(
            make_finding(
                finding_type="Inefficient Code",
                severity="Low",
                filename=self.filename,
                line=node.lineno,
                code=self.code,
                explanation=(
                    "Repeated string concatenation in a loop is O(n^2) because each += "
                    "rebuilds the whole string. Accumulate parts in a list and join once "
                    "at the end."
                ),
                suggested_fix=(
                    "parts = []\n"
                    "for item in items:\n"
                    "    parts.append(str(item))\n"
                    "result = ''.join(parts)"
                ),
                source="ast.inefficient_code",
            )
        )

    def _n_plus_one_finding(self, node: ast.Call) -> None:
        self.findings.append(
            make_finding(
                finding_type="N+1 Query Pattern",
                severity="Medium",
                filename=self.filename,
                line=node.lineno,
                code=self.code,
                explanation=(
                    "A database/API call happens inside a loop (N+1 pattern): one query "
                    "per iteration. For N rows this issues N+1 round trips. Batch the "
                    "work with a single query (IN (...) / JOIN) or fetch all rows up front."
                ),
                suggested_fix=(
                    "# Fetch everything in one query, then loop over the results in memory."
                ),
                source="ast.inefficient_code",
            )
        )

    def _list_materialization_finding(self, node: ast.AST) -> None:
        self.findings.append(
            make_finding(
                finding_type="Inefficient Code",
                severity="Low",
                filename=self.filename,
                line=node.lineno,
                code=self.code,
                explanation=(
                    "list() eagerly materializes the whole sequence even though you only "
                    "iterate it once. Iterate the generator/iterator directly to save memory."
                ),
                suggested_fix="for item in <iterator>:\n    ...",
                source="ast.inefficient_code",
            )
        )

    def _scan_loop_body(self, stmts: list[ast.stmt]) -> None:
        for child in ast.walk(ast.Module(body=stmts, type_ignores=[])):
            if isinstance(child, (ast.For, ast.While, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(child, ast.AugAssign):
                if (
                    isinstance(child.op, ast.Add)
                    and isinstance(child.target, ast.Name)
                    and child.target.id in self.string_names
                ):
                    self._concat_finding(child)
            elif isinstance(child, ast.Assign):
                value = child.value
                if (
                    isinstance(value, ast.BinOp)
                    and isinstance(value.op, ast.Add)
                    and isinstance(value.left, ast.Name)
                    and value.left.id in self.string_names
                ):
                    self._concat_finding(child)
            elif isinstance(child, ast.Call):
                if (
                    isinstance(child.func, ast.Attribute)
                    and child.func.attr in N_PLUS_ONE_METHODS
                ):
                    self._n_plus_one_finding(child)

    def _check_iter(self, iter_node: ast.AST) -> None:
        if (
            isinstance(iter_node, ast.Call)
            and isinstance(iter_node.func, ast.Name)
            and iter_node.func.id == "list"
            and iter_node.args
            and isinstance(iter_node.args[0], (ast.Call, ast.GeneratorExp))
        ):
            inner = iter_node.args[0]
            if isinstance(inner, ast.GeneratorExp) or (
                isinstance(inner.func, ast.Name) and inner.func.id in MATERIALIZED_CALLS
            ):
                self._list_materialization_finding(iter_node)

    def visit_For(self, node: ast.For) -> None:
        self._scan_loop_body(node.body)
        self._check_iter(node.iter)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._scan_loop_body(node.body)
        self.generic_visit(node)


def detect_inefficient_code(code: str, filename: str = "main.py") -> list[Finding]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    names = _StringNames()
    names.visit(tree)
    visitor = _InefficientVisitor(code, filename)
    visitor.string_names = names.names
    visitor.visit(tree)
    return visitor.findings