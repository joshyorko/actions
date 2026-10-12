"""Read-only shortlist/binding plan; does not rerun the frozen checkpoint collector."""
import datetime
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path('/workspace/engineering')
OUT = Path(__file__).parent
REPO = ROOT/'campaign-checkpoint'
COMMIT = '62f4e180f6c894777ebc8ed3a729e88d2f6531d6'
BRANCH = 'handoff/actions-swarm-mk3-wave8-20261010'


def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(REPO), *args], timeout=15)


def bind(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                mode=oct(stat.S_IMODE(path.stat().st_mode)))


assert git('rev-parse', 'HEAD').decode().strip() == COMMIT
assert git('rev-parse', 'refs/heads/'+BRANCH).decode().strip() == COMMIT
original_status = git('status', '--porcelain')
assert original_status.decode().splitlines() == [
    ' M docs/skills/provenance-observability.md', ' M docs/skills/repository-operations.md']
dirty = {name: bind(REPO/name) for name in (
    'docs/skills/repository-operations.md', 'docs/skills/provenance-observability.md')}
collector = bind(ROOT/'checkpoint-current-engineering-after299-0938.py')
assert collector['sha256'] == '0319f50eaa81800c7edf3bc75b80182bbfc5721ba0ef86d45c199e3bc0a6d4d1'
prior_blobs = {row.split(b'\t', 1)[0].split()[2].decode()
               for row in git('ls-tree', '-r', '-z', COMMIT).split(b'\0') if row}
GROUPS = {
'actual300': [
'pr300-current74-root-normal-ready-and-merge/OWNERFINAL-root-actual-normal-PR300-integration.json',
'pr300-current74-actual-integration-independent-review/OWNERFINAL-independent-actual-normal-current74-PR300-integration-review.json'],
'actual312': [
'root-pr312-currentec70-one-normal-ready-and-merge/OWNERFINAL-root-one-normal-currentec70-PR312-integration-named-successor.json',
'pr312-actual-a54-independent-integration-review/OWNERFINAL-independent-actual-a54-PR312-normal-integration-review.json',
'pr312-currentec70-SOURCEFULL-independent-actual-review/OWNERFINAL-independent-currentec70-configured-SOURCEFULL-review.json'],
'current_e4_source_cache': [
'pr308-cache-current-e3c-source/OWNERFINAL-current-e4ff-reviewed-cache-application-and-e3c-ordinary-source-LIGHT.json',
'pr308-currente4ff-independent-SOURCE-LIGHT-review/OWNERFINAL-independent-current-e4ff-owned-cache-ordinary-source-LIGHT-review.json',
'root-pr308-currente4ff-one-sourcefull-v2/OWNERFINAL-root-currente4ff-configured-SOURCEFULL-PASS-v2.json',
'pr308-currente4ff-SOURCEFULL-independent-actual-review/OWNERFINAL-independent-current-e4ff-configured-SOURCEFULL-review-v2.json',
'pr308-owned-package-cache-independent-private-patch-review/OWNERFINAL-independent-private-owned-package-cache-two-path-patch-review.json',
'pr308-cache-current-e3c-SOURCEFULL-preexecution/OWNERFINAL-current-e4ff-managed-configured-SOURCEFULL-preexecution-proposal-v2.json',
'pr308-cache-current-e3c-independent-SOURCEFULL-preexecution-review/OWNERFINAL-independent-named-V2-current-e4ff-SOURCEFULL-preexecution-review.json'],
'V7_configuration': [
'rcc-compatibility-owned-cache-runner-successor-preparation/OWNERFINAL-current-e4ff-owned-cache-transport-v7-CONDITIONAL-preexecution-proposal.json',
'rcc-owned-cache-v7-independent-private-source-review/OWNERFINAL-independent-private-V7-current-e4ff-owned-cache-source-preparation-review.json',
'rcc-compatibility-current-e4ff-qualified-config-successor/OWNERFINAL-current-e4ff-control3-SOURCE-QUALIFIED-owned-cache-config-v4.json',
'rcc-current-e4ff-qualified-cache-config-independent-review/OWNERFINAL-independent-current-e4ff-control3-qualified-cache-config-review.json',
'rcc-compatibility-current-e4ff-qualified-config-successor/qualified-config-metadata-proof.json',
'rcc-compatibility-current-e4ff-qualified-config-successor/readonly-native-prepared-supplement.json',
'rcc-compatibility-current-e4ff-qualified-config-successor/named-qualified-constructor-scope-proof.json'],
'failed_control3_preservation': [
'root-rcc-compatibility-control3-one-actual/OWNERFINAL-root-one-control3-terminal.json',
'rcc-compatibility-control3-one-actual-independent-review/OWNERFINAL-independent-original-control3-capacity-and-cleanup-failure-STOP-review.json',
'root-failed-control3-one-byte-preservation-v4/OWNERFINAL-root-one-failed-control3-byte-preservation-terminal.json',
'root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json'],
'capacity_B25_B26': [
'root-B25-one-existing-tmp-recovery/OWNERFINAL-root-one-B25-existing-tmp-volume-terminal.json',
'capacity-recovery-batch25-independent-actual-review/OWNERFINAL-independent-one-B25-existing-tmp-original-preservation-actual-review.json',
'root-B26-one-existing-tmp-recovery/OWNERFINAL-root-one-B26-existing-tmp-volume-terminal.json',
'capacity-recovery-batch26-independent-preexecution-review/OWNERFINAL-independent-exact-seven-B26-existing-tmp-preexecution-review.json'],
'current305_PENDING': [
'pr305-current-e3c-source-LIGHT/OWNERFINAL-current584a-ordinary-e3-source-LIGHT-full-and-actual-HOLD.json',
'pr305-current584a-independent-LIGHT-preexecution-review/OWNERFINAL-independent-current584a-SOURCE-LIGHT-and-managed-full-preexecution-review.json'],
'current282_PENDING': [
'pr282-current-a54-source-LIGHT/OWNERFINAL-current1299-ordinary-a54-source-LIGHT-full-and-actual-HOLD.json',
'pr282-current1299-independent-SOURCE-LIGHT-review/OWNERFINAL-independent-current1299-SOURCE-LIGHT-review.json'],
'current313_PENDING': [
'pr313-actual300-refresh/OWNERFINAL-pr313-current-actual300-ordinary-refresh-SOURCE_LIGHT.json',
'pr313-current12dd-independent-LIGHT-and-preexecution-review/OWNERFINAL-independent-current12dd-SOURCE_LIGHT-GO-and-original4918-FULL-preexecution-HOLD.json',
'pr313-current12dd-bound-FULL-independent-preexecution-review/OWNERFINAL-independent-current12dd-root-bound-FULL-preexecution-review.json'],
'exact_canonical_deltas': [
'rcc-compatibility-owned-cache-runner-successor-preparation/canonical-current-cache-runner-proposed-delta.patch',
'pr308-cache-current-e3c-SOURCEFULL-preexecution/canonical-exact-historical-receipt-archive-alias-proposed.patch',
'pr308-owned-package-cache-independent-private-patch-review/exact-accepted-owned-package-cache-canonical-delta.patch',
'pr305-current-e3c-source-LIGHT/exact-imported-e3-canonical-guide-delta.patch',
'pr282-current-a54-source-LIGHT/exact-imported-a54-canonical-guide-delta.patch',
'pr313-current12dd-bound-FULL-independent-preexecution-review/exact-scoped-execution-review-decision-canonical-proposed.patch']}

DESCRIPTION = 'Distinct regularnonsymlink0600 root authorization with announced SHA; exactnewconfig141187/sourcee4ff/tree973/sourceFULLfb8a+LIGHT66a+FULLind16d/cacheplan ae6/currentcacheind binding/labelcontrol3/serializedtrue only'


def unsafe(value, path=()):
    hits = []
    if isinstance(value, dict):
        for key, item in value.items():
            position = '.'.join((*path, key))
            if key.lower() in {'authorization', 'access_token', 'client_secret', 'api_key',
                               'signed_url', 'stdout', 'stderr', 'raw_response', 'raw_body',
                               'environment_dump'} and isinstance(item, str) and item:
                if not (position == 'root_adoption_required.authorization' and item == DESCRIPTION):
                    hits.append(position)
            hits.extend(unsafe(item, (*path, key)))
    elif isinstance(value, list):
        for item in value:
            hits.extend(unsafe(item, path))
    return hits


rows = []
for group, names in GROUPS.items():
    for name in names:
        path = ROOT/name
        assert path.is_file(), name
        raw = path.read_bytes()
        row = bind(path)
        blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        row.update(group=group, already_in_62f4_exact_blob=blob in prior_blobs,
                   proposed_successor_relative_path='docs/program/evidence/wave11/current-engineering-successor-20261011/'+group+'--'+path.name)
        if path.suffix == '.json':
            value = json.loads(raw)
            assert not unsafe(value), (name, unsafe(value))
            row.update(content_class='SCOPED_SUMMARY_OR_BINDING_METADATA_ONLY',
                       original_declared_status=value.get('status', value.get('decision', value.get('admission', 'NO_SINGLE_STATUS_FIELD'))))
        else:
            row['content_class'] = 'EXACT_SOURCE_BACKED_CANONICAL_PATCH'
        rows.append(row)

canonical = OUT/'canonical-safe-curated-successor-proposed.patch'
raw = b'''--- a/docs/skills/repository-operations.md
+++ b/docs/skills/repository-operations.md
@@
 paths. Preserve running and skipped CI states separately from passing results.
+Curate a successor by exact body identity and declared scope, not filename or
+timestamp. Copy only reviewed safe summaries and patches; a summary's binding
+to private API, provider, process-census or log bytes does not authorize copying
+that payload. Retain failed and conditional predecessors separately from
+accepted successors, including their original identities and remaining holds.
'''
fd = os.open(canonical, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
with os.fdopen(fd, 'wb') as stream:
    stream.write(raw)
text = (REPO/'docs/skills/repository-operations.md').read_text()
patch8 = ROOT/'rcc-compatibility-owned-cache-runner-successor-preparation/canonical-current-cache-runner-proposed-delta.patch'
patch6 = ROOT/'pr308-cache-current-e3c-SOURCEFULL-preexecution/canonical-exact-historical-receipt-archive-alias-proposed.patch'
plan = {
'schema': 1, 'owner_announced_at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
'status': 'READONLY_CURATED_SUCCESSOR_HANDOFF_PLAN_ONLY_NOT_CHECKPOINT_ACCEPTANCE',
'checkpoint': {'branch': BRANCH, 'head': COMMIT, 'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
               'existing1180manifest_not_recollected': True, 'frozen_collector': collector, 'collector_rerun': 'NOT_RUN'},
'dirty_canonical_guides_preserved': dirty, 'curated_rows': rows, 'candidate_count': len(rows),
'new_exact_bodies_not_in_checkpoint': sum(not row['already_in_62f4_exact_blob'] for row in rows),
'existing_exact_bodies_no_duplicate_needed': sum(row['already_in_62f4_exact_blob'] for row in rows),
'candidate_total_bytes_only_no_payload_copied': sum(row['bytes'] for row in rows),
'selection_method': 'Explicit bounded engineering shortlist; exact SHA256/size/mode and Git body identity against62f4 complete tree. No timestamp collector or recursive binding expansion. Summaries retain original statuses, including conditional/HOLD/FAIL. Root ingestion needs independent content and staged-byte verification.',
'private_payload_exclusions': [
'Raw/full/private API responses, auth requests/headers, signed asset URLs, decoded logs/stdout/stderr',
'Provider bodies, process/cwd/FD/PID/create-time inventories and full pytest node census',
'Native binaries, ZIP/wheel/sdist/archive bytes, private archive indices, registry/cache/datadir/lease snapshots',
'Current797131B actual configuration and marker/selector bodies; private constructor/test code/logs; original frozen helper profiles',
'Any referenced private body inside safe owner/review JSON: binding metadata does not authorize recursive copying'],
'pending_frontiers': {
'native_current_control3': 'NO_CURRENT_PASS_AT_PLAN_FREEZE. Earlier failed-control3 capacity/cleanup remains FAIL; configuration141187/ind4102 does not execute it. No nextversionconfig until real current control3PASS.',
'current305': '584a sourceLIGHT/ind only; current full/freshCI/native/private/full99/release held',
'current282': '1299 sourceLIGHT/ind only; current full/freshCI/native/private/full127/release held',
'current313': '12dd sourceLIGHT+corrected FULLpreexecution; currentfull/freshCI/oldWindowsfailure held',
'capacityB26': 'Root terminal and preexecution independent included; no actualB26 independent receipt adopted here',
'Runtime221': 'HOLD; platform/content/OAuthauthority/private/cold/install/tag/publication scopes remain separate',
'sourcegraph': 'Existing54 graph retained; no graph/ledger regeneration or campaign authorized'},
'canonical_reconciliation': {
'accepted_V7_eight_lines': {'binding': bind(patch8), 'exact_anchor': 'Keep capacity thresholds and strict cleanup admission unchanged.',
'anchor_present_in_dirty_checkpoint': 'Keep capacity thresholds and strict cleanup admission unchanged.' in text,
'adaptation': 'First retain accepted source/cache blocks, then exact8line meaning alongside isolated cache contract; never blindly apply absent anchor or replace dirty guide.'},
'accepted_archive_alias_six_lines': {'binding': bind(patch6),
'long_context_present_in_dirty_checkpoint': 'proof. A historical synthetic build commit may have the accepted source tree' in text,
'adaptation': 'If long source context absent, preserve exact6line archival-preservation-versus-acceptance meaning next to evidence hash/staged-blob paragraph. No old-path recreation.'},
'conflicts': ['V7 archive sentence overlaps detailed6line archival rule; keep originalfailure scope and currentconfiguration admission distinct.',
'Dirty guides and305/282/313 accepted imports overlap producer/path-filter/cleanup lessons; compare accepted changed blocks and preserve both, never whole-file overwrite.'],
'new_scoped_privacy_delta': bind(canonical)},
'preserved_classifier_diagnostic': bind(OUT/'initial-safe-field-scanner-diagnostic.json'),
'documentation_improvement': {'canonical_file_proposed': 'docs/skills/repository-operations.md', 'exact_delta': bind(canonical),
'durable_learning_captured': 'Body/scope-based successor curation; private binding is not payload publication authority; failures/conditional proposals keep provenance.',
'evidence': '62f4 exact body comparison; unchanged0319 collector; explicit summaries/patch shortlist and raw exclusions; dirty-guide and8line/6line anchor inspection.',
'stale_or_ambiguous_guidance_removed': 'Filename, timestamp or source/configGO is not blanket publication/native acceptance; absent patch anchors require explicit reconciliation.',
'remaining_uncertainty': 'Currentnative attempt and pendingfull/CI/release scopes; root ingestion/content/staged-byte review still required.'},
'upstream_disposition': 'none',
'operations_not_performed': ['No checkpoint/index/ref/source mutation or commit/push', 'No oldcollector rerun/APIquery/download',
'No gateway/native/product import/test/full execution', 'No largepayloadcopy/extraction or nextversionconfiguration generation']}
assert original_status == git('status', '--porcelain')
for name, row in dirty.items():
    assert bind(REPO/name) == row
assert bind(ROOT/'checkpoint-current-engineering-after299-0938.py') == collector
path = OUT/'OWNERFINAL-safe-curated-successor-handoff-plan-after62f4.json'
fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o400)
with os.fdopen(fd, 'w') as stream:
    json.dump(plan, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps(bind(path), sort_keys=True))
print(json.dumps({key: plan[key] for key in ('candidate_count', 'new_exact_bodies_not_in_checkpoint', 'existing_exact_bodies_no_duplicate_needed', 'candidate_total_bytes_only_no_payload_copied')}))
print(json.dumps(bind(canonical), sort_keys=True))
