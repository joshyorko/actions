"""Core must select one native truststore implementation without namespace overlap."""

import datetime
import ipaddress
import os
import socket
import ssl
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_core_requires_official_native_truststore():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = project["tool"]["poetry"]["dependencies"]
    assert "robocorp-truststore" not in dependencies
    assert dependencies["truststore"] == ">=0.10,<1.0"


def test_core_lock_has_no_overlapping_truststore_distribution():
    packages = tomllib.loads((ROOT / "poetry.lock").read_text())["package"]
    assert not any(p["name"] == "robocorp-truststore" for p in packages)
    official = [p for p in packages if p["name"] == "truststore"]
    assert len(official) == 1
    assert "main" in official[0]["groups"]


@pytest.fixture
def isolated_python():
    configured = os.environ.get("ACTIONS_TRUSTSTORE_TEST_PYTHON")
    if not configured:
        pytest.skip("set ACTIONS_TRUSTSTORE_TEST_PYTHON to a clean owned HTTP consumer")
    executable = Path(configured)
    assert executable.is_absolute() and executable.is_file()
    return str(executable)


def _run(executable, script, *arguments):
    return subprocess.run(
        [executable, "-I", "-B", "-c", script, *map(str, arguments)],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )


def test_official_installed_bytes_and_http_context(isolated_python):
    _run(
        isolated_python,
        """
import base64, hashlib, importlib.metadata as md, ssl
original = ssl.SSLContext
import actions_http, truststore
try:
    md.distribution('robocorp-truststore')
except md.PackageNotFoundError:
    pass
else:
    raise AssertionError('overlapping truststore distribution installed')
distribution = md.distribution('truststore')
assert truststore.__version__ == distribution.version
assert tuple(map(int, distribution.version.split('.')[:2])) >= (0, 10)
for member in distribution.files:
    if str(member).startswith('truststore/') and str(member).endswith('.py'):
        assert member.hash.mode == 'sha256'
        actual = base64.urlsafe_b64encode(hashlib.sha256(member.locate().read_bytes()).digest()).decode().rstrip('=')
        assert actual == member.hash.value, str(member)
context = actions_http.build_ssl_context()
assert isinstance(context, truststore.SSLContext)
assert context.verify_mode == ssl.CERT_REQUIRED
assert context.check_hostname is True
assert ssl.SSLContext is original, 'HTTP helper must not globally inject TLS policy'
""",
    )


@pytest.mark.skipif(sys.platform != "linux", reason="Linux native OpenSSL CA store")
def test_official_context_loads_native_ca_store(isolated_python):
    _run(
        isolated_python,
        """
import ssl
import actions_http
from truststore._openssl import _configure_context
context = actions_http.build_ssl_context()
expected = set(ssl.create_default_context().get_ca_certs(binary_form=True))
assert expected, 'native default CA store is empty'
with _configure_context(context._ctx):
    actual = set(context._ctx.get_ca_certs(binary_form=True))
assert expected <= actual, 'native default CA roots were not preserved'
assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
""",
    )


@pytest.fixture
def certificate(tmp_path):
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Owned test CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    ca_path, cert_path, key_path = [
        tmp_path / n for n in ("ca.pem", "server.pem", "key.pem")
    ]
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_path.write_bytes(server.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    return ca_path, cert_path, key_path


@pytest.mark.parametrize("case", ["trusted", "untrusted", "wrong-host"])
def test_owned_http_tls_verification(isolated_python, certificate, case):
    ca_path, cert_path, key_path = certificate
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert_path, key_path)
    errors = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(10)
        port = listener.getsockname()[1]

        def serve():
            try:
                connection, _ = listener.accept()
                with connection:
                    with server_context.wrap_socket(
                        connection, server_side=True
                    ) as stream:
                        stream.sendall(b"owned TLS probe")
            except ssl.SSLError:
                if case == "trusted":
                    errors.append("trusted handshake rejected")
            except Exception as exc:
                errors.append(type(exc).__name__)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            _run(
                isolated_python,
                """
import socket, ssl, sys
import actions_http
case, ca_path, port = sys.argv[1:]
context = actions_http.build_ssl_context()
assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
if case != 'untrusted':
    context.load_verify_locations(cafile=ca_path)
hostname = 'different.invalid' if case == 'wrong-host' else 'localhost'
try:
    with socket.create_connection(('127.0.0.1', int(port)), timeout=5) as connection:
        with context.wrap_socket(connection, server_hostname=hostname) as stream:
            assert stream.recv(64) == b'owned TLS probe'
except ssl.SSLCertVerificationError as exc:
    assert case != 'trusted', str(exc)
    if case == 'wrong-host':
        assert 'hostname' in exc.verify_message.lower(), str(exc)
else:
    assert case == 'trusted', 'untrusted/hostname-invalid certificate accepted'
""",
                case,
                ca_path,
                port,
            )
        finally:
            thread.join(timeout=11)
        assert not thread.is_alive(), "owned TLS server failed to stop"
        assert not errors, errors
