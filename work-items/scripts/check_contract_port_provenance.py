#!/usr/bin/env python3
"""Generate or verify immutable, checked-in contract-port provenance."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "contracts" / "ported-tests.json"
PROVENANCE_PATH = ROOT / "contracts" / "contract-port-provenance.json"
SURFACE_PATH = ROOT / "contracts" / "public-surface-fixtures.json"
LEDGER_PATH = ROOT / "contracts" / "compatibility-ledger.json"
FAILURE_PATH = ROOT / "contracts" / "expected-red-failures.json"

REFERENCE_AUXILIARY = {
    "robocorp-1.5.0": {
        "fixtures.py": ROOT / "tests" / "contract_sources" / "robocorp_fixtures_source.py",
        "mocks.py": ROOT / "tests" / "contract_sources" / "robocorp_mocks_source.py",
    },
    "custom-0.1.6": {
        "fixtures.py": ROOT / "tests" / "contract_sources" / "robocorp_fixtures_source.py",
        "mocks.py": ROOT / "tests" / "contract_sources" / "robocorp_mocks_source.py",
    },
}
ADAPTED_AUXILIARY = (
    ROOT / "tests" / "work_items_tests" / "contract_ports" / "conftest.py",
    ROOT / "tests" / "work_items_tests" / "contract_ports" / "mocks.py",
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _test_nodes(path: Path, suite: str) -> dict[str, str]:
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    nodes = {}
    def node_digest(node):
        starts = [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
        return _digest("".join(lines[min(starts) - 1 : node.end_lineno]).encode())

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            key = f"{suite}::{node.name}"
            nodes[key] = node_digest(node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    key = f"{suite}::{node.name}::{child.name}"
                    nodes[key] = node_digest(child)
    return nodes


def _ast_test_nodes(path: Path, suite: str) -> dict[str, ast.AST]:
    tree = ast.parse(path.read_text())
    nodes = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            nodes[f"{suite}::{node.name}"] = node
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    nodes[f"{suite}::{node.name}::{child.name}"] = child
    return nodes


def _fixture_interfaces(path: Path) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    tree = ast.parse(path.read_text())
    found = {}

    def record(prefix: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        decorators = tuple(
            ast.dump(decorator, include_attributes=False)
            for decorator in node.decorator_list
        )
        if not any("fixture" in decorator for decorator in decorators):
            return
        arguments = tuple(argument.arg for argument in [*node.args.posonlyargs, *node.args.args])
        found[f"{prefix}{node.name}"] = (arguments, decorators)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            record("", node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    record(f"{node.name}.", child)
    return found


def _class_decorators(path: Path) -> dict[str, tuple[str, ...]]:
    return {
        node.name: tuple(
            ast.dump(decorator, include_attributes=False)
            for decorator in node.decorator_list
        )
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.ClassDef)
    }


class _CompatibilityNames(ast.NodeTransformer):
    """Normalize the explicit import/name substitutions used by adapted ports."""

    MODULES = {
        "actions": "robocorp",
        "actions.work_items": "robocorp.workitems",
        "actions.work_items._adapters": "robocorp.workitems._adapters",
        "actions.work_items._adapters._docdb": "robocorp.workitems._adapters._docdb",
        "actions.work_items._adapters._redis": "robocorp.workitems._adapters._redis",
        "actions.work_items._adapters._sqlite": "robocorp.workitems._adapters._sqlite",
        "actions.work_items._exceptions": "robocorp.workitems._exceptions",
        "actions.work_items._types": "robocorp.workitems._types",
        "actions.work_items._workitem": "robocorp.workitems._workitem",
        "actions.work_items.scripts": "scripts",
    }
    STRINGS = {
        "actions.work_items._adapters._redis": "robocorp.workitems._adapters._redis",
        "actions.work_items._adapters._docdb": "robocorp.workitems._adapters._docdb",
    }

    def visit_ImportFrom(self, node):  # noqa: N802
        node = self.generic_visit(node)
        node.module = self.MODULES.get(node.module, node.module)
        for alias in node.names:
            if alias.name == "WorkItemsContext":
                alias.name = "Context"
        return node

    def visit_Name(self, node):  # noqa: N802
        if node.id == "WorkItemsContext":
            node.id = "Context"
        return node

    def visit_Constant(self, node):  # noqa: N802
        if isinstance(node.value, str):
            node.value = self.STRINGS.get(node.value, node.value)
        return node

    def visit_With(self, node):  # noqa: N802
        node = self.generic_visit(node)
        if self._is_deprecation_warning_wrapper(node):
            return node.body
        return node

    def visit_FunctionDef(self, node):  # noqa: N802
        node = self.generic_visit(node)
        if node.name == "test_failed_work_item_release" and self._is_sqlite_release_assertion(node):
            node.body[-1:] = ast.parse(
                """\
item = adapter.get_item(reserved_id)
assert item["state"] == State.FAILED.value
assert item["error_message"] == exception["message"]
"""
            ).body
        return node

    @staticmethod
    def _is_sqlite_release_assertion(node: ast.FunctionDef) -> bool:
        if not node.body or not isinstance(node.body[-1], ast.With):
            return False
        context = node.body[-1].items[0].context_expr
        return (
            isinstance(context, ast.Call)
            and isinstance(context.func, ast.Attribute)
            and context.func.attr == "acquire"
            and isinstance(context.func.value, ast.Attribute)
            and context.func.value.attr == "_pool"
            and isinstance(context.func.value.value, ast.Name)
            and context.func.value.value.id == "adapter"
        )

    @staticmethod
    def _is_deprecation_warning_wrapper(node: ast.With) -> bool:
        if len(node.items) != 1 or len(node.body) != 1:
            return False
        context = node.items[0].context_expr
        if not (
            isinstance(context, ast.Call)
            and isinstance(context.func, ast.Attribute)
            and isinstance(context.func.value, ast.Name)
            and context.func.value.id == "pytest"
            and context.func.attr == "warns"
            and len(context.args) == 1
            and isinstance(context.args[0], ast.Name)
            and context.args[0].id == "DeprecationWarning"
            and len(context.keywords) == 1
            and context.keywords[0].arg == "match"
            and isinstance(context.keywords[0].value, ast.Constant)
        ):
            return False
        warning = context.keywords[0].value.value
        statement = node.body[0]
        call = statement.value if isinstance(statement, ast.Assign) else None
        method = call.func.attr if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) else None
        return (method, warning) in {
            ("download_file", "use get_file"),
            ("download_files", "use get_files"),
        }


def _normalized_node(node: ast.AST) -> str:
    normalized = _CompatibilityNames().visit(copy.deepcopy(node))
    ast.fix_missing_locations(normalized)
    return ast.dump(normalized, include_attributes=False)


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", root, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _literal_exports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    exports = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"__version__", "version_info"}:
                    exports.add(target.id)
                if isinstance(target, ast.Name) and target.id == "__all__":
                    value = ast.literal_eval(node.value)
                    exports.update(value)
    return exports


def _definitions(package_root: Path) -> dict[str, ast.AST]:
    found = {}
    for path in sorted(package_root.rglob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                found.setdefault(node.name, node)
    return found


def _argument(argument: ast.arg, default: ast.AST | None = None) -> str:
    rendered = argument.arg
    if argument.annotation is not None:
        rendered += f": {ast.unparse(argument.annotation)}"
    if default is not None:
        rendered += f" = {ast.unparse(default)}"
    return rendered


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    rendered = [
        _argument(arg, default)
        for arg, default in zip(positional, defaults, strict=True)
    ]
    if args.vararg:
        rendered.append("*" + _argument(args.vararg))
    elif args.kwonlyargs:
        rendered.append("*")
    rendered.extend(
        _argument(arg, default)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
    )
    if args.kwarg:
        rendered.append("**" + _argument(args.kwarg))
    result = f"({', '.join(rendered)})"
    if node.returns is not None:
        result += f" -> {ast.unparse(node.returns)}"
    return result


def _verify_public_surface(origin: str, package_root: Path, init_path: Path, ledger: dict) -> None:
    recorded = ledger["public_surfaces"][origin]
    exports = _literal_exports(init_path)
    assert exports == set(recorded["symbols"]), f"{origin} exported symbols differ from ledger"

    definitions = _definitions(package_root)
    for qualified, expected in recorded["signatures"].items():
        if expected == "class":
            assert isinstance(definitions.get(qualified), ast.ClassDef), qualified
            continue
        owner, separator, member = qualified.partition(".")
        if separator:
            class_node = definitions.get(owner)
            assert isinstance(class_node, ast.ClassDef), qualified
            candidates = {node.name: node for node in class_node.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            node = candidates.get(member)
        else:
            node = definitions.get(owner)
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)), qualified
        assert _signature(node) == expected, f"{origin} signature differs: {qualified}"


def _verify_authoritative(robocorp_root: Path, custom_root: Path) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    ledger = json.loads(LEDGER_PATH.read_text())
    roots = {
        "robocorp-1.5.0": robocorp_root.resolve(),
        "custom-0.1.6": custom_root.resolve(),
    }
    labels = {"robocorp-1.5.0": "Robocorp", "custom-0.1.6": "custom adapter"}

    for origin, root in roots.items():
        expected = manifest["sources"][origin]["commit"]
        actual = _git_head(root)
        if actual != expected:
            raise SystemExit(f"{labels[origin]} reference HEAD {actual} != required {expected}")

    selected = {
        origin: {case["source_test"] for case in manifest["cases"] if case["origin"] == origin}
        for origin in roots
    }
    for origin, root in roots.items():
        source = manifest["sources"][origin]
        discovered = set()
        for suite, paths in source["ports"].items():
            authoritative_path = root / source["path"] / suite
            snapshot_path = ROOT / paths["source"]
            adapted_path = ROOT / paths["adapted"]
            source_nodes = _ast_test_nodes(authoritative_path, suite)
            snapshot_nodes = _ast_test_nodes(snapshot_path, suite)
            adapted_nodes = _ast_test_nodes(adapted_path, suite)
            required = selected[origin] & source_nodes.keys()
            assert required == selected[origin] & snapshot_nodes.keys()
            assert required == selected[origin] & adapted_nodes.keys()
            discovered.update(required)
            for name in sorted(required):
                if ast.dump(source_nodes[name], include_attributes=False) != ast.dump(
                    snapshot_nodes[name], include_attributes=False
                ):
                    raise SystemExit(
                        f"stored selected node differs from pinned source: {origin}/{name}"
                    )
                if _normalized_node(source_nodes[name]) != _normalized_node(adapted_nodes[name]):
                    raise SystemExit(
                        f"adapted test semantics differ beyond explicit import/name rewrites: {origin}/{name}"
                    )
            unselected = source_nodes.keys() - required
            if unselected and not all("::TestRobocorpAdapter::" in name for name in unselected):
                raise SystemExit(f"undeclared source selection gap: {origin}/{suite}")

            selected_classes = {
                name.split("::", 2)[1]
                for name in required
                if len(name.split("::", 2)) == 3
            }
            source_decorators = _class_decorators(authoritative_path)
            adapted_decorators = _class_decorators(adapted_path)
            for class_name in selected_classes:
                if source_decorators.get(class_name) != adapted_decorators.get(class_name):
                    raise SystemExit(
                        f"adapted class decorators differ from pinned source: {origin}/{suite}::{class_name}"
                    )

            source_fixtures = _fixture_interfaces(authoritative_path)
            adapted_fixtures = _fixture_interfaces(adapted_path)
            for fixture_name, interface in source_fixtures.items():
                if fixture_name.split(".", 1)[0] not in selected_classes:
                    continue
                if adapted_fixtures.get(fixture_name) != interface:
                    raise SystemExit(
                        f"adapted fixture interface differs from pinned source: {origin}/{fixture_name}"
                    )
        assert discovered == selected[origin]

    robocorp_package = robocorp_root / "workitems" / "src" / "robocorp" / "workitems"
    custom_package = custom_root / "robocorp_adapters_custom"
    _verify_public_surface(
        "robocorp-1.5.0",
        robocorp_package,
        robocorp_package / "__init__.py",
        ledger,
    )
    _verify_public_surface(
        "custom-0.1.6",
        custom_package,
        custom_package / "__init__.py",
        ledger,
    )

    for origin, root in roots.items():
        tests_root = root / manifest["sources"][origin]["path"]
        for name, snapshot in REFERENCE_AUXILIARY[origin].items():
            actual_tree = ast.parse((tests_root / name).read_text())
            snapshot_tree = ast.parse(snapshot.read_text())
            if ast.dump(actual_tree, include_attributes=False) != ast.dump(
                snapshot_tree, include_attributes=False
            ):
                raise SystemExit(f"stored {name} differs from pinned {origin} fixture source")

        source_fixture_names = set(_fixture_interfaces(tests_root / "fixtures.py"))
        adapted_fixture_names = set(_fixture_interfaces(ADAPTED_AUXILIARY[0]))
        if not source_fixture_names <= adapted_fixture_names:
            missing = sorted(source_fixture_names - adapted_fixture_names)
            raise SystemExit(f"adapted ports are missing pinned fixtures: {missing}")

    assert (custom_root / "workitems_tests" / "test_fizzy_orchestration.py").is_file()
    assert (custom_package / "_yorko_control_room.py").is_file()
    assert "TestRobocorpAdapter" in (
        robocorp_root
        / manifest["sources"]["robocorp-1.5.0"]["path"]
        / "test_adapters.py"
    ).read_text()


def _artifact() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text())
    selected = {
        origin: {case["source_test"] for case in manifest["cases"] if case["origin"] == origin}
        for origin in manifest["sources"]
    }
    ports = {}
    files = {MANIFEST_PATH, SURFACE_PATH, LEDGER_PATH, FAILURE_PATH, *ADAPTED_AUXILIARY}
    for origin, source in manifest["sources"].items():
        ports[origin] = {}
        discovered = set()
        for suite, paths in source["ports"].items():
            source_path = ROOT / paths["source"]
            adapted_path = ROOT / paths["adapted"]
            files.update((source_path, adapted_path))
            source_nodes = _test_nodes(source_path, suite)
            adapted_nodes = _test_nodes(adapted_path, suite)
            required = selected[origin] & source_nodes.keys()
            assert required == selected[origin] & adapted_nodes.keys()
            discovered.update(required)
            ports[origin][suite] = {
                "selected_nodes": {name: source_nodes[name] for name in sorted(required)},
                "adapted_nodes": {name: adapted_nodes[name] for name in sorted(required)},
                "source_unselected": sorted(source_nodes.keys() - required),
                "declared_exclusions": source["excluded"],
            }
        assert discovered == selected[origin]
    return {
        "schema_version": 1,
        "files": {
            str(path.relative_to(ROOT)): _digest(path.read_bytes()) for path in sorted(files)
        },
        "ports": ports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--robocorp-root", type=Path)
    parser.add_argument("--custom-root", type=Path)
    args = parser.parse_args()
    if bool(args.robocorp_root) != bool(args.custom_root):
        parser.error("--robocorp-root and --custom-root are required together")
    if args.robocorp_root:
        if args.write:
            parser.error("--write is only valid for the offline diagnostic artifact")
        _verify_authoritative(args.robocorp_root, args.custom_root)
        return 0
    rendered = json.dumps(_artifact(), indent=2, sort_keys=True) + "\n"
    if args.write:
        PROVENANCE_PATH.write_text(rendered)
        return 0
    if not PROVENANCE_PATH.exists() or PROVENANCE_PATH.read_text() != rendered:
        raise SystemExit(
            "offline contract provenance digest is stale; review the baseline/port change, then run "
            "`python scripts/check_contract_port_provenance.py --write`"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
