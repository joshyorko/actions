import sys
import pytest
import owned_batch_capture
raise SystemExit(pytest.main(sys.argv[1:],plugins=[owned_batch_capture]))
