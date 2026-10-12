"""Exact process-local import and fresh once-root identity; no native call."""
import hashlib
import sys
from pathlib import Path

DIRECTORIES = (
    '/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor',
    '/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation',
)
sys.path[:0] = list(DIRECTORIES)

from owned_cache_policy_v8 import ROOTS, need
import owned_cache_policy_v8

CACHE = Path(DIRECTORIES[0]) / 'owned_cache_policy_v8.py'
TRANSPORT = Path(DIRECTORIES[0]) / 'actual_transport_v8.py'
need(Path(owned_cache_policy_v8.__file__).resolve() == CACHE, 'V9_ORIGINAL_CACHE_MODULE_PATH')
need(hashlib.sha256(CACHE.read_bytes()).hexdigest() == '4ccac4e3bd2c1e91352ef4e647968b4ca61f8691e1fc0f41e72a128a2942c205', 'V9_ORIGINAL_CACHE_MODULE_HASH')
need(hashlib.sha256(TRANSPORT.read_bytes()).hexdigest() == '33dda17140ef749e22f086cc91b92ed8c3230fddfde8a4a369769e2183f695a1', 'V9_ORIGINAL_TRANSPORT_HASH')
need(ROOTS == {
    'control3': '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-3',
    'released5': '/dev/shm/actions-rcc-compatibility-actual-released5-20261011-owned-pkgs-1',
    'candidate7276': '/dev/shm/actions-rcc-compatibility-actual-candidate7276-20261011-owned-pkgs-1',
}, 'V9_ORIGINAL_ONCE_ROOT_MAP')
# Original cache functions/predicates remain unchanged. This named successor
# binds exactly one fresh root; no operator-supplied root is accepted.
ROOTS['control3'] = '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-4'
from actual_transport_v8 import main
