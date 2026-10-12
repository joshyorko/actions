import os
import toolkit
os.environ['ADMISSION_REVIEW_GATE'] = '/workspace/engineering/pr221-current776-linux-consumer-preflight/current-input-admission.py'
toolkit.poetry('action_server', 'run', 'python', '-m', 'pytest', '-q', '/workspace/engineering/pr221-current776-linux-consumer-preflight/test_current_input_admission.py', '-k', 'metadata_rejects_non_utf8')
