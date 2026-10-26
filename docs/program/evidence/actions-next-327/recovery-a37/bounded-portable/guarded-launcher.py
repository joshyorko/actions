import sys
import pytest
import owned_batch_capture

if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:], plugins=[owned_batch_capture]))
