import toolkit
base='/workspace/engineering/pr221-current776-linux-consumer-preflight/'
paths=[base+name for name in ['current-input-admission-v2.py','test_current_input_admission.py','test_installed_consumer_runner_v2.py']]
toolkit.poetry('action_server','run','ruff','format',*paths)
toolkit.poetry('action_server','run','ruff','check',*paths)
