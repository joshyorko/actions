

@pytest.fixture
def owned_rcc_package_cache_control(monkeypatch):
    """Own only a tiny synthetic Linux task namespace; never run RCC."""
    import tempfile

    if sys.platform != "linux":
        pytest.skip("owned /dev/shm package-cache controls require Linux")
    with tempfile.TemporaryDirectory(
        prefix="actions-rcc-compatibility-actual-control3-unit-", dir="/dev/shm"
    ) as directory:
        root = Path(directory)
        root.chmod(0o700)
        client = root / "actions-home"
        client.mkdir(mode=0o700)
        case = root / "pytest" / "synthetic-stage"
        case.mkdir(parents=True, mode=0o700)
        managed = case / "managed-home"
        managed.mkdir(mode=0o700)
        value = {
            "schema": 1, "runtime_source_sha": "b" * 40,
            "runtime_source_tree": "c" * 40, "label": "control3",
            "binary_sha256": "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428",
            "state_root": str(root), "package_cache_root": str(client / "pkgs"),
        }
        def configure():
            marker = root / "rcc-package-cache-owner.json"
            raw = json.dumps({key: item for key, item in value.items() if key != "state_marker_sha256"}, sort_keys=True).encode()
            marker.write_bytes(raw)
            marker.chmod(0o600)
            value["state_marker_sha256"] = hashlib.sha256(raw).hexdigest()
            monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG", json.dumps(value))
        configure()
        for key, item in {
            "RCC_ROLLBACK_CANDIDATE_SHA": "b" * 40,
            "RCC_ROLLBACK_CANDIDATE_TREE": "c" * 40,
            "ACTIONS_HOME": str(client), "ROBOCORP_HOME": str(client),
            "ACTIONS_RUNTIME_PUBLISHED_DETAILS_RECEIPT": str(root / "publication.json"),
        }.items():
            monkeypatch.setenv(key, item)
        publication = {"schema_version": 1, "status": "PASS",
                       "source": {"commit": "b" * 40, "tree": "c" * 40},
                       "rcc": {"version": "v18.19.3", "sha256": value["binary_sha256"]},
                       "publication": {"invocation_count": 1}}
        def published():
            cache = client / "pkgs"
            cache.mkdir(mode=0o700, exist_ok=True)
            (cache / "synthetic-repodata.json").write_bytes(b"synthetic-package-index")
            receipt = root / "publication.json"
            receipt.write_text(json.dumps(publication))
            receipt.chmod(0o600)
        yield root, case, managed, value, configure, publication, published


def test_owned_rcc_package_cache_preserves_cold_first_and_shared_download_only(
    owned_rcc_package_cache_control,
):
    root, case, managed, value, configure, publication, published = owned_rcc_package_cache_control
    result = _prepare_owned_rcc_test_package_cache(case, "v18.19.3", value["binary_sha256"])
    assert result == {"label": "control3", "shared_only": "pkgs", "cold_first_publication": True}
    assert not any((root / "actions-home" / "pkgs").iterdir())
    published()
    _prepare_owned_rcc_test_package_cache(case, "v18.19.3", value["binary_sha256"], managed_home=managed)
    shared = root / "actions-home" / "pkgs"
    assert (managed / "pkgs").is_symlink() and (managed / "pkgs").resolve() == shared
    assert (managed / "pkgs" / "synthetic-repodata.json").stat().st_ino == (shared / "synthetic-repodata.json").stat().st_ino
    assert not any((managed / name).exists() for name in ("holotree", "artifacts", "provider"))
    assert (shared / "synthetic-repodata.json").read_bytes() == b"synthetic-package-index"


@pytest.mark.parametrize("poison", [
    "unknown_key", "schema_bool", "wrong_binary", "wrong_measured_version",
    "cross_version", "source", "tree", "marker_hash", "marker_mode",
    "marker_symlink", "root_mode", "client_symlink", "target_mode",
    "target_symlink", "target_escape", "case_escape", "managed_symlink",
    "existing_mount", "publication_status", "publication_source",
    "publication_binary", "publication_count", "publication_bool_count",
    "publication_missing", "publication_mode", "publication_symlink",
    "client_env", "empty_cache", "duplicate_config",
])
def test_owned_rcc_package_cache_rejects_poison_before_mount(
    owned_rcc_package_cache_control, monkeypatch, poison,
):
    root, case, managed, value, configure, publication, published = owned_rcc_package_cache_control
    published()
    cache = root / "actions-home" / "pkgs"
    version = "v18.19.3"
    digest = value["binary_sha256"]
    if poison == "unknown_key": value["unknown"] = True
    elif poison == "schema_bool": value["schema"] = True
    elif poison == "wrong_binary": value["binary_sha256"] = "d" * 64
    elif poison == "wrong_measured_version": version = "v18.19.5"
    elif poison == "cross_version": value["label"] = "released5"
    elif poison == "source": value["runtime_source_sha"] = "a" * 40
    elif poison == "tree": value["runtime_source_tree"] = "a" * 40
    elif poison == "target_escape": value["package_cache_root"] = str(root / "other-cache")
    elif poison == "case_escape": case = root / "not-a-pytest-case";case.mkdir(mode=0o700)
    elif poison == "publication_status": publication["status"] = "FAIL"
    elif poison == "publication_source": publication["source"]["commit"] = "a" * 40
    elif poison == "publication_binary": publication["rcc"]["sha256"] = "d" * 64
    elif poison == "publication_count": publication["publication"]["invocation_count"] = 2
    elif poison == "publication_bool_count": publication["publication"]["invocation_count"] = True
    configure()
    receipt = root / "publication.json"
    receipt.write_text(json.dumps(publication))
    if poison == "marker_hash": value["state_marker_sha256"] = "e" * 64;monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG",json.dumps(value))
    elif poison == "marker_mode": (root / "rcc-package-cache-owner.json").chmod(0o644)
    elif poison == "marker_symlink": marker=root / "rcc-package-cache-owner.json";other=root / "owned-other-marker";marker.rename(other);marker.symlink_to(other)
    elif poison == "root_mode": root.chmod(0o755)
    elif poison == "client_symlink": client=root / "actions-home";other=root / "other-client";client.rename(other);client.symlink_to(other, target_is_directory=True)
    elif poison == "target_mode": cache.chmod(0o755)
    elif poison == "target_symlink": other=root / "other-cache";cache.rename(other);cache.symlink_to(other,target_is_directory=True)
    elif poison == "managed_symlink": other=case / "other-home";managed.rename(other);managed.symlink_to(other,target_is_directory=True)
    elif poison == "existing_mount": (managed / "pkgs").symlink_to(cache,target_is_directory=True)
    elif poison == "publication_missing": receipt.unlink()
    elif poison == "publication_mode": receipt.chmod(0o644)
    elif poison == "publication_symlink": other=root / "other-publication";receipt.rename(other);receipt.symlink_to(other)
    elif poison == "client_env": monkeypatch.setenv("ACTIONS_HOME",str(root / "wrong-client"))
    elif poison == "empty_cache": (cache / "synthetic-repodata.json").unlink()
    elif poison == "duplicate_config": monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG",json.dumps(value)[:-1]+',"schema":1}')
    preexisting = (managed / "pkgs").is_symlink()
    with pytest.raises((AssertionError, ValueError)):
        _prepare_owned_rcc_test_package_cache(case, version, digest, managed_home=managed)
    assert (managed / "pkgs").is_symlink() is preexisting


def test_owned_rcc_package_cache_rejects_prewarmed_first_publication(owned_rcc_package_cache_control):
    root, case, managed, value, configure, publication, published = owned_rcc_package_cache_control
    published()
    with pytest.raises(AssertionError, match="COLD_FIRST_PUBLICATION"):
        _prepare_owned_rcc_test_package_cache(case, "v18.19.3", value["binary_sha256"])
    assert not (managed / "pkgs").exists()
