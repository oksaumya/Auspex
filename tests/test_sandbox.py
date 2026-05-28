"""AST sandbox blocks dangerous imports and calls."""
from core.sandbox import safe_sandbox_compile


def test_safe_code_passes():
    assert safe_sandbox_compile("x = 1 + 2\nprint(x)")["status"] == "safe"


def test_dangerous_import_os_rejected():
    result = safe_sandbox_compile("import os")
    assert result["status"] == "unsafe"
    assert any("os" in v for v in result["violations"])


def test_dangerous_subprocess_rejected():
    result = safe_sandbox_compile("import subprocess\nsubprocess.run(['ls'])")
    assert result["status"] == "unsafe"


def test_eval_call_rejected():
    result = safe_sandbox_compile("eval('1+1')")
    assert result["status"] == "unsafe"
    assert any("eval" in v for v in result["violations"])


def test_exec_call_rejected():
    assert safe_sandbox_compile("exec('print(1)')")["status"] == "unsafe"


def test_os_system_attribute_rejected():
    result = safe_sandbox_compile("some.system('rm -rf /')")
    assert result["status"] == "unsafe"
    assert any("system" in v for v in result["violations"])


def test_syntax_error_reported():
    result = safe_sandbox_compile("def f(:")
    assert result["status"] == "syntax_error"
    assert "lineno" not in result["detail"].lower() or "line" in result["detail"].lower()


def test_from_subprocess_rejected():
    assert safe_sandbox_compile("from subprocess import run")["status"] == "unsafe"
