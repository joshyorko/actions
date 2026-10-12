import hashlib
import json
from pathlib import Path

root = Path('/workspace/engineering/campaign-checkpoint')
dest = root / 'docs/program/evidence/wave11/current-engineering-20261011'
manifest = json.loads((dest / 'manifest.json').read_text())
files = {
    'pr282-windows-source-checkpoint.json': '/workspace/engineering/pr282-windows-owned/successor-receipt.json',
    'pr221-actual-clean-consumer.json': '/workspace/actions-cloud/receipts/runtime-103-preflight/actual-clean-consumer-receipt.json',
    'pr221-independent-clean-consumer.json': '/workspace/engineering/pr221-clean-consumer-independent-review/actual-one-consumer-review.json',
    'pr221-clean-consumer-runner.py': '/workspace/actions-cloud/receipts/runtime-103-preflight/installed-consumer-runner.py',
    'pr221-clean-consumer-runner-tests.py': '/workspace/actions-cloud/receipts/runtime-103-preflight/test_installed_consumer_runner.py',
    'pr221-clean-consumer-proposal.json': '/workspace/actions-cloud/receipts/runtime-103-preflight/clean-consumer-proposal.json',
    'oauth-build-design.json': '/workspace/engineering/oauth-config-design-owned/design-receipt.json',
    'oauth-build-design.md': '/workspace/engineering/oauth-config-design-owned/design.md',
    'oauth-canonical-proposed.patch': '/workspace/engineering/oauth-config-design-owned/canonical-guide-proposed.patch',
}
for name in ['consumer-proof.json', 'execution-cleanup-receipt.json', 'pip-install-report.json', 'installed-inventory-raw.json', 'attempt-identity.json', 'install-argv.json']:
    files['pr221-' + name] = '/workspace/actions-cloud/receipts/runtime-103-preflight/installed-linux-12340bb17-1/' + name
for name, source in files.items():
    data = Path(source).read_bytes()
    (dest / name).write_bytes(data)
    manifest[name] = {'source': source, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
merge = {'pr': 290, 'head': '5c8084c61389e293eb992c24bc0f2962f705378e', 'merge': 'fbde0d3a248c47c9964851355f96575c89a87329', 'parents': ['ba85aac7324ea4463bfba8c5f8586e27706dc2fe', '5c8084c61389e293eb992c24bc0f2962f705378e'], 'tree': '65954e87147645985ee44f82de9907e937892112', 'tested_merge': '7176fc8f8f5b0c867a4b334e99dd3375826373c6', 'checks': {'success': 27, 'pending': 0, 'failure': 0}, 'merged_at': '2026-10-11T03:52:03Z', 'method': 'normal pinned-head merge, no bypass', 'acceptance': 'bounded source/control merge; no full issue closure or publication'}
(dest / 'pr290-actual-integration.json').write_text(json.dumps(merge, indent=2) + '\n')
data = (dest / 'pr290-actual-integration.json').read_bytes()
manifest['pr290-actual-integration.json'] = {'source': 'authenticated GitHub merge and readback', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
(dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
guide = root / 'docs/skills/repository-operations.md'
s = guide.read_text()
old = 'never rebuilds. It verifies the exact seven artifacts and retained\n`actions-runtime-manifest.sha256` before running Twine 6.2.0. With `--publish`,'
new = 'never rebuilds. It verifies the exact seven artifacts and retained\n`actions-runtime-manifest.sha256`. `--dry-run` then returns without running\nTwine or reading publication credentials; retain a separate strict Twine\nresult when admitting metadata. The publishing path requires Twine 6.2.0. With `--publish`,'
assert s.count(old) == 1
s = s.replace(old, new)
proposal = Path('/workspace/actions-cloud/receipts/runtime-103-preflight/canonical-documentation-proposal.md').read_text()
blocks = proposal.split('Insert after the paragraph')[1].split('Documentation improvement:')[0]
quoted = '\n'.join(line[2:] if line.startswith('> ') else '' for line in blocks.splitlines() if line.startswith('>'))
follow = Path('/workspace/actions-cloud/receipts/runtime-103-preflight/canonical-documentation-proposal-followup.md').read_text().split('Documentation improvement:')[0]
extra = '\n'.join(line[2:] if line.startswith('> ') else '' for line in follow.splitlines() if line.startswith('>'))
anchor = 'Binary release names use GitHub expressions containing `${{ github.ref_name }}`; shell\nliterals such as `$tag-linux64` are not valid action inputs.\n'
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + '\n' + quoted + '\n\n' + extra + '\n')
old = '`ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD`. PR builds run equivalent frontend and\nOAuth generation without credentials; PAT-bearing variants are limited to tag\npushes.'
replacement = Path('/workspace/engineering/oauth-config-design-owned/canonical-guide-proposed.patch').read_text()
addition = '\n'.join(line[1:] for line in replacement.splitlines() if line.startswith('+') and not line.startswith('+++'))
assert s.count(old) == 1
tail = ' Twine version and metadata checks run with `PYPI` and `TWINE_*` removed'
assert addition.endswith(tail)
s = s.replace(old, addition[:-len(tail)])
receipt = json.loads(Path('/workspace/engineering/pr290-independent-current-acceptance/independent-actual-receipt-review.json').read_text())
delta = receipt['documentation_improvement']['exact_delta'].split('add: "')[1][:-1]
anchor = 'passes; its selected lifecycle cases do not prove unselected startup-reader cleanup.\n'
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + '\n' + delta + '\n')
guide.write_text(s)
readme = dest / 'README.md'
s = readme.read_text()
s += '\n#290 subsequently integrated normally at `fbde0d3a248c47c9964851355f96575c89a87329`, with the same reviewed tree `65954e87` and 27 successful checks. #310 and #309 are refreshing against this actual target. #302 must then create a current source candidate and repin its strict three-case control; its earlier receipt remains historical. Integrate #310 before #302 changes Runtime producer inputs.\n\nThe exact retained Runtime Linux cp312 wheel from PR producer `12340bb17` passed one fresh isolated public-floor consumer: all196 Python members equal original wheel bytes,195 equal tracked producer-tree bytes, private-Core scan empty, pip check and CLI1.0.3 passed. Independent actual review `00d1b3c5` reconciles the original wheel and raw receipts. Ten captured process identities were cleaned and the environment removed; this is not service/natural-shutdown or universal adoption proof. The generated196th member contains two empty OAuth strings. Original native configuration contains API error objects. These are separate release-content blockers: the successful narrow consumer does not qualify OAuth or publication.\n\n#282 source successor `0d8d0803` fixes committed-byte/CRLF fixtures and passed Toolkit103 locally. Its current Linux browser testcase passed, but strict hosted receipt admission failed; no green consumer admission is claimed. #311 exact1151 Linux/macOS source and native suites passed but configured Isort rejected the diagnostic test imports; Windows remains pending at this checkpoint. Both failures remain engineering holds.\n\nThe OAuth design is a read-only proposal, not implemented source policy. Its immutable-manifest/mode architecture is deferred pending authoritative source ownership. Root accepted the smaller existing-task boundary guard for the next source slot; no replacement repository, synthetic release configuration, credentials, or infrastructure is authorized. Canonical guidance now corrects dry-run/Twine, PR-producer identity, host-wheel selection, installed/generated-member boundaries and false equivalent OAuth claims. Upstream disposition: none.\n'
readme.write_text(s)
print(json.dumps({'retained_files': len(files) + 1, 'guide_changed': True}))
