from pathlib import Path
import subprocess
import toolkit
R=toolkit.REPOSITORY_ROOT
assert R==Path('/workspace/engineering/pr306')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()=='fada8e068f61f6e0e380ec4685eed2f4cf0b9ade'
assert subprocess.check_output(['git','status','--porcelain'],cwd=R)==b''
toolkit.poetry('action_server','run','python','-m','pytest','-q','-n','0',
 'tests/action_server_tests/test_native_startup_diagnostics.py',
 'tests/action_server_tests/common_tests/test_process.py',
 'tests/action_server_tests/test_database.py','tests/action_server_tests/test_database_shared.py',
 'tests/action_server_tests/test_native_startup_diagnostics_workflow.py',
 'tests/action_server_tests/test_rcc_runtime_adapter.py',
 'tests/action_server_tests/test_source_staging_rcc_consumer.py',
 'tests/action_server_tests/mcp/test_resource_history.py',
 'tests/action_server_tests/test_cli_mcp_resource_history.py',
 'tests/action_server_tests/run_outputs/test_migration.py',
 '-m','not integration_test')
toolkit.poetry('action_server','run','invoke','lint','typecheck')
