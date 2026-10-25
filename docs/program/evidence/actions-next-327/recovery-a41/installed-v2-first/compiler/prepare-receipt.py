"""Convert trusted local RCC publish output to an observed prepared receipt."""
import argparse
import hashlib
import json
from pathlib import Path
from actions.server.deployments.package_revision_compiler import (
    PreparedRccEnvironment, RccBuildIdentity, load_prepared_rcc_environment,
)
parser = argparse.ArgumentParser()
parser.add_argument("compiler", type=Path)
args = parser.parse_args()
base = args.compiler.resolve()
package_digest = "sha256:" + hashlib.sha256((base / "package.yaml").read_bytes()).hexdigest()
assert package_digest == "sha256:15a134c950602faa1f8658a61f6e5195308e66e702d4134c0d8de7d1fd582890"
rows = []
for line in (base / "publish.jsonl").read_text().splitlines():
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        continue
    if isinstance(value, dict) and {"specificationDigest", "artifactDigest"} <= value.keys():
        rows.append(value)
assert len(rows) == 1, "expected exactly one RCC publish result"
result = rows[0]
prepared = PreparedRccEnvironment(base / "robocorp", package_digest,
    RccBuildIdentity(result["specificationDigest"], result["artifactDigest"]))
path = base / "prepared.json"
path.write_bytes(prepared.to_receipt_bytes())
path.chmod(0o600)
assert load_prepared_rcc_environment(path) == prepared
print(result["artifactDigest"])
