import toolkit
base='/workspace/engineering/pr221-current618-linux-consumer-preflight/'
toolkit.poetry('action_server','run','ruff','check',base+'installed-consumer-runner-v3.py')
toolkit.poetry('action_server','run','ruff','format','--check',base+'installed-consumer-runner-v3.py')
toolkit.poetry('action_server','run','python','-m','pytest','-c','/workspace/engineering/pr282/action_server/pyproject.toml','-q',base+'test_current_input_admission.py',base+'test_installed_consumer_runner_v3.py','-k','original_current_input_gate_reads or current_source_and_archive_binding_mutations or live_source_binding_passes')
