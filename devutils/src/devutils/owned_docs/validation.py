"""Owned D420/D421 supplement to official pydocstyle's Google checks.

Rule provenance and MIT notices are recorded in UPSTREAM.md.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

_ORDER = ("Example", "Args", "Returns", "Yields", "Raises", "Note")


def section_errors(source: str) -> list[tuple[str, int]]:
    """Return custom section-order and inline-description violations."""
    from pydocstyle.checker import ConventionChecker

    errors = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        doc = ast.get_docstring(node, clean=False)
        if not doc:
            continue
        lines = doc.splitlines()
        # Reuse the official parser's section boundaries rather than matching prose.
        contexts = list(
            ConventionChecker()._get_section_contexts(
                lines, ConventionChecker.GOOGLE_SECTION_NAMES
            )
        )
        found = [context.section_name for context in contexts]
        line = getattr(node, "lineno", 1)
        if found and found != [name for name in _ORDER if name in found]:
            errors.append(("D420", line))
        for context in contexts:
            if context.section_name not in ("Args", "Raises"):
                continue
            for text in context.following_lines:
                match = re.match(
                    r"(^ {8})(\**[\w\[\]_]+?)\s*?:(.{2,})?", text, re.IGNORECASE
                )
                if match and match.group().endswith(":"):
                    errors.append(("D421", line))
    return errors


def validate_path(target: str) -> list[str]:
    """Validate a file, directory or import path without invoking a shell."""
    import pydocstyle

    path = Path(target)
    if not path.exists():
        spec = importlib.util.find_spec(target)
        if spec is None:
            raise ValueError(f"Cannot resolve documentation target {target!r}")
        # Preserve the original import-target contract: validate __file__, not
        # every descendant. Namespace packages without a file use their roots.
        roots = (
            [Path(spec.origin)]
            if spec.origin and spec.origin not in {"built-in", "frozen"}
            else [Path(p) for p in (spec.submodule_search_locations or [])]
        )
    else:
        roots = [path]
    files = sorted(
        {
            p
            for root in roots
            for p in (root.rglob("*.py") if root.is_dir() else [root])
            if re.match(r"^(?!_(?!_))(?!test_).*\.py$", p.name)
            and not any(
                part.startswith("_") and not part.startswith("__")
                for part in p.parts[:-1]
            )
        }
    )
    ignored = {"D100", "D101", "D102", "D103", "D104", "D105", "D107", "D202"}
    selected = (
        set(pydocstyle.violations.conventions.google) - ignored - {"D420", "D421"}
    )
    errors = [
        str(error)
        for error in pydocstyle.check([str(p) for p in files], select=selected)
    ]
    for file in files:
        errors.extend(
            f"{file}:{line}: {code}"
            for code, line in section_errors(file.read_text(encoding="utf-8"))
        )
    return errors
