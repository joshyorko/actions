"""Construct proposals from immutable bytes; never edits a checkout or launches RCC."""
import ast
import difflib
import os
from pathlib import Path

BASE = Path(__file__).parent
OLD = Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
PUBLIC = Path('/workspace/engineering/pr308/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py')

def write(name, raw):
    fd = os.open(BASE/name, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)

old = (OLD/'owned_cache_policy_v1.py').read_text()
new = old.replace("_owned_directory(root / \"actions-home\")", "_owned_rcc_home(root / \"actions-home\")")
assert new != old and old.count('_owned_directory(root / "actions-home")') == 2
point = new.index('\ndef create_cache_marker(')
helper = '''\ndef _owned_rcc_home(path):
    """Only the native-managed home may use0750, with current UID and GID."""
    meta = path.lstat()
    need(stat.S_ISDIR(meta.st_mode) and not path.is_symlink()
         and path.resolve(strict=True) == path
         and stat.S_IMODE(meta.st_mode) in (0o700, 0o750)
         and meta.st_uid == os.getuid() and meta.st_gid == os.getgid(),
         "CACHE_NATIVE_HOME_MODE_OWNER_GROUP")

'''
new = new[:point]+helper+new[point:]
write('owned_cache_policy_v2.py', new.encode())
records = (OLD/'fixture_records_v2.py').read_text()
changed = records.replace('Data-only admission for the frozen b614 two-case interface.',
                          'Data-only admission for the independently source-bound two-case interface.')
changed = changed.replace("value['source_commit'] == 'b614864ba9da55c13662894b6ef3c8515d9fdb25'", "value['source_commit'] == expected['source']['commit']")
changed = changed.replace("value['source_tree'] == '6fa4f5c1e9837a0d893868255575b355b3977fae'", "value['source_tree'] == expected['source']['tree']")
assert records != changed
write('fixture_records_v3.py', changed.encode())
public = PUBLIC.read_text()
needle = '''    assert (
        stat.S_IMODE(client.stat().st_mode) == 0o700
        and client.stat().st_uid == os.getuid()
    ), "PACKAGE_CACHE_CLIENT_MODE_OWNER"'''
replacement = '''    client_metadata = client.stat()
    assert (
        stat.S_IMODE(client_metadata.st_mode) in (0o700, 0o750)
        and client_metadata.st_uid == os.getuid()
        and client_metadata.st_gid == os.getgid()
    ), "PACKAGE_CACHE_CLIENT_MODE_OWNER"'''
assert public.count(needle) == 1
proposed = public.replace(needle, replacement)
newtests = '''

@pytest.mark.parametrize("mode", [0o700, 0o750])
def test_owned_rcc_package_cache_native_home_mode_preserves_cold_and_warm(
    owned_rcc_package_cache_control, owned_rcc_package_cache_mount_spy, mode
):
    root, case, managed, value, configure, publication, published = (
        owned_rcc_package_cache_control
    )
    client = root / "actions-home"
    client.chmod(mode)
    calls = owned_rcc_package_cache_mount_spy()
    result = _prepare_owned_rcc_test_package_cache(case, "v18.19.3", value["binary_sha256"])
    assert result["cold_first_publication"] is True
    assert calls == []
    assert stat.S_IMODE(client.stat().st_mode) == mode
    published()
    result = _prepare_owned_rcc_test_package_cache(
        case, "v18.19.3", value["binary_sha256"], managed_home=managed
    )
    assert result["cold_first_publication"] is False
    assert calls == [(managed / "pkgs", (client / "pkgs",), {"target_is_directory": True})]
    assert stat.S_IMODE(client.stat().st_mode) == mode
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE((client / "pkgs").stat().st_mode) == 0o700
    assert stat.S_IMODE((root / "rcc-package-cache-owner.json").stat().st_mode) == 0o600


@pytest.mark.parametrize("mode", [0o701, 0o710, 0o740, 0o751, 0o760, 0o770, 0o777])
def test_owned_rcc_package_cache_native_home_rejects_other_modes_before_mount(
    owned_rcc_package_cache_control, owned_rcc_package_cache_mount_spy, mode
):
    root, case, managed, value, configure, publication, published = (
        owned_rcc_package_cache_control
    )
    published()
    client = root / "actions-home"
    client.chmod(mode)
    calls = owned_rcc_package_cache_mount_spy()
    with pytest.raises(AssertionError, match="PACKAGE_CACHE_CLIENT_MODE_OWNER"):
        _prepare_owned_rcc_test_package_cache(
            case, "v18.19.3", value["binary_sha256"], managed_home=managed
        )
    assert calls == []
    assert not (managed / "pkgs").exists()
    assert stat.S_IMODE(client.stat().st_mode) == mode


@pytest.mark.parametrize("mode", [0o700, 0o750])
@pytest.mark.parametrize("identity", ["uid", "gid"])
def test_owned_rcc_package_cache_native_home_rejects_foreign_owner_or_group(
    owned_rcc_package_cache_control, owned_rcc_package_cache_mount_spy,
    monkeypatch, mode, identity
):
    root, case, managed, value, configure, publication, published = (
        owned_rcc_package_cache_control
    )
    published()
    client = root / "actions-home"
    client.chmod(mode)
    original_stat = Path.stat
    def controlled_stat(path, *args, **kwargs):
        metadata = original_stat(path, *args, **kwargs)
        if path == client:
            fields = list(metadata)
            fields[4 if identity == "uid" else 5] += 1
            return os.stat_result(fields)
        return metadata
    monkeypatch.setattr(Path, "stat", controlled_stat)
    calls = owned_rcc_package_cache_mount_spy()
    with pytest.raises(AssertionError, match="PACKAGE_CACHE_CLIENT_MODE_OWNER"):
        _prepare_owned_rcc_test_package_cache(
            case, "v18.19.3", value["binary_sha256"], managed_home=managed
        )
    assert calls == []
    assert not (managed / "pkgs").exists()
    assert stat.S_IMODE(client.stat().st_mode) == mode
'''
proposed += newtests
write('proposed_test_source_staging_rcc_consumer.py', proposed.encode())
patch = ''.join(difflib.unified_diff(public.splitlines(True), proposed.splitlines(True),
    fromfile='a/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py',
    tofile='b/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'))
write('exact-current-e4ff-native-managed-home-mode-fixture-only-proposed.patch', patch.encode())
print('PRIVATE PROPOSALS ONLY; public checkout unchanged; transport/config/root state unchanged')
