#!/usr/bin/env python3
"""Extract interface metadata from Python modules for context-efficient agent navigation.

Designed for the tiered context model: agents read compressed interface descriptions
instead of full source code, achieving 85-90% token savings.

Usage:
    python tools/inspect_interface.py <path> [options]

Arguments:
    path                File or directory to inspect

Options:
    --depth=N           0=names, 1=signatures (default), 2=signatures+docstrings
    --format=FMT        text (default) | json
    --only-base         Only inspect base.py files (skip implementations)
    --module-doc        Extract only module-level docstrings
    --verify=PATH       Verify CLAUDE.md module map matches code reality

Depth levels and approximate token costs (per module):
    0: Class/function names only            ~20 tokens  (Tier 0.5)
    1: Names + signatures + type annotations ~100 tokens (Tier 1 compressed)
    2: Names + signatures + docstrings       ~300 tokens (Tier 1 full)
"""

import ast
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional


def get_annotation_str(node: Optional[ast.expr]) -> str:
    """Convert an AST annotation node to its string representation."""
    if node is None:
        return ""
    return ast.unparse(node)


def get_first_line_docstring(node: ast.AST) -> str:
    """Extract first line of docstring from an AST node."""
    docstring = ast.get_docstring(node)
    if not docstring:
        return ""
    return docstring.strip().split("\n")[0]


def get_full_docstring(node: ast.AST) -> str:
    """Extract full docstring from an AST node."""
    return ast.get_docstring(node) or ""


def format_signature(func: ast.FunctionDef) -> str:
    """Format a function/method signature from AST node."""
    args = []
    all_args = func.args

    # Regular args
    num_defaults = len(all_args.defaults)
    num_args = len(all_args.args)
    for i, arg in enumerate(all_args.args):
        if arg.arg == "self" or arg.arg == "cls":
            continue
        ann = get_annotation_str(arg.annotation)
        default_idx = i - (num_args - num_defaults)
        if default_idx >= 0:
            default = ast.unparse(all_args.defaults[default_idx])
            args.append(f"{arg.arg}: {ann} = {default}" if ann else f"{arg.arg}={default}")
        else:
            args.append(f"{arg.arg}: {ann}" if ann else arg.arg)

    # *args
    if all_args.vararg:
        ann = get_annotation_str(all_args.vararg.annotation)
        args.append(f"*{all_args.vararg.arg}: {ann}" if ann else f"*{all_args.vararg.arg}")

    # keyword-only args
    for i, arg in enumerate(all_args.kwonlyargs):
        ann = get_annotation_str(arg.annotation)
        if i < len(all_args.kw_defaults) and all_args.kw_defaults[i] is not None:
            default = ast.unparse(all_args.kw_defaults[i])
            args.append(f"{arg.arg}: {ann} = {default}" if ann else f"{arg.arg}={default}")
        else:
            args.append(f"{arg.arg}: {ann}" if ann else arg.arg)

    # **kwargs
    if all_args.kwarg:
        ann = get_annotation_str(all_args.kwarg.annotation)
        args.append(f"**{all_args.kwarg.arg}: {ann}" if ann else f"**{all_args.kwarg.arg}")

    ret = get_annotation_str(func.returns)
    ret_str = f" -> {ret}" if ret else ""
    return f"{func.name}({', '.join(args)}){ret_str}"


def get_bases(node: ast.ClassDef) -> str:
    """Get base classes as a string."""
    if not node.bases:
        return ""
    bases = [ast.unparse(b) for b in node.bases]
    return f"({', '.join(bases)})"


def get_class_fields(node: ast.ClassDef) -> list[tuple[str, str]]:
    """Extract class-level annotated fields (for dataclasses, NamedTuples, etc.)."""
    fields = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            ann = get_annotation_str(item.annotation)
            if item.value is not None:
                default = ast.unparse(item.value)
                fields.append((item.target.id, f"{ann} = {default}"))
            else:
                fields.append((item.target.id, ann))
    return fields


def is_dataclass_or_similar(node: ast.ClassDef) -> bool:
    """Check if class has @dataclass or similar decorator."""
    for dec in node.decorator_list:
        name = ast.unparse(dec)
        if "dataclass" in name.lower() or "namedtuple" in name.lower():
            return True
    # Also check if it inherits from known data types
    for base in node.bases:
        name = ast.unparse(base)
        if name in ("NamedTuple", "TypedDict", "BaseModel"):
            return True
    return False


def extract_module_info(filepath: str, depth: int = 1, module_doc_only: bool = False) -> dict:
    """Extract interface information from a Python file."""
    with open(filepath, "r") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"file": filepath, "error": f"SyntaxError: {e}"}

    info = {
        "file": filepath,
        "module_docstring": "",
        "classes": [],
        "functions": [],
        "exports": [],
    }

    # Module-level docstring
    info["module_docstring"] = get_full_docstring(tree)

    if module_doc_only:
        return info

    # Find __all__ exports
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        info["exports"] = [
                            ast.unparse(elt) for elt in node.value.elts
                        ]

    # Top-level classes and functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "bases": get_bases(node),
                "is_dataclass": is_dataclass_or_similar(node),
            }

            if depth >= 1:
                class_info["methods"] = []
                class_info["fields"] = get_class_fields(node)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name.startswith("_") and item.name != "__init__":
                            continue
                        method_info = {"signature": format_signature(item)}
                        if depth >= 2:
                            method_info["docstring"] = get_full_docstring(item)
                        class_info["methods"].append(method_info)

            if depth >= 2:
                class_info["docstring"] = get_full_docstring(node)
            elif depth >= 1:
                class_info["first_line_doc"] = get_first_line_docstring(node)

            info["classes"].append(class_info)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            func_info = {"name": node.name}
            if depth >= 1:
                func_info["signature"] = format_signature(node)
            if depth >= 2:
                func_info["docstring"] = get_full_docstring(node)
            elif depth >= 1:
                func_info["first_line_doc"] = get_first_line_docstring(node)
            info["functions"].append(func_info)

    return info


def format_text(info: dict, depth: int, module_doc_only: bool = False) -> str:
    """Format extracted info as compact text."""
    lines = []
    filepath = info["file"]

    if "error" in info:
        lines.append(f"# {filepath} — ERROR: {info['error']}")
        return "\n".join(lines)

    if module_doc_only:
        if info["module_docstring"]:
            lines.append(info["module_docstring"])
        else:
            lines.append(f"# {filepath} — no module docstring")
        return "\n".join(lines)

    # Header
    first_line = get_first_line_from_docstring(info["module_docstring"])
    if first_line:
        lines.append(f"# {filepath} — {first_line}")
    else:
        lines.append(f"# {filepath}")

    if info["exports"]:
        lines.append(f"exports: {', '.join(info['exports'])}")

    # Classes
    for cls in info["classes"]:
        if depth == 0:
            prefix = "dataclass " if cls.get("is_dataclass") else "class "
            lines.append(f"{prefix}{cls['name']}{cls.get('bases', '')}")
        else:
            prefix = "dataclass " if cls.get("is_dataclass") else "class "
            header = f"{prefix}{cls['name']}{cls.get('bases', '')}:"
            if depth >= 2 and cls.get("docstring"):
                lines.append(header)
                for doc_line in cls["docstring"].split("\n"):
                    lines.append(f"    \"\"\"{doc_line}\"\"\"" if "\n" not in cls["docstring"] else f"    {doc_line}")
            elif cls.get("first_line_doc"):
                lines.append(f"{header}  # {cls['first_line_doc']}")
            else:
                lines.append(header)

            # Fields (for dataclasses)
            for fname, ftype in cls.get("fields", []):
                lines.append(f"    {fname}: {ftype}")

            # Methods
            for method in cls.get("methods", []):
                lines.append(f"    {method['signature']}")
                if depth >= 2 and method.get("docstring"):
                    for doc_line in method["docstring"].split("\n"):
                        lines.append(f"        {doc_line}")

    # Module-level functions
    for func in info["functions"]:
        if depth == 0:
            lines.append(f"def {func['name']}")
        else:
            sig_line = func.get("signature", func["name"])
            if depth >= 2 and func.get("docstring"):
                lines.append(f"def {sig_line}:")
                for doc_line in func["docstring"].split("\n"):
                    lines.append(f"    {doc_line}")
            elif func.get("first_line_doc"):
                lines.append(f"def {sig_line}  # {func['first_line_doc']}")
            else:
                lines.append(f"def {sig_line}")

    return "\n".join(lines)


def get_first_line_from_docstring(docstring: str) -> str:
    """Get first non-empty line from a docstring."""
    if not docstring:
        return ""
    for line in docstring.strip().split("\n"):
        line = line.strip()
        if line:
            return line
    return ""


def find_python_files(path: str, only_base: bool = False) -> list[str]:
    """Find Python files to inspect."""
    path = Path(path)
    if path.is_file():
        return [str(path)]

    files = []
    for root, dirs, filenames in os.walk(path):
        # Skip hidden dirs, __pycache__, .git, etc.
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            if only_base and fname != "base.py":
                continue
            files.append(os.path.join(root, fname))
    return files


def verify_claude_md(path: str, claude_md_path: str, only_base: bool = True) -> str:
    """Verify CLAUDE.md module map matches code reality."""
    with open(claude_md_path, "r") as f:
        claude_md = f.read()

    files = find_python_files(path, only_base=only_base)
    results = []

    for filepath in files:
        info = extract_module_info(filepath, depth=0)
        if "error" in info:
            results.append(f"ERROR: {filepath} — {info['error']}")
            continue

        for cls in info["classes"]:
            name = cls["name"]
            if name in claude_md:
                results.append(f"OK: {name} (from {filepath}) found in CLAUDE.md")
            else:
                results.append(f"MISSING: {name} (from {filepath}) not in CLAUDE.md")

    # Check for names in CLAUDE.md that reference modules
    module_dirs = set()
    for f in files:
        parts = Path(f).parts
        # Find the module directory (parent of base.py)
        if Path(f).name == "base.py" and len(parts) >= 2:
            module_dirs.add(parts[-2])

    return "\n".join(results) if results else "No Python files found to verify."


def main():
    parser = argparse.ArgumentParser(
        description="Extract interface metadata from Python modules.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("path", help="File or directory to inspect")
    parser.add_argument(
        "--depth", type=int, default=1, choices=[0, 1, 2],
        help="Detail level: 0=names, 1=signatures (default), 2=signatures+docstrings",
    )
    parser.add_argument(
        "--format", dest="output_format", default="text", choices=["text", "json"],
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--only-base", action="store_true",
        help="Only inspect base.py files",
    )
    parser.add_argument(
        "--module-doc", action="store_true",
        help="Extract only module-level docstrings",
    )
    parser.add_argument(
        "--verify", metavar="CLAUDE_MD_PATH",
        help="Verify CLAUDE.md module map matches code",
    )

    args = parser.parse_args()

    if args.verify:
        result = verify_claude_md(args.path, args.verify, only_base=args.only_base)
        print(result)
        return

    files = find_python_files(args.path, only_base=args.only_base)
    if not files:
        print(f"No Python files found at {args.path}", file=sys.stderr)
        sys.exit(1)

    all_info = []
    for filepath in files:
        info = extract_module_info(filepath, depth=args.depth, module_doc_only=args.module_doc)
        all_info.append(info)

    if args.output_format == "json":
        print(json.dumps(all_info, indent=2))
    else:
        outputs = []
        for info in all_info:
            text = format_text(info, args.depth, module_doc_only=args.module_doc)
            if text.strip():
                outputs.append(text)
        print("\n\n".join(outputs))


if __name__ == "__main__":
    main()
