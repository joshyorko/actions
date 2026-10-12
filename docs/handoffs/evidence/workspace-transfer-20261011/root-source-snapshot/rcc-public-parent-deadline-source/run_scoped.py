import toolkit

toolkit.poetry('action_server', 'run', 'python', '-c', "import actions.server; from pathlib import Path; assert Path(actions.server.__file__).resolve() == Path('/workspace/engineering/rcc-public/action_server/src/actions/server/__init__.py'); print('CURRENT_PUBLIC_RUNTIME_SOURCE_ORIGIN=PASS')")
toolkit.poetry('action_server', 'run', 'python', '-m', 'pytest', '-q', 'tests/action_server_tests/test_dakota_rcc_acceptance.py', 'tests/action_server_tests/test_rcc_runtime_adapter.py', 'scripts/test_native_runtime_artifact_binding.py', '-m', 'not integration_test and not real_rcc')
