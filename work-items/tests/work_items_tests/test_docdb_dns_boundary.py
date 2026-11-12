"""Reject vulnerable SRV DNS resolution before creating a Mongo client."""

import sys
from types import ModuleType

import pytest

from actions.work_items._adapters import _docdb


@pytest.mark.parametrize("uri", ["mongodb+srv://example.invalid", "MONGODB+SRV://example.invalid"])
def test_unpatched_srv_dns_is_rejected_before_client_or_files(monkeypatch, tmp_path, uri):
    monkeypatch.setattr(_docdb, "_pymongo_available", True)
    dns = ModuleType("dns")
    version = ModuleType("dns.version")
    version.hexversion = 0x020800F0
    dns.version = version
    monkeypatch.setitem(sys.modules, "dns", dns)
    monkeypatch.setitem(sys.modules, "dns.version", version)
    monkeypatch.setenv("DOCDB_URI", uri)
    monkeypatch.setenv("DOCDB_DATABASE", "synthetic")
    files = tmp_path / "files"
    monkeypatch.setenv("RC_WORKITEM_FILES_DIR", str(files))

    def forbidden_client(*args, **kwargs):
        pytest.fail("vulnerable SRV URI reached MongoClient")

    monkeypatch.setattr(_docdb, "MongoClient", forbidden_client)
    with pytest.raises(ImportError, match="dnspython>=2.9.0"):
        _docdb.DocumentDBAdapter()
    assert not files.exists()


@pytest.mark.parametrize(
    "uri,hexversion",
    [("mongodb://localhost:27017", 0x020800F0), ("mongodb+srv://example.invalid", 0x020900F0)],
)
def test_standard_uri_or_patched_dns_reaches_client(monkeypatch, tmp_path, uri, hexversion):
    monkeypatch.setattr(_docdb, "_pymongo_available", True)
    dns = ModuleType("dns")
    version = ModuleType("dns.version")
    version.hexversion = hexversion
    dns.version = version
    monkeypatch.setitem(sys.modules, "dns", dns)
    monkeypatch.setitem(sys.modules, "dns.version", version)
    monkeypatch.setenv("DOCDB_URI", uri)
    monkeypatch.setenv("DOCDB_DATABASE", "synthetic")
    monkeypatch.setenv("RC_WORKITEM_FILES_DIR", str(tmp_path / "files"))

    class ClientReached(BaseException):
        pass

    def client(*args, **kwargs):
        raise ClientReached

    monkeypatch.setattr(_docdb, "MongoClient", client)
    with pytest.raises(ClientReached):
        _docdb.DocumentDBAdapter()
