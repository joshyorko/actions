import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path('/workspace/engineering/pr306')
OUT = Path('/workspace/engineering/pr306-v2-precision-successor')
ORIGINAL = Path('/workspace/engineering/pr306-windows-v2-source/implementation-V2-frozen-source-checkpoint.json')
REVIEW = Path('/workspace/engineering/pr306-V2-independent-source-review/independent-original-cf6352-source-review-HOLD.json')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def record(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


before = json.loads((OUT / 'before-full-source-checkpoint.json').read_text())
assert before['head'] == 'cf6352e253c70095c8e09904e730fc18a42f9a65'
assert git('rev-parse', 'HEAD^') == before['head']
assert git('status', '--porcelain') == ''
assert record(ORIGINAL)['sha256'] == 'f542bc04747ea8fd8741c309f26de523ee347c8aee82320931f44accf9681be0'
assert record(REVIEW)['sha256'] == '24a0d2c1bf0e0cfa18a141dbbfb0952e0fdf297ff7b93be25c58ea681a08cba7'
original = json.loads(ORIGINAL.read_text())
for item in original['evidence_files'].values():
    assert record(Path(item['path']))['sha256'] == item['sha256'], item['path']
after = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in before['files']}
assert after == before['files']
full = (OUT / 'current-full-configured-source.log').read_text()
assert '"actual main robot run" was SUCCESS' in full
summary = re.findall(r'(\d+) passed, (\d+) skipped, (\d+) warnings in ([\d.]+)s', full)
assert len(summary) == 1, summary
passed, skipped, warnings, seconds = summary[0]
scope = json.loads((OUT / 'precision-successor-scope-proof.json').read_text())
assert scope['all_other_leaf_bodies_modes_exact'] == 1406
assert scope['original58controls_and_helper_function_ASTs_exact'] is True
target = OUT / 'precision-successor-frozen-source-checkpoint.json'
assert not target.exists()
files = [record(p) for p in sorted(OUT.iterdir()) if p.is_file() and p != target]
receipt = {
    'status': 'FROZEN_SOURCE_AWAITING_INDEPENDENT_SUCCESSOR_REVIEW_NO_PUSH_OR_ACTUAL_GO',
    'branch': git('branch', '--show-current'),
    'head': git('rev-parse', 'HEAD'),
    'tree': git('rev-parse', 'HEAD^{tree}'),
    'ordered_parents': git('show', '-s', '--format=%P', 'HEAD').split(),
    'working_tree_clean': True,
    'ordinary_merge_and_all_history_preserved': True,
    'original_held_subject': record(ORIGINAL),
    'original_independent_HOLD': record(REVIEW),
    'unchanged_original_evidence_files': len(original['evidence_files']),
    'source_after_full_equals_before': after,
    'scope_proof': scope,
    'validation': {
        'precision_RED_on_original_cf6352': '9 failed, 5 passed, 58 deselected; exact post/equal boundary false positives reproduced',
        'current_observer_controls': '72 passed; original58 plus14 fractional/equal/post/unknown cases',
        'Doctor': 'PASS',
        'Bootstrap': 'REUSE ONLY: 30 actual unique gateway/build/manifest/lock inputs and five own package origins/prefixes verified; no install',
        'ToolkitTest': '69 passed; developer Ruff PASS',
        'scoped_source': '94 passed',
        'complete_DB_source': '61 passed; 12 PostgreSQL skips retained, no actual PostgreSQL run',
        'configured_static': '301 files formatted/Isort/Ruff PASS; Mypy337 PASS; optional Markdown lint unavailable',
        'generation': '8 generated workflows plus dependabot roundtrip unchanged;29 yml files scope, separately complete34GitHub leaves/30 yaml+yml bytes/modes unchanged',
        'full_configured_source': {'passed': int(passed), 'skipped': int(skipped), 'warnings': int(warnings), 'seconds': float(seconds), 'workers': 2, 'RCC': 'SUCCESS', 'outer_seconds': 600, 'kill_grace_seconds': 10},
    },
    'native_92498': 'UNQUALIFIED for retained DBguard input delta; no build/rerun/artifact relabel; all267 other producer and five selected inputs unchanged from original proof',
    'actual_native_provider_browser_or_PostgreSQL_execution': 'NONE',
    'Documentation_improvement': {
        'Canonical_file_changed': 'docs/skills/repository-operations.md',
        'Durable_learning': 'Classify delivered readiness using private unrounded monotonic instants; round only display. Strict equality is not before a conservative lower bound; pre-bound delivery alone does not prove actual readiness completion.',
        'Evidence': ['independent24a0 precision finding', '9 failing original-boundary controls', '72 passing current controls', 'exact-precision-canonical-delta.patch'],
        'Independent_proposal_disposition': 'Adapted e2f885f8 proposal with strict equality and conservative-bound scope; original36-line V2 lesson retained',
        'Stale_guidance_removed': 'Removed ambiguity allowing displayed rounded offsets to classify deadlines; no original operational lesson removed',
        'Remaining_uncertainty': 'No new native Windows execution; readiness Future, native log emission and RCC internal forwarding remain unavailable; positive lower-bound comparison is narrower than actual deadline success',
    },
    'Upstream_disposition': 'none; no established RCC upstream defect and no mutation target authorized',
    'remaining_HOLDs': ['independent successor review and root normal push', 'fresh exact-head hosted CI', 'actual Windows V2 observations not yet executed', 'original broader DB/private/native/release gates unchanged'],
    'before_full_available_bytes': before['available_bytes'],
    'current_available_bytes': shutil.disk_usage(ROOT).free,
    'evidence_files': files,
}
target.write_text(json.dumps(receipt, indent=2) + '\n')
for path in OUT.iterdir():
    if path.is_file():
        path.chmod(0o400 if path.suffix == '.log' else 0o444)
print(json.dumps({'head': receipt['head'], 'tree': receipt['tree'], 'parents': receipt['ordered_parents'], 'receipt': record(target), 'full': receipt['validation']['full_configured_source']}, indent=2))
