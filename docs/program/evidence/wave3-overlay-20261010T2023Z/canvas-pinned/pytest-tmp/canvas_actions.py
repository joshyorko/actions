
import hashlib
import json
import sys
from importlib.metadata import distribution
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from actions import mcp

EXPECTED_CORE_WHEEL = Path('/workspace/work/actions-mk3-evidence/canvas-pinned/pytest-tmp/test_canvas_view_calls_public_0/candidate-core/actions_core-1.0.3-py3-none-any.whl')
EXPECTED_CORE_WHEEL_SHA256 = '80f8e0b828ceb92d7cb7412a92f9306a4b0d2960365bf9aee899ad0cd71144f8'
UI_URI = "ui://action-canvas/v1/canvas.html?query-fixture=0.1"

@mcp.resource(
    UI_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {}}},
)
def canvas_view() -> str:
    return Path(__file__).with_name("canvas.html").read_text(encoding="utf-8")

@mcp.tool(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
    meta={"ui": {"resourceUri": UI_URI, "visibility": ["model", "app"]}},
)
def canvas_fixture_search(query: str) -> dict[str, object]:
    if query.casefold() == "alpha":
        return {
            "rows": [
                {"id": "record-001", "title": "Alpha guide", "category": "Guide"},
                {"id": "record-002", "title": "Alpha checklist", "category": "Checklist"},
            ],
            "artifact": {"handle": "art_7Wk3qN9pL2xD5mR8sV4cY1"},
            "error": None,
        }
    return {
        "rows": [],
        "artifact": None,
        "error": {
            "code": "no_matches",
            "message": "No records matched that query.",
        },
    }

@mcp.tool(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
    meta={"ui": {"resourceUri": UI_URI, "visibility": ["app"]}},
)
def canvas_fixture_artifact_status(handle: str) -> dict[str, str]:
    if handle != "art_7Wk3qN9pL2xD5mR8sV4cY1":
        raise ValueError("Unknown fixture artifact handle.")
    return {"status": "ready"}

@mcp.tool(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
def canvas_fixture_worker_provenance() -> dict[str, str]:
    core_distribution = distribution("actions-core")
    actions_module = Path(__import__("actions").__file__).resolve()
    installed_files = {
        Path(core_distribution.locate_file(file)).resolve()
        for file in (core_distribution.files or [])
    }
    if actions_module not in installed_files:
        raise AssertionError("worker actions module is not owned by actions-core")

    direct_url_value = core_distribution.read_text("direct_url.json")
    if not direct_url_value:
        raise AssertionError("worker actions-core has no direct_url.json")
    direct_url = json.loads(direct_url_value)
    source = urlsplit(direct_url.get("url", ""))
    if source.scheme != "file" or source.netloc not in {"", "localhost"}:
        raise AssertionError("worker actions-core was not installed from a local wheel")
    installed_wheel = Path(url2pathname(source.path)).resolve()
    if installed_wheel != EXPECTED_CORE_WHEEL.resolve():
        raise AssertionError("worker actions-core direct_url differs from the candidate wheel")

    archive = direct_url.get("archive_info", {})
    installed_sha256 = archive.get("hashes", {}).get("sha256")
    if installed_sha256 is None:
        hash_value = archive.get("hash", "")
        if hash_value.startswith("sha256="):
            installed_sha256 = hash_value.removeprefix("sha256=")
    candidate_sha256 = hashlib.sha256(installed_wheel.read_bytes()).hexdigest()
    if installed_sha256 != EXPECTED_CORE_WHEEL_SHA256 or candidate_sha256 != EXPECTED_CORE_WHEEL_SHA256:
        raise AssertionError("worker actions-core wheel SHA-256 differs from the candidate")
    return {
        "worker_prefix": sys.prefix,
        "actions_module": str(actions_module),
        "actions_core_version": core_distribution.version,
        "direct_url_wheel": str(installed_wheel),
        "wheel_sha256": candidate_sha256,
    }
