"""
TestGen AI — Multi-step NVIDIA Nemotron Agent Pipeline
Powered by Nebius AI Cloud (OpenAI-compatible API)

Pipeline:
  Step 1: Code Analysis       (Nemotron — fast, compact context)
  Step 2: Test Strategy       (Nemotron — plan edge cases & scenarios)
  Step 3: Test Generation     (Nemotron — write full pytest file)
  Step 4: Sandbox Execution   (local subprocess)
  Step 5: Iterative Fix       (Nemotron — fix failing tests, up to N iterations)
"""

import os
import asyncio
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

from parser import parse_python_code, build_context_summary
from sandbox import run_python_tests

load_dotenv()

NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1/")
MODEL_FAST = os.getenv("MODEL_FAST", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF")
MODEL_SMART = os.getenv("MODEL_SMART", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF")
MAX_FIX_ITERATIONS = int(os.getenv("MAX_FIX_ITERATIONS", "3"))
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=NEBIUS_API_KEY,
        base_url=NEBIUS_BASE_URL,
    )


class TestGenAgent:
    """
    Orchestrates the full test generation pipeline using NVIDIA Nemotron
    models hosted on Nebius AI Cloud.
    """

    def __init__(self):
        self.client = get_client()
        self.steps_log = []

    def _log(self, step: str, detail: str = "") -> dict:
        entry = {"step": step, "detail": detail}
        self.steps_log.append(entry)
        return entry

    async def run(self, source_code: str, language: str = "python") -> dict:
        """
        Run the full pipeline and return the complete result.
        """
        self.steps_log = []
        result = {
            "steps": self.steps_log,
            "analysis": None,
            "strategy": None,
            "test_code": None,
            "execution": None,
            "iterations": 0,
            "final_status": "pending",
            "error": None,
        }

        try:
            # ── Step 1: Code Analysis ──────────────────────────────────────
            self._log("analyzing", "Parsing code structure with AST...")
            parsed = parse_python_code(source_code)
            context = build_context_summary(parsed, source_code)
            result["analysis"] = parsed

            if parsed.get("error"):
                result["final_status"] = "error"
                result["error"] = f"Code parse error: {parsed['error']}"
                return result

            # ── Step 2: Test Strategy Planning ────────────────────────────
            self._log("planning", "Planning test strategy with Nemotron...")
            strategy = await self._plan_test_strategy(context, language)
            result["strategy"] = strategy

            # ── Step 3: Test Code Generation ──────────────────────────────
            self._log("generating", "Generating test code with NVIDIA Nemotron...")
            test_code = await self._generate_tests(context, strategy, language)
            result["test_code"] = test_code

            # ── Step 4: Sandbox Execution ─────────────────────────────────
            self._log("executing", "Running tests in secure sandbox...")
            execution = run_python_tests(source_code, test_code, timeout=SANDBOX_TIMEOUT)
            result["execution"] = execution

            # ── Step 5: Iterative Fix Loop ─────────────────────────────────
            iteration = 0
            while (
                execution.get("failed", 0) > 0 or execution.get("errors", 0) > 0
            ) and iteration < MAX_FIX_ITERATIONS:
                iteration += 1
                result["iterations"] = iteration
                fail_count = execution.get("failed", 0) + execution.get("errors", 0)
                self._log(
                    "fixing",
                    f"Iteration {iteration}: Fixing {fail_count} failing test(s)..."
                )
                test_code = await self._fix_tests(
                    context, test_code, execution, language
                )
                result["test_code"] = test_code
                self._log("re-executing", f"Re-running tests after fix #{iteration}...")
                execution = run_python_tests(source_code, test_code, timeout=SANDBOX_TIMEOUT)
                result["execution"] = execution

            result["iterations"] = iteration
            result["final_status"] = execution.get("status", "unknown")
            self._log(
                "complete",
                f"Done! {execution.get('passed', 0)} passed, "
                f"{execution.get('failed', 0)} failed out of {execution.get('total', 0)} tests."
            )

        except Exception as e:
            result["final_status"] = "error"
            result["error"] = str(e)
            self._log("error", str(e))

        return result

    async def run_streaming(
        self, source_code: str, language: str = "python"
    ) -> AsyncGenerator[dict, None]:
        """
        Streaming version: yields step updates as they happen (for SSE).
        """
        self.steps_log = []

        async def emit(event: str, data: dict):
            yield {"event": event, "data": data}

        try:
            # Step 1: Analyze
            yield {"event": "step", "data": {"step": "analyzing", "detail": "Parsing code structure with AST..."}}
            await asyncio.sleep(0.1)
            parsed = parse_python_code(source_code)
            context = build_context_summary(parsed, source_code)

            if parsed.get("error"):
                yield {"event": "error", "data": {"message": parsed["error"]}}
                return

            yield {"event": "analysis", "data": parsed}

            # Step 2: Strategy
            yield {"event": "step", "data": {"step": "planning", "detail": "Planning test strategy with NVIDIA Nemotron..."}}
            strategy = await self._plan_test_strategy(context, language)
            yield {"event": "strategy", "data": {"strategy": strategy}}

            # Step 3: Generate
            yield {"event": "step", "data": {"step": "generating", "detail": "Generating comprehensive tests with Nemotron..."}}
            test_code = await self._generate_tests(context, strategy, language)
            yield {"event": "tests", "data": {"test_code": test_code}}

            # Step 4: Execute
            yield {"event": "step", "data": {"step": "executing", "detail": "Running tests in secure sandbox..."}}
            execution = run_python_tests(source_code, test_code, timeout=SANDBOX_TIMEOUT)
            yield {"event": "execution", "data": execution}

            # Step 5: Fix loop
            iteration = 0
            while (
                execution.get("failed", 0) > 0 or execution.get("errors", 0) > 0
            ) and iteration < MAX_FIX_ITERATIONS:
                iteration += 1
                fail_count = execution.get("failed", 0) + execution.get("errors", 0)
                yield {
                    "event": "step",
                    "data": {
                        "step": "fixing",
                        "detail": f"Iteration {iteration}: Fixing {fail_count} failing test(s) with Nemotron..."
                    }
                }
                test_code = await self._fix_tests(context, test_code, execution, language)
                yield {"event": "tests", "data": {"test_code": test_code}}

                yield {"event": "step", "data": {"step": "re-executing", "detail": f"Re-running tests after fix #{iteration}..."}}
                execution = run_python_tests(source_code, test_code, timeout=SANDBOX_TIMEOUT)
                yield {"event": "execution", "data": execution}

            yield {
                "event": "complete",
                "data": {
                    "iterations": iteration,
                    "final_status": execution.get("status", "unknown"),
                    "summary": f"{execution.get('passed', 0)} passed / {execution.get('total', 0)} total",
                }
            }

        except Exception as e:
            yield {"event": "error", "data": {"message": str(e)}}

    async def _plan_test_strategy(self, context: str, language: str) -> str:
        """Use Nemotron to plan a comprehensive testing strategy."""
        system_prompt = """You are an expert software testing strategist powered by NVIDIA Nemotron on Nebius AI Cloud.
Your job is to analyze code and create a thorough test strategy.
Be concise but comprehensive. Output a numbered list of test scenarios."""

        user_prompt = f"""Analyze this {language} code and create a test strategy.
List specific test scenarios including:
- Happy path cases
- Edge cases (empty input, None, zero, negative numbers, etc.)
- Error/exception cases
- Boundary conditions
- Type variations (if applicable)

{context}

Output format:
1. [Test scenario name]: [what to test and expected outcome]
2. ...
Keep it to 8-12 scenarios maximum."""

        response = await self.client.chat.completions.create(
            model=MODEL_FAST,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return response.choices[0].message.content

    async def _generate_tests(
        self, context: str, strategy: str, language: str
    ) -> str:
        """Use Nemotron to generate a complete pytest test file."""
        system_prompt = """You are an expert Python test engineer powered by NVIDIA Nemotron on Nebius AI Cloud.
Generate complete, runnable pytest test files. Follow these rules:
- Always import from 'source_module' (e.g. 'from source_module import MyClass, my_function')
- Use descriptive test function names: test_<scenario>_<condition>
- Add docstrings to each test explaining what it tests
- Use pytest.mark.parametrize for data-driven tests when appropriate
- Use pytest.raises() for exception testing
- Include assertions with helpful failure messages
- Output ONLY the Python test code, no explanations, no markdown fences"""

        user_prompt = f"""Generate a complete pytest test file for the following code.

TEST STRATEGY TO IMPLEMENT:
{strategy}

CODE TO TEST:
{context}

Remember:
- Import from 'source_module'
- Implement ALL scenarios from the strategy
- Make tests actually runnable and correct
- Output only raw Python code"""

        response = await self.client.chat.completions.create(
            model=MODEL_SMART,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()
        # Strip any markdown fences if model adds them
        return _strip_code_fences(raw)

    async def _fix_tests(
        self,
        context: str,
        test_code: str,
        execution: dict,
        language: str,
    ) -> str:
        """Use Nemotron to fix failing tests based on execution output."""
        failing_details = []
        for t in execution.get("tests", []):
            if t["status"] in ("failed", "error"):
                failing_details.append(
                    f"- Test: {t['name']}\n  Error: {t.get('error', 'Unknown error')}"
                )

        failing_str = "\n".join(failing_details) if failing_details else execution.get("stdout", "")[:1000]

        system_prompt = """You are an expert Python debugging engineer powered by NVIDIA Nemotron on Nebius AI Cloud.
Fix failing pytest tests. Output ONLY the corrected complete Python test file, no explanations."""

        user_prompt = f"""The following tests are failing. Fix them.

ORIGINAL SOURCE CODE CONTEXT:
{context}

CURRENT TEST FILE:
```python
{test_code}
```

FAILING TESTS:
{failing_str}

EXECUTION OUTPUT:
{execution.get('stdout', '')[:500]}

Fix the failing tests while keeping the passing ones intact.
Output only the complete corrected Python test file."""

        response = await self.client.chat.completions.create(
            model=MODEL_SMART,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()
        return _strip_code_fences(raw)


def _strip_code_fences(text: str) -> str:
    """Remove ```python ... ``` or ``` ... ``` wrappers if present."""
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
