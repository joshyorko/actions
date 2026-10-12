

def _prepare_owned_rcc_test_package_cache(
    tmp_path: Path, rcc_version: str, rcc_sha256: str, *, managed_home=None
):
    """Share only serial-case package downloads within one admitted task root."""
    import json

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("PACKAGE_CACHE_DUPLICATE_KEY")
            result[key] = value
        return result

    def parse(raw):
        try:
            value = json.loads(raw, object_pairs_hook=object_pairs)
        except json.JSONDecodeError:
            raise ValueError("PACKAGE_CACHE_INVALID_JSON") from None
        assert isinstance(value, dict), "PACKAGE_CACHE_OBJECT"
        return value

    value = parse(os.environ["ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG"])
    keys = {
        "schema", "runtime_source_sha", "runtime_source_tree", "label",
        "binary_sha256", "state_root", "package_cache_root", "state_marker_sha256",
    }
    assert set(value) == keys, "PACKAGE_CACHE_CONFIG_KEYS"
    assert type(value["schema"]) is int and value["schema"] == 1, "PACKAGE_CACHE_SCHEMA"
    expected = {
        "control3": ("v18.19.3", "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"),
        "released5": ("v18.19.5", "1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e"),
        "candidate7276": ("v18.19.6", "be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e"),
    }
    assert isinstance(value["label"], str) and value["label"] in expected, "PACKAGE_CACHE_LABEL"
    assert (rcc_version, rcc_sha256) == expected[value["label"]], "PACKAGE_CACHE_APPROVED_BINARY"
    assert value["binary_sha256"] == rcc_sha256, "PACKAGE_CACHE_BINARY_IDENTITY"
    for key, env_key in (
        ("runtime_source_sha", "RCC_ROLLBACK_CANDIDATE_SHA"),
        ("runtime_source_tree", "RCC_ROLLBACK_CANDIDATE_TREE"),
    ):
        text = value[key]
        assert isinstance(text, str) and len(text) == 40 and all(
            character in "0123456789abcdef" for character in text
        ), "PACKAGE_CACHE_SOURCE_IDENTITY"
        assert text == os.environ.get(env_key), "PACKAGE_CACHE_SOURCE_BINDING"
    for key in ("state_root", "package_cache_root", "state_marker_sha256"):
        assert isinstance(value[key], str), "PACKAGE_CACHE_FIELD_TYPE"
    root = Path(value["state_root"])
    assert root.is_absolute() and root.parent == Path("/dev/shm"), "PACKAGE_CACHE_STATE_LOCATION"
    assert root.name.startswith(
        "actions-rcc-compatibility-actual-" + value["label"] + "-"
    ), "PACKAGE_CACHE_CROSS_VERSION"
    assert not root.is_symlink() and root.resolve(strict=True) == root, "PACKAGE_CACHE_ROOT_LINK"
    assert stat.S_IMODE(root.stat().st_mode) == 0o700 and root.stat().st_uid == os.getuid(), "PACKAGE_CACHE_ROOT_MODE_OWNER"
    marker = root / "rcc-package-cache-owner.json"
    assert not marker.is_symlink() and marker.is_file(), "PACKAGE_CACHE_MARKER_FILE"
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600 and marker.stat().st_uid == os.getuid(), "PACKAGE_CACHE_MARKER_MODE_OWNER"
    raw_marker = marker.read_bytes()
    assert hashlib.sha256(raw_marker).hexdigest() == value["state_marker_sha256"], "PACKAGE_CACHE_MARKER_HASH"
    assert parse(raw_marker) == {key: value[key] for key in keys if key != "state_marker_sha256"}, "PACKAGE_CACHE_MARKER_IDENTITY"
    case = tmp_path.resolve(strict=True)
    assert not tmp_path.is_symlink() and case.is_relative_to(root / "pytest"), "PACKAGE_CACHE_CASE_CONTAINMENT"
    cache = Path(value["package_cache_root"])
    assert cache == root / "actions-home" / "pkgs", "PACKAGE_CACHE_TARGET_IDENTITY"
    client = cache.parent
    assert client.is_dir() and not client.is_symlink() and client.resolve() == client, "PACKAGE_CACHE_CLIENT_LINK"
    assert stat.S_IMODE(client.stat().st_mode) == 0o700 and client.stat().st_uid == os.getuid(), "PACKAGE_CACHE_CLIENT_MODE_OWNER"
    assert all(Path(os.environ.get(key, "")).resolve() == client for key in ("ACTIONS_HOME", "ROBOCORP_HOME")), "PACKAGE_CACHE_CLIENT_ENV"
    if cache.exists() or cache.is_symlink():
        assert cache.is_dir() and not cache.is_symlink(), "PACKAGE_CACHE_TARGET_LINK"
        assert stat.S_IMODE(cache.stat().st_mode) == 0o700 and cache.stat().st_uid == os.getuid(), "PACKAGE_CACHE_TARGET_MODE_OWNER"
    if managed_home is None:
        assert not cache.exists() or not any(cache.iterdir()), "PACKAGE_CACHE_COLD_FIRST_PUBLICATION"
        if not cache.exists():
            cache.mkdir(mode=0o700)
    else:
        assert cache.is_dir() and any(cache.iterdir()), "PACKAGE_CACHE_FIRST_PUBLICATION_REQUIRED"
        receipt = Path(os.environ.get("ACTIONS_RUNTIME_PUBLISHED_DETAILS_RECEIPT", ""))
        assert receipt == root / "publication.json" and receipt.is_file() and not receipt.is_symlink(), "PACKAGE_CACHE_PUBLICATION_PATH"
        assert stat.S_IMODE(receipt.stat().st_mode) == 0o600 and receipt.stat().st_uid == os.getuid(), "PACKAGE_CACHE_PUBLICATION_MODE_OWNER"
        publication = parse(receipt.read_bytes())
        assert publication.get("status") == "PASS" and publication.get("schema_version") == 1 and type(publication.get("schema_version")) is int, "PACKAGE_CACHE_PUBLICATION_STATUS"
        assert publication.get("source") == {"commit": value["runtime_source_sha"], "tree": value["runtime_source_tree"]}, "PACKAGE_CACHE_PUBLICATION_SOURCE"
        assert publication.get("rcc") == {"version": rcc_version, "sha256": rcc_sha256}, "PACKAGE_CACHE_PUBLICATION_BINARY"
        assert isinstance(publication.get("publication"), dict) and type(publication["publication"].get("invocation_count")) is int and publication["publication"]["invocation_count"] == 1, "PACKAGE_CACHE_PUBLICATION_INVOCATION"
        assert managed_home == tmp_path / "managed-home" and managed_home.is_dir() and not managed_home.is_symlink(), "PACKAGE_CACHE_MANAGED_HOME_IDENTITY"
        assert stat.S_IMODE(managed_home.stat().st_mode) == 0o700 and managed_home.stat().st_uid == os.getuid(), "PACKAGE_CACHE_MANAGED_HOME_MODE_OWNER"
        link = managed_home / "pkgs"
        assert not link.exists() and not link.is_symlink(), "PACKAGE_CACHE_EXISTING_MOUNT"
        link.symlink_to(cache, target_is_directory=True)
        assert link.resolve(strict=True) == cache and link.is_symlink(), "PACKAGE_CACHE_MOUNT_CONTAINMENT"
    return {"label": value["label"], "shared_only": "pkgs", "cold_first_publication": managed_home is None}
