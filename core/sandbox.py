"""AST-based static validator for proposed code patches."""
import ast
from typing import Any, Dict

DANGEROUS_MODULES = {"os", "subprocess", "shutil", "sys", "socket", "urllib", "requests"}
PROHIBITED_BUILTINS = {"eval", "exec", "open", "input"}
PROHIBITED_ATTRIBUTES = {"system", "popen", "spawn", "rmdir", "remove", "chmod"}


class SafeCodeVisitor(ast.NodeVisitor):
    """Walks an AST and flags imports or calls that should not appear in a fix."""

    def __init__(self) -> None:
        self.is_safe = True
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in DANGEROUS_MODULES:
                self.is_safe = False
                self.violations.append(f"Dangerous Import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module in DANGEROUS_MODULES:
            self.is_safe = False
            self.violations.append(f"Dangerous FromImport: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in PROHIBITED_BUILTINS:
            self.is_safe = False
            self.violations.append(f"Prohibited Built-in Call: {node.func.id}")
        elif isinstance(node.func, ast.Attribute) and node.func.attr in PROHIBITED_ATTRIBUTES:
            self.is_safe = False
            self.violations.append(f"Prohibited Attribute Call: {node.func.attr}")
        self.generic_visit(node)


def safe_sandbox_compile(code_str: str) -> Dict[str, Any]:
    """Parses + compiles `code_str` and rejects banned imports/calls."""
    try:
        tree = ast.parse(code_str)
        visitor = SafeCodeVisitor()
        visitor.visit(tree)
        if not visitor.is_safe:
            return {"status": "unsafe", "violations": visitor.violations}
        compile(code_str, filename="sandbox_eval", mode="exec")
        return {"status": "safe", "detail": "Code syntax compiles successfully in sandbox."}
    except SyntaxError as se:
        return {
            "status": "syntax_error",
            "detail": f"Syntax verification failed: {se.msg} on line {se.lineno}",
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
