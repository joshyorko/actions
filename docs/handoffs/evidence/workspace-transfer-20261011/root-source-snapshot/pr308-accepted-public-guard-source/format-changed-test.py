import toolkit
toolkit.poetry("action_server", "run", "ruff", "format", "--config", str(toolkit.REPOSITORY_ROOT / "devutils/ruff.toml"), "tests/action_server_tests/test_dakota_rcc_acceptance.py")
