import sys,toolkit
toolkit.run([sys.executable,"-m","pytest","-q","developer/tests/test_rcc_provider_rollback_workflow.py","developer/tests/test_rcc_provider_rollback_summary.py"])
toolkit.run([sys.executable,"-m","ruff","check","developer/tests/test_rcc_provider_rollback_workflow.py"])
toolkit.run([sys.executable,"-m","ruff","format","--check","developer/tests/test_rcc_provider_rollback_workflow.py"])
toolkit.poetry("action_server","run","isort","--check",str(toolkit.REPOSITORY_ROOT/"developer/tests/test_rcc_provider_rollback_workflow.py"),str(toolkit.REPOSITORY_ROOT/".github/workflows/_gen_workflows.py"))
toolkit.run([sys.executable,"-m","py_compile","developer/tests/test_rcc_provider_rollback_workflow.py",".github/workflows/_gen_workflows.py"])
