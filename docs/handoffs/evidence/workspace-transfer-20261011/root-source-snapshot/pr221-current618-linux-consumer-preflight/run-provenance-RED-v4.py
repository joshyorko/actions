import toolkit
base='/workspace/engineering/pr221-current618-linux-consumer-preflight/'
toolkit.run(['env','ADMISSION_PROVENANCE_GATE='+base+'current-input-admission-v3.py','poetry','run','python','-m','pytest','-c','/workspace/engineering/pr282/action_server/pyproject.toml','-q',base+'test_current_input_provenance_v4.py'],cwd=toolkit.REPOSITORY_ROOT/'action_server')
