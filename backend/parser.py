import ast
import json
from typing import Optional


def parse_python_code(source_code: str) -> dict:
    """
    Parses Python source code using AST and extracts structured metadata
    for functions, classes, and module-level info.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}", "functions": [], "classes": [], "imports": []}

    result = {
        "language": "python",
        "functions": [],
        "classes": [],
        "imports": [],
        "has_type_hints": False,
        "total_lines": len(source_code.splitlines()),
    }

    for node in ast.walk(tree):
        # Extract imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                result["imports"].append(f"{module}.{alias.name}")

        # Extract top-level functions
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            func_info = _extract_function_info(node)
            result["functions"].append(func_info)
            if func_info.get("return_type") or func_info.get("args_with_types"):
                result["has_type_hints"] = True

        # Extract classes
        elif isinstance(node, ast.ClassDef):
            class_info = _extract_class_info(node)
            result["classes"].append(class_info)

    return result


def _extract_function_info(node) -> dict:
    """Extract detailed info from a function AST node."""
    args = []
    args_with_types = []

    for arg in node.args.args:
        arg_name = arg.arg
        arg_type = None
        if arg.annotation:
            arg_type = _annotation_to_str(arg.annotation)
            args_with_types.append(f"{arg_name}: {arg_type}")
        args.append({"name": arg_name, "type": arg_type})

    return_type = None
    if node.returns:
        return_type = _annotation_to_str(node.returns)

    docstring = ast.get_docstring(node) or ""

    # Get default values
    defaults = []
    for default in node.args.defaults:
        try:
            defaults.append(ast.literal_eval(default))
        except Exception:
            defaults.append("...")

    return {
        "name": node.name,
        "args": args,
        "args_with_types": args_with_types,
        "return_type": return_type,
        "docstring": docstring,
        "defaults": defaults,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "decorators": [_annotation_to_str(d) for d in node.decorator_list],
        "line_start": node.lineno,
        "line_end": node.end_lineno,
    }


def _extract_class_info(node) -> dict:
    """Extract detailed info from a class AST node."""
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_extract_function_info(item))

    bases = []
    for base in node.bases:
        bases.append(_annotation_to_str(base))

    return {
        "name": node.name,
        "bases": bases,
        "methods": methods,
        "docstring": ast.get_docstring(node) or "",
        "line_start": node.lineno,
        "line_end": node.end_lineno,
    }


def _annotation_to_str(annotation) -> str:
    """Convert an AST annotation node to a readable string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Attribute):
        return f"{_annotation_to_str(annotation.value)}.{annotation.attr}"
    elif isinstance(annotation, ast.Subscript):
        return f"{_annotation_to_str(annotation.value)}[{_annotation_to_str(annotation.slice)}]"
    elif isinstance(annotation, ast.Constant):
        return str(annotation.value)
    elif isinstance(annotation, ast.Tuple):
        return ", ".join(_annotation_to_str(e) for e in annotation.elts)
    elif isinstance(annotation, ast.BinOp):
        return f"{_annotation_to_str(annotation.left)} | {_annotation_to_str(annotation.right)}"
    else:
        return "Any"


def build_context_summary(parsed: dict, source_code: str) -> str:
    """
    Build a compact, LLM-friendly summary of the parsed code
    to use as context for test generation.
    """
    lines = [f"## Code Summary ({parsed['total_lines']} lines, Python)\n"]

    if parsed.get("imports"):
        lines.append(f"**Imports:** {', '.join(parsed['imports'][:10])}")

    if parsed.get("functions"):
        lines.append(f"\n### Functions ({len(parsed['functions'])} total):")
        for fn in parsed["functions"]:
            sig_parts = [fn["name"]]
            args_str = ", ".join(
                f"{a['name']}: {a['type']}" if a["type"] else a["name"]
                for a in fn["args"]
            )
            ret = f" -> {fn['return_type']}" if fn["return_type"] else ""
            lines.append(f"- `def {fn['name']}({args_str}){ret}`")
            if fn["docstring"]:
                lines.append(f"  Docstring: {fn['docstring'][:150]}")
            if fn["decorators"]:
                lines.append(f"  Decorators: {', '.join(fn['decorators'])}")

    if parsed.get("classes"):
        lines.append(f"\n### Classes ({len(parsed['classes'])} total):")
        for cls in parsed["classes"]:
            method_names = [m["name"] for m in cls["methods"]]
            lines.append(f"- `class {cls['name']}({', '.join(cls['bases'])})` — methods: {', '.join(method_names)}")
            if cls["docstring"]:
                lines.append(f"  Docstring: {cls['docstring'][:150]}")

    lines.append(f"\n### Full Source Code:\n```python\n{source_code}\n```")

    return "\n".join(lines)
