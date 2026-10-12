"""Community bundles must build offline from the owned, secret-free input pair."""

import ast
import hashlib
import importlib.util
from pathlib import Path

import pytest
import yaml

SPEC = importlib.util.spec_from_file_location(
    "community_oauth2_builder",
    Path(__file__).resolve().parents[2] / "scripts/build_oauth2_config.py",
)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def test_owned_pair_builds_without_credentials_or_network(tmp_path, monkeypatch):
    # The previous builder invokes gh even with no available hosted registration.
    def no_network(*args, **kwargs):
        pytest.fail("OAuth packaging must not acquire vendor configuration")

    import subprocess

    monkeypatch.setattr(subprocess, "run", no_network)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    destination = tmp_path / "_oauth2_config.py"
    builder.build_oauth2_config(destination)
    namespace = {}
    exec(
        compile(ast.parse(destination.read_bytes()), str(destination), "exec"),
        namespace,
    )
    for key, filename in builder.INPUTS:
        body = (builder.INPUT_ROOT / filename).read_bytes()
        assert namespace["FILE_CONTENTS"][key].encode() == body
        assert namespace["INPUT_SHA256"][filename] == hashlib.sha256(body).hexdigest()
        assert yaml.safe_load(body) == {
            "formatVersion": "1.0.0",
            "oauth2Config": {"providers": {}},
        }


@pytest.mark.parametrize(
    "body",
    [
        b"formatVersion: '1.0.0'\noauth2Config: {providers: {}}\noauth2Config: {providers: {}}",
        b"formatVersion: '1.0.0'\noauth2Config: {providers: {google: {clientId: private, clientSecret: secret}}}",
        b"formatVersion: '2.0.0'\noauth2Config: {providers: {}}",
    ],
)
def test_unapproved_owned_input_preserves_previous_module(tmp_path, monkeypatch, body):
    monkeypatch.setattr(builder, "INPUT_ROOT", tmp_path, raising=False)
    for _, filename in builder.INPUTS:
        (tmp_path / filename).write_bytes(body)
    destination = tmp_path / "_oauth2_config.py"
    destination.write_bytes(b"previous module\n")
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, body, b""),
    )
    with pytest.raises(builder.OAuth2ConfigBuildError):
        builder.build_oauth2_config(destination)
    assert destination.read_bytes() == b"previous module\n"
