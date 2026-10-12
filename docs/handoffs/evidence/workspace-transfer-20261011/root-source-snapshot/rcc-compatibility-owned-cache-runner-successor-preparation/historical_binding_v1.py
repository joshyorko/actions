"""One fixed historical original-row alias; never fabricate payload bytes."""
import json
from pathlib import Path

from historical_failed_receipt_archive_v1 import verify_exact_historical_receipt
from runner_contracts_v3 import need


MAPPING = {
    'path': '/workspace/engineering/root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json',
    'bytes': 1864, 'sha256': 'cc73027ce86ea0965f3bdd88ed3398c322dcf012b337a4ca161966f19ffee6c7', 'mode': '0o600',
}
ORIGINAL = {
    'path': '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-1/OWNERFINAL-one-version-actual-result.json',
    'bytes': 1696, 'sha256': '8dc25bb1b99503af386d12d32c0637aa3503617c6f97d66a83f4643969934d4c', 'mode': '0o600',
}


def verify_missing_original(row):
    need(type(row) is dict and json.dumps(row, sort_keys=True) == json.dumps(ORIGINAL, sort_keys=True)
         and not Path(row['path']).exists()
         and not Path(row['path']).is_symlink(), 'UNAPPROVED_MISSING_BINDING')
    return verify_exact_historical_receipt(row, MAPPING)
