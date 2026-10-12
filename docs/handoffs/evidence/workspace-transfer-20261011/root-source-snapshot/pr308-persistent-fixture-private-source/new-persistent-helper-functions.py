def _validate_persistent_call_series(
    rows, *, expected_compatibility, artifact_digest, receipt_path,
    source_hash, managed_root, source_root,
):
    """Validate measured six-call facts; synthetic controls are never actual proof."""
    import math

    assert isinstance(rows, list) and len(rows) == 6
    keys = {
        "ordinal", "counter", "worker_pid", "worker_created", "wrapper_pid",
        "wrapper_created", "artifact_digest", "compatibility", "receipt_path",
        "action_source_sha256", "action_source_path", "python_executable",
        "core_origin", "core_version",
    }
    first = rows[0]
    for index, row in enumerate(rows, 1):
        assert isinstance(row, dict) and set(row) == keys
        assert type(row["ordinal"]) is int and row["ordinal"] == index
        assert type(row["counter"]) is int and row["counter"] == index
        for key in ("worker_pid", "wrapper_pid"):
            assert type(row[key]) is int and 0 < row[key] < 2**63
        for key in ("worker_created", "wrapper_created"):
            assert type(row[key]) in (int, float)
            assert math.isfinite(row[key]) and row[key] > 0
        for key in ("worker_pid", "worker_created", "wrapper_pid", "wrapper_created"):
            assert row[key] == first[key]
        assert row["artifact_digest"] == artifact_digest
        assert isinstance(row["compatibility"], dict)
        assert row["compatibility"] == expected_compatibility
        assert row["receipt_path"] == receipt_path
        assert row["action_source_sha256"] == source_hash
        assert row["core_version"] == "1.0.2"
        for key, root in (
            ("python_executable", managed_root), ("core_origin", managed_root),
            ("action_source_path", source_root),
        ):
            assert isinstance(row[key], str) and Path(row[key]).is_absolute()
            assert Path(row[key]).resolve().is_relative_to(root.resolve())
            assert row[key] == first[key]
    return rows


def _run_persistent_staged_calls(
    pool, package, action, run, run_dir, source_digests,
    managed_root, source_root, expected_compatibility,
):
    """Execute six real pool calls; never substitute the native runner or handler."""
    from dataclasses import replace

    import psutil

    from actions.server._rcc_runtime_adapter import load_descriptor

    rows = []
    last_handle = None
    result_json = None
    expected_artifact = None
    expected_receipt = None
    for ordinal in range(1, 7):
        directory = run_dir / str(ordinal)
        directory.mkdir()
        input_json = directory / "input.json"
        input_json.write_text("{}", encoding="utf-8")
        result_json = directory / "result.json"
        output = directory / "output.txt"
        owned_run = replace(run, id=f"{run.id}-{ordinal}", numbered_id=ordinal)
        with pool.obtain_process_for_action(action) as handle:
            assert handle.run_action(
                owned_run, package, action, input_json, directory, output,
                result_json, {}, {}, False,
            ) == 0
            result = json.loads(result_json.read_text(encoding="utf-8"))["result"]
            assert isinstance(result, dict)
            assert isinstance(result.get("worker_pid"), str)
            assert result["worker_pid"].isdecimal()
            assert result.get("counter") == str(ordinal)
            worker_pid = int(result["worker_pid"])
            assert worker_pid > 0
            wrapper = psutil.Process(handle.pid)
            worker = psutil.Process(worker_pid)
            worker_created = worker.create_time()
            wrapper_created = wrapper.create_time()
            assert worker_pid == wrapper.pid or any(
                parent.pid == wrapper.pid and parent.create_time() == wrapper_created
                for parent in worker.parents()
            )
            descriptor = load_descriptor(package.env_json)
            assert descriptor is not None
            assert descriptor.rcc_compatibility is not None
            compatibility = descriptor.rcc_compatibility.to_dict()
            receipt = str(handle._rcc_wrapper.receipt_file.resolve())
            if expected_artifact is None:
                expected_artifact = descriptor.artifact_digest
                expected_receipt = receipt
            rows.append({
                "ordinal": ordinal, "counter": int(result["counter"]),
                "worker_pid": worker_pid, "worker_created": worker_created,
                "wrapper_pid": wrapper.pid, "wrapper_created": wrapper_created,
                "artifact_digest": descriptor.artifact_digest,
                "compatibility": compatibility, "receipt_path": receipt,
                "action_source_sha256": result.get("action_source_sha256"),
                "action_source_path": result.get("action_source_path"),
                "python_executable": result.get("python_executable"),
                "core_origin": result.get("core_origin"),
                "core_version": result.get("core_version"),
            })
            last_handle = handle
    _validate_persistent_call_series(
        rows, expected_compatibility=expected_compatibility,
        artifact_digest=expected_artifact, receipt_path=expected_receipt,
        source_hash=source_digests["action.py"], managed_root=managed_root,
        source_root=source_root,
    )
    assert last_handle is not None and result_json is not None
    return last_handle, result_json, rows
