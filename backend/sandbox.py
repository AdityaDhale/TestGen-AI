import subprocess
import tempfile
import os
import sys
import json
import re
import shutil
from typing import Optional


import os as _os
# Use venv python if available (co-located .venv), else fall back to sys.executable
_venv_python = _os.path.join(_os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
PYTHON_EXEC = _venv_python if _os.path.exists(_venv_python) else sys.executable


def run_python_tests(
    source_code: str,
    test_code: str,
    timeout: int = 30,
) -> dict:
    """
    Executes generated pytest tests against source code in a temporary directory.
    Returns structured pass/fail/coverage results.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write source module
        source_path = os.path.join(tmpdir, "source_module.py")
        test_path = os.path.join(tmpdir, "test_generated.py")
        report_path = os.path.join(tmpdir, "report.json")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        # Inject the correct import into the test code
        patched_test = _patch_imports(test_code)
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(patched_test)

        try:
            cmd = [
                PYTHON_EXEC, "-m", "pytest",
                "test_generated.py",
                "--json-report",
                f"--json-report-file={report_path}",
                "--tb=short",
                "-v",
                "--no-header",
                "-q",
            ]

            proc = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            stdout = proc.stdout
            stderr = proc.stderr

            # Try to load structured JSON report
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                return _parse_json_report(report, stdout, stderr)
            else:
                # Fallback: parse stdout
                return _parse_stdout_fallback(stdout, stderr, proc.returncode)

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "total": 0,
                "tests": [],
                "stdout": "Execution timed out after {} seconds.".format(timeout),
                "stderr": "",
                "coverage_pct": 0,
            }
        except Exception as e:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "total": 0,
                "tests": [],
                "stdout": "",
                "stderr": str(e),
                "coverage_pct": 0,
            }


def _patch_imports(test_code: str) -> str:
    """
    Replace common import patterns to point to source_module.
    e.g. 'from mymodule import ...' -> 'from source_module import ...'
         'import mymodule' -> 'import source_module as mymodule'
    """
    lines = test_code.splitlines()
    patched = []
    for line in lines:
        stripped = line.strip()
        # If line imports something that's NOT a standard lib or pytest, remap to source_module
        if stripped.startswith("from ") and " import " in stripped:
            parts = stripped.split(" import ")
            module = parts[0].replace("from ", "").strip()
            # Leave pytest, stdlib alone
            if module not in ("pytest", "unittest", "os", "sys", "re", "json",
                              "math", "typing", "collections", "itertools",
                              "functools", "pathlib", "datetime", "time",
                              "string", "random", "copy", "io", "abc"):
                line = line.replace(f"from {module} ", "from source_module ")
        elif stripped.startswith("import ") and "pytest" not in stripped:
            mod = stripped.replace("import ", "").split(" as ")[0].strip()
            if "." not in mod and mod not in ("os", "sys", "re", "json", "math",
                                               "typing", "collections", "unittest",
                                               "itertools", "functools", "pathlib",
                                               "datetime", "time", "string",
                                               "random", "copy", "io", "abc"):
                line = f"import source_module as {mod}"
        patched.append(line)
    return "\n".join(patched)


def _parse_json_report(report: dict, stdout: str, stderr: str) -> dict:
    """Parse pytest-json-report output into a clean result dict."""
    summary = report.get("summary", {})
    tests = []

    for test in report.get("tests", []):
        outcome = test.get("outcome", "unknown")
        name = test.get("nodeid", "").split("::")[-1]
        duration = test.get("duration", 0)

        call_info = test.get("call", {})
        longrepr = ""
        if outcome == "failed":
            longrepr = call_info.get("longrepr", "")

        tests.append({
            "name": name,
            "status": outcome,
            "duration_ms": round(duration * 1000, 1),
            "error": longrepr[:500] if longrepr else None,
        })

    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("error", 0)
    total = summary.get("total", 0)

    coverage_pct = round((passed / total * 100) if total > 0 else 0, 1)

    return {
        "status": "passed" if failed == 0 and errors == 0 else "failed",
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": total,
        "tests": tests,
        "stdout": stdout,
        "stderr": stderr,
        "coverage_pct": coverage_pct,
    }


def _parse_stdout_fallback(stdout: str, stderr: str, returncode: int) -> dict:
    """Fallback parser when JSON report is unavailable."""
    passed = len(re.findall(r"PASSED", stdout))
    failed = len(re.findall(r"FAILED", stdout))
    errors = len(re.findall(r"ERROR", stdout))
    total = passed + failed + errors

    # Extract individual test results
    tests = []
    for line in stdout.splitlines():
        if " PASSED" in line:
            name = line.split("::")[1].split(" ")[0] if "::" in line else line.strip()
            tests.append({"name": name, "status": "passed", "duration_ms": 0, "error": None})
        elif " FAILED" in line:
            name = line.split("::")[1].split(" ")[0] if "::" in line else line.strip()
            tests.append({"name": name, "status": "failed", "duration_ms": 0, "error": None})

    coverage_pct = round((passed / total * 100) if total > 0 else 0, 1)

    return {
        "status": "passed" if returncode == 0 else "failed",
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": total,
        "tests": tests,
        "stdout": stdout,
        "stderr": stderr,
        "coverage_pct": coverage_pct,
    }
