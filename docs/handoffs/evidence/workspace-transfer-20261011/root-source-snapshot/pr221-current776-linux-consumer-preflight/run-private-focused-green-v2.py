import toolkit
base='/workspace/engineering/pr221-current776-linux-consumer-preflight/'
files=[base+name for name in ['current-input-admission-v2.py','installed-consumer-runner-v2.py','test_current_input_admission.py','test_installed_consumer_runner_v2.py']]
toolkit.poetry('action_server','run','ruff','format',*files)
toolkit.poetry('action_server','run','ruff','check',*files)
toolkit.poetry('action_server','run','ruff','format','--check',*files)
toolkit.poetry('action_server','run','isort','--check',*files)
toolkit.poetry('action_server','run','python','-m','pytest','-q',files[2],files[3])
