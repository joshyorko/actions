from pathlib import Path
import ast
p=Path('/workspace/engineering/pr305/action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py')
s=p.read_text()
# Reuse the exact reviewed282 worker sample probe, changing only its fixture tool name/decorator.
accepted=Path('/workspace/engineering/pr282/action_server/tests/action_server_tests/mcp/test_canvas_query_template.py').read_text()
node=next(n for n in ast.walk(ast.parse(accepted)) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def published_core_identity()' in n.value)
published=node.value.replace('from actions.mcp import tool\n','').replace('@tool\ndef published_core_identity()', '@mcp.tool(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)\ndef canvas_fixture_worker_provenance()')
worker_start=s.index('@mcp.tool(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)\ndef canvas_fixture_worker_provenance()')
worker_end=s.index('\n"""',worker_start)
candidate=s[worker_start:worker_end]
prepare_start=s.index('    candidate_core_wheel_dir = tmp_path / "candidate-core"')
prepare_end=s.index('    subprocess.run(["npm", "run", "build:canvas"]',prepare_start)
oldprepare=s[prepare_start:prepare_end]
oldprepare=oldprepare[oldprepare.index('    candidate_core_wheel_dir'):]
# Move the accepted candidate preparation without changing its wheel command/manifest assertions.
oldprepare=oldprepare.replace('tmp_path / "candidate-core"','package_root / "candidate-core"').replace('    build_env = os.environ.copy()\n    build_env["UV_CACHE_DIR"] = str(build_temp_dir / "uv-cache")\n    build_env["TMPDIR"] = str(build_temp_dir)\n','').replace('package_yaml = tmp_path / "package.yaml"','package_yaml = package_root / "package.yaml"')
helpers='''# An external immutable acceptance runner may supply subprocess ownership only.
# The hook receives the exact command/cwd/env/timeout and returns CompletedProcess.
# It must not patch Runtime/Core behavior or any expectation in this test.
CANVAS_OWNED_RUNNER: Callable[..., subprocess.CompletedProcess[str]] | None = None
PUBLISHED_CORE_WHEEL_SHA256 = "8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265"
PUBLISHED_CORE_MODULE_SHA256 = {
    "actions": "790b5e45f1a570f4d209879a47007ce94b73aab76c522bd6400867168726b0d2",
    "actions.mcp": "c944de3b044a232143e66edd85ebd342b81b49cd100221689e22908d0dd5f365",
    "actions.mcp._metadata": "c5750e654cb3c1e057705d80e65c4f6a935a3d81e46450d6dbf68d37f45cb48c",
}


def _canvas_core_mode() -> str:
    mode = os.environ.get("ACTIONS_CANVAS_CORE_MODE", "candidate")
    assert mode in {"candidate", "published"}, "Unknown Canvas Core mode"
    if mode == "published":
        assert callable(CANVAS_OWNED_RUNNER), "Public mode requires an owned runner"
    return mode


def _canvas_command(command: list[str], *, cwd: Path, env: dict[str, str], timeout: float, mode: str) -> subprocess.CompletedProcess[str]:
    if mode == "published":
        assert callable(CANVAS_OWNED_RUNNER), "Public mode requires an owned runner"
        completed = CANVAS_OWNED_RUNNER(command, cwd=cwd, env=env, timeout=timeout)
    else:
        completed = subprocess.run(command, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True)
    # Preserve both output streams before enforcing the command's success contract.
    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)
    completed.check_returncode()
    return completed


def _prepare_canvas_core(repository_root: Path, package_root: Path, build_env: dict[str, str], mode: str) -> dict[str, Any]:
    assert mode in {"candidate", "published"}
    if mode == "published":
        (package_root / "package.yaml").write_text(
            "spec-version: v2\\nname: Canvas Runtime bridge acceptance\\n"
            "description: Isolated fixture using published Core 1.0.3.\\n"
            "version: 0.0.1\\ndependencies:\\n  conda-forge:\\n"
            "    - python=3.12\\n    - uv=0.9.26\\n  pypi:\\n    - actions-core=1.0.3\\n",
            encoding="utf-8",
        )
        return {
            "mode": "published", "declared_version": "1.0.3",
            "independently_verified_registry_wheel_sha256": PUBLISHED_CORE_WHEEL_SHA256,
            "measured_members": list(PUBLISHED_CORE_MODULE_SHA256),
            "whole_wheel_authenticated": False, "cold_registry_acquisition": False,
        }
'''+oldprepare+'''    return {"mode": "candidate", "path": str(candidate_core_wheel), "sha256": candidate_core_wheel_sha256}


'''
helpers+='PUBLISHED_CORE_PROBE = '+repr(published)+'\n\nCANDIDATE_CORE_PROBE = '+repr(candidate)+'\n\n'
helpers+='''def _canvas_worker_probe(core: dict[str, Any]) -> str:
    if core["mode"] == "published":
        return PUBLISHED_CORE_PROBE
    return (
        "EXPECTED_CORE_WHEEL = Path(" + repr(core["path"]) + ")\\n"
        "EXPECTED_CORE_WHEEL_SHA256 = " + repr(core["sha256"]) + "\\n"
        + CANDIDATE_CORE_PROBE
    )


def _assert_canvas_playwright_report(report: dict[str, Any]) -> None:
    specs: list[dict[str, Any]] = []
    def collect(suites: list[dict[str, Any]]) -> None:
        for suite in suites:
            specs.extend(suite.get("specs", []))
            collect(suite.get("suites", []))
    collect(report.get("suites", []))
    assert not report.get("errors"), "Playwright reported errors"
    assert len(specs) == 1, "Expected exactly one Canvas browser case"
    assert specs[0]["title"] == "official bridge renders a real Runtime Action result"
    tests = specs[0]["tests"]
    assert len(tests) == 1 and len(tests[0]["results"]) == 1
    assert tests[0]["results"][0]["status"] == "passed", "Browser case did not pass without skips/retries"


def _run_canvas_browser(frontend_root: Path, runtime_url: str, mode: str) -> dict[str, Any]:
    env = os.environ.copy()
    selected = env.get("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if mode == "published":
        assert selected, "Public mode requires an explicit Chromium executable"
    if not selected:
        selected = shutil.which("chromium")
    browser_path = Path(selected).resolve(strict=True) if selected else None
    if browser_path:
        assert browser_path.is_file() and os.access(browser_path, os.X_OK)
        env["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = str(browser_path)
    env["CANVAS_RUNTIME_MCP_URL"] = runtime_url
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        env["CANVAS_HARNESS_PORT"] = str(port_probe.getsockname()[1])
    if mode == "candidate":
        _canvas_command(["npm", "run", "test:canvas-harness", "--", "--grep", "real Runtime Action result"], cwd=frontend_root, env=env, timeout=180, mode=mode)
        version = _canvas_command([str(browser_path), "--version"], cwd=frontend_root, env=env, timeout=15, mode=mode).stdout.strip() if browser_path else "Playwright-pinned Chromium"
        return {"executable": str(browser_path) if browser_path else None, "version": version, "sha256": hashlib.sha256(browser_path.read_bytes()).hexdigest() if browser_path else "not-recorded", "selection": "explicit" if selected == os.environ.get("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") and selected else "system-or-managed"}
    assert browser_path is not None
    cli = frontend_root / "node_modules/@playwright/test/cli.js"
    node = shutil.which("node")
    assert node and cli.is_file(), "Use prepared Node/Playwright"
    lock_path = frontend_root / "package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    version = json.loads((cli.parent / "package.json").read_text(encoding="utf-8"))["version"]
    assert version == lock["packages"]["node_modules/@playwright/test"]["version"]
    browser_sha256 = hashlib.sha256(browser_path.read_bytes()).hexdigest()
    browser_version = _canvas_command([str(browser_path), "--version"], cwd=frontend_root, env=env, timeout=10, mode=mode).stdout.strip()
    assert browser_version
    with tempfile.TemporaryDirectory(prefix="cv305-", dir="/tmp" if os.name != "nt" else None) as browser_temp:
        root = Path(browser_temp)
        if os.name != "nt":
            root.chmod(0o700)
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = str(root)
        completed = _canvas_command([node, str(cli), "test", "--config", str(frontend_root / "playwright.canvas-harness.config.ts"), "--grep", "^official bridge renders a real Runtime Action result$", "--workers", "1", "--reporter", "json"], cwd=frontend_root, env=env, timeout=180, mode=mode)
        _assert_canvas_playwright_report(json.loads(completed.stdout))
    assert not root.exists()
    assert hashlib.sha256(browser_path.read_bytes()).hexdigest() == browser_sha256
    return {"status": "passed", "selection": "explicit", "path": str(browser_path), "executable": str(browser_path), "sha256": browser_sha256, "version": browser_version, "playwright_version": version, "frontend_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(), "temporary_root": str(root), "temporary_root_removed": True}


'''
s=s[:worker_start]+s[worker_end:]
s=s.replace('EXPECTED_CORE_WHEEL = Path("__EXPECTED_CORE_WHEEL__")\nEXPECTED_CORE_WHEEL_SHA256 = "__EXPECTED_CORE_WHEEL_SHA256__"\n','')
replacement='''    build_env = os.environ.copy()
    build_env["UV_CACHE_DIR"] = str(build_temp_dir / "uv-cache")
    build_env["TMPDIR"] = str(build_temp_dir)
    core = _prepare_canvas_core(repository_root, tmp_path, build_env, mode)
'''
a=s.index('    candidate_core_wheel_dir = tmp_path / "candidate-core"');b=s.index('    subprocess.run(["npm", "run", "build:canvas"]',a)
s=s[:a]+replacement+s[b:]
s=s.replace('    subprocess.run(["npm", "run", "build:canvas"], cwd=frontend_root, check=True)','    _canvas_command(["npm", "run", "build:canvas"], cwd=frontend_root, env=build_env, timeout=120, mode=mode)')
a=s.index('    action_source = action_source.replace(');b=s.index('    (tmp_path / "canvas_actions.py")',a)
s=s[:a]+'    action_source += _canvas_worker_probe(core)\n'+s[b:]
s=s.replace('    repository_root = Path(__file__).resolve().parents[4]\n    frontend_root', '    mode = _canvas_core_mode()\n    repository_root = Path(__file__).resolve().parents[4]\n    frontend_root')
s=s.replace('            assert worker_provenance["wheel_sha256"] == candidate_core_wheel_sha256','''            if mode == "candidate":
                assert worker_provenance["wheel_sha256"] == core["sha256"]
            else:
                assert worker_provenance["version"] == "1.0.3"
                assert worker_provenance["module_hashes"] == PUBLISHED_CORE_MODULE_SHA256''')
a=s.index('    playwright_executable = shutil.which("chromium")');b=s.index('    runtime_call_observations.extend(',a)
s=s[:a]+'    browser = _run_canvas_browser(frontend_root, f"http://127.0.0.1:{action_server_process.port}/mcp", mode)\n'+s[b:]
a=s.index('    if playwright_executable:\n');b=s.index('    receipt_path = ',a)
s=s[:a]+s[b:]
s=s.replace('''                "schema_version": 2,
                "actions_core_wheel": {
                    "path": str(candidate_core_wheel),
                    "sha256": candidate_core_wheel_sha256,
                },''','''                "schema_version": 3,
                "core_mode": mode,
                **({"actions_core_wheel": core} if mode == "candidate" else {"published_core": core}),''')
a=s.index('                "browser": {');b=s.index('                "runtime_call_observations":',a)
s=s[:a]+'''                "browser": browser,
                "limits": [
                    "Fixture artifact status is not real artifact resolution.",
                    "Public Core provenance measures three members, not full-wheel authentication or cold acquisition.",
                    "Native source and owned cleanup are admitted separately by the immutable runner; no production host/ChatGPT proof.",
                ],
                "cache": {"source_root": str(tmp_path.resolve()), "build_root": str(build_temp_dir.resolve()), "uv_cache": build_env["UV_CACHE_DIR"], "outside_synchronized_package": not build_temp_dir.resolve().is_relative_to(tmp_path.resolve())},
'''+s[b:]
s=s.replace('import subprocess\n','import subprocess\nimport sys\nimport tempfile\n')
s=s.replace('@pytest.mark.integration_test\n@pytest.mark.skipif(\n    os.environ.get("ACTIONS_CANVAS_RUNTIME_ACCEPTANCE")',helpers+'@pytest.mark.integration_test\n@pytest.mark.skipif(\n    os.environ.get("ACTIONS_CANVAS_RUNTIME_ACCEPTANCE")')
p.write_text(s)
