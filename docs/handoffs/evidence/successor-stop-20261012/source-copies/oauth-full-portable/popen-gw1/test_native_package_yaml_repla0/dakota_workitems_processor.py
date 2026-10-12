from pathlib import Path

def _local_wheel_path_from_file_url(source_url: str) -> Path:
    """Resolve a local wheel URL using the target platform's path rules."""
    from urllib.parse import urlparse
    from urllib.request import url2pathname

    parsed = urlparse(source_url)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
        raise ValueError("candidate wheel install source is not a local file URL")
    return Path(url2pathname(parsed.path)).resolve()


from actions import action


@action
def process_work_item(
    db_path: str,
    files_dir: str,
    expected_id: str,
    scenario: str,
    expected_core_wheel: str,
    expected_core_wheel_sha256: str,
    expected_core_version: str,
    core_install_report: str,
    core_install_proof: str,
) -> dict[str, str]:
    import hashlib
    import json
    from importlib.metadata import distribution
    from pathlib import Path
    import actions

    core_distribution = distribution("actions-core")
    if core_distribution.version != expected_core_version:
        raise AssertionError("candidate actions-core version is not installed")
    module_path = Path(actions.__file__).resolve()
    distribution_files = {
        Path(core_distribution.locate_file(file)).resolve()
        for file in (core_distribution.files or [])
    }
    if module_path not in distribution_files:
        raise AssertionError("actions module is not owned by actions-core distribution")

    wheel_path = Path(expected_core_wheel).resolve()
    wheel_digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    if wheel_digest != expected_core_wheel_sha256:
        raise AssertionError("candidate actions-core wheel bytes changed")
    install_report = json.loads(Path(core_install_report).read_text(encoding="utf-8"))
    core_installs = [
        entry
        for entry in install_report.get("install", [])
        if entry.get("metadata", {}).get("name", "").lower().replace("_", "-")
        == "actions-core"
    ]
    if len(core_installs) != 1:
        raise AssertionError("candidate actions-core install is absent from pip report")
    source = core_installs[0].get("download_info", {})
    source_url = source.get("url", "")
    if _local_wheel_path_from_file_url(source_url) != wheel_path:
        raise AssertionError("actions-core was not installed from the candidate wheel")
    if source.get("archive_info", {}).get("hashes", {}).get("sha256") != wheel_digest:
        raise AssertionError("pip install report is not bound to candidate wheel bytes")
    Path(core_install_proof).write_text(
        json.dumps(
            {
                "actions_core_version": core_distribution.version,
                "actions_module_owned_by_distribution": True,
                "install_source_matches_candidate": True,
                "wheel_sha256": wheel_digest,
                "pip_report_sha256": hashlib.sha256(
                    Path(core_install_report).read_bytes()
                ).hexdigest(),
            }
        ),
        encoding="utf-8",
    )

    from actions.work_items import SQLiteAdapter, State

    adapter = SQLiteAdapter(db_path=db_path, files_dir=files_dir)
    if scenario == "recover":
        recovered = adapter.recover_orphaned_work_items()
        if expected_id not in recovered:
            raise AssertionError("synthetic abandoned reservation was not recovered")

    item_id = adapter.reserve_input()
    if item_id != expected_id:
        raise AssertionError("consumer reserved an unexpected synthetic input")
    payload = adapter.load_payload(item_id)

    if scenario == "fail":
        adapter.release_input(
            item_id,
            State.FAILED,
            exception={
                "type": "APPLICATION",
                "code": "SYNTHETIC_PROCESSOR_FAILURE",
                "message": "synthetic consumer failure",
            },
        )
        raise RuntimeError("synthetic consumer failed after recording Work Item failure")

    output_id = adapter.create_output(
        item_id,
        {"input": payload, "scenario": scenario, "result": "synthetic success"},
    )
    adapter.release_input(item_id, State.DONE)
    return {"item_id": item_id, "output_id": output_id}
