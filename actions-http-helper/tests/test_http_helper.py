class FakeResponse:
    def __init__(self, data: bytes, headers: dict[str, str], status: int = 200):
        self.data = data
        self.headers = headers
        self.status = status
        self.reason = "OK"

    def read(self, chunk_size: int) -> bytes:
        data, self.data = self.data, b""
        return data


class FakePool:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.requests: list[tuple[str, str, dict[str, object]]] = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.response


def test_get_wraps_fake_urllib3_response(monkeypatch):
    import actions_http

    pool = FakePool(
        FakeResponse(b"hello", {"content-type": "text/plain; charset=utf-8"})
    )
    monkeypatch.setattr(actions_http, "_get_connection_manager", lambda: pool)

    response = actions_http.get("https://example.test/resource")

    assert response.status == 200
    assert response.status_code == 200
    assert response.text == "hello"
    response.raise_for_status()
    assert pool.requests[0][0:2] == ("get", "https://example.test/resource")


def test_network_settings_path_uses_actions_root(monkeypatch, tmp_path):
    import actions_http

    monkeypatch.setattr(actions_http.sys, "platform", "linux")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert actions_http._NetworkConfig._get_network_settings_path() == (
        tmp_path / ".actions" / "network-settings.yaml"
    )

    monkeypatch.setattr(actions_http.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    assert actions_http._NetworkConfig._get_network_settings_path() == (
        tmp_path / "Local" / "actions" / "network-settings.yaml"
    )


def test_configured_proxy_builds_proxy_manager(monkeypatch):
    import actions_http

    ssl_context = object()
    proxy_manager = object()
    pool_manager = object()

    config = actions_http._NetworkConfig.__new__(actions_http._NetworkConfig)
    monkeypatch.setattr(config, "get_ssl_context", lambda: ssl_context)
    monkeypatch.setattr(
        type(config),
        "profile_config",
        property(lambda self: {"proxy-settings": {"https-proxy": "http://proxy"}}),
    )
    monkeypatch.setattr(
        actions_http.urllib3,
        "ProxyManager",
        lambda **kwargs: (proxy_manager, kwargs)[0],
    )
    monkeypatch.setattr(
        actions_http.urllib3,
        "PoolManager",
        lambda **kwargs: pool_manager,
    )

    assert config._build_connection_pool() is proxy_manager


def test_no_proxy_uses_persisted_hyphenated_schema():
    import actions_http

    config = actions_http._NetworkConfig.__new__(actions_http._NetworkConfig)
    config.profile_config = {"proxy-settings": {"no-proxy": "localhost, 127.0.0.1"}}

    assert actions_http.ProxyConfig.from_network_config(config).no_proxy == [
        "localhost",
        "127.0.0.1",
    ]


def test_ssl_context_uses_supported_truststore():
    import ssl

    import actions_http

    context = actions_http.build_ssl_context()

    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_download_with_resume_uses_fake_pool(tmp_path):
    import actions_http

    target = tmp_path / "download.bin"
    pool = FakePool(FakeResponse(b"downloaded", {"Content-Length": "10"}))

    result = actions_http.download_with_resume(
        "https://example.test/download", target, pool_manager=pool, wait_interval=0
    )

    assert result.status == actions_http.DownloadStatus.DONE
    assert target.read_bytes() == b"downloaded"
    assert pool.requests[0][2]["preload_content"] is False


def test_download_with_resume_leaves_existing_target_untouched(tmp_path):
    import actions_http

    target = tmp_path / "download.bin"
    target.write_bytes(b"existing")
    pool = FakePool(FakeResponse(b"replacement", {"Content-Length": "11"}))

    result = actions_http.download_with_resume(
        "https://example.test/download", target, pool_manager=pool, wait_interval=0
    )

    assert result.status == actions_http.DownloadStatus.ALREADY_EXISTS
    assert target.read_bytes() == b"existing"
    assert pool.requests == []


def test_download_with_resume_resumes_existing_partial_file(tmp_path):
    import actions_http

    target = tmp_path / "download.bin"
    target.with_name("download.bin.part").write_bytes(b"abc")
    pool = FakePool(
        FakeResponse(b"def", {"Content-Length": "3", "Content-Range": "bytes 3-5/6"})
    )

    result = actions_http.download_with_resume(
        "https://example.test/download", target, pool_manager=pool, wait_interval=0
    )

    assert result.status == actions_http.DownloadStatus.DONE
    assert target.read_bytes() == b"abcdef"
    assert pool.requests[0][2]["headers"] == {"Range": "bytes=3-"}


def test_persisted_no_proxy_routes_each_destination_without_changing_tls(monkeypatch):
    import ssl

    import actions_http

    context = ssl.create_default_context()
    config = actions_http._NetworkConfig.__new__(actions_http._NetworkConfig)
    monkeypatch.setattr(config, "get_ssl_context", lambda: context)
    monkeypatch.setattr(
        type(config),
        "profile_config",
        property(
            lambda self: {
                "proxy-settings": {
                    "https-proxy": "http://proxy.example:8080",
                    "no-proxy": "localhost,127.0.0.1,::1,.internal.test,port.test:9443",
                }
            }
        ),
    )
    routes = []

    def fake_urlopen(pool, method, url, **kwargs):
        routes.append(
            (
                isinstance(pool, actions_http.urllib3.ProxyManager),
                pool.connection_pool_kw["ssl_context"],
            )
        )
        return FakeResponse(b"ok", {})

    monkeypatch.setattr(actions_http.urllib3.PoolManager, "urlopen", fake_urlopen)
    pool = config._build_connection_pool()
    for url, proxied in [
        ("http://localhost:54321/path", False),
        ("http://127.0.0.1:54321/path", False),
        ("http://[::1]:54321/path", False),
        ("https://service.internal.test/path", False),
        ("https://port.test:9443/path", False),
        ("https://port.test:443/path", True),
        ("https://notinternal.test/path", True),
        ("https://localhost.evil.test/path", True),
        ("https://public.example/path", True),
    ]:
        pool.urlopen("GET", url)
        assert routes[-1] == (proxied, context), url


def test_no_proxy_redirect_rechecks_the_new_destination(monkeypatch):
    import ssl

    from urllib3.response import HTTPResponse

    import actions_http

    config = actions_http._NetworkConfig.__new__(actions_http._NetworkConfig)
    monkeypatch.setattr(config, "get_ssl_context", ssl.create_default_context)
    monkeypatch.setattr(
        type(config),
        "profile_config",
        property(
            lambda self: {
                "proxy-settings": {
                    "http-proxy": "http://proxy.example:8080",
                    "no-proxy": "localhost",
                }
            }
        ),
    )
    routes = []

    def respond(connection, method, url, **kwargs):
        routes.append(connection.proxy is not None)
        if len(routes) == 1:
            return HTTPResponse(
                status=302,
                headers={"Location": "http://public.example/next"},
                body=b"",
                preload_content=False,
            )
        return HTTPResponse(status=200, body=b"ok")

    monkeypatch.setattr(actions_http.urllib3.HTTPConnectionPool, "urlopen", respond)
    response = config._build_connection_pool().request(
        "GET", "http://localhost:54321/start"
    )
    assert response.status == 200
    assert routes == [False, True]


def test_proxy_to_direct_redirect_updates_generated_host_but_keeps_explicit_host(
    monkeypatch,
):
    import ssl

    from urllib3.response import HTTPResponse

    import actions_http

    config = actions_http._NetworkConfig.__new__(actions_http._NetworkConfig)
    monkeypatch.setattr(config, "get_ssl_context", ssl.create_default_context)
    monkeypatch.setattr(
        type(config),
        "profile_config",
        property(
            lambda self: {
                "proxy-settings": {
                    "http-proxy": "http://proxy.example:8080",
                    "no-proxy": "localhost",
                }
            }
        ),
    )
    for explicit_host in (None, "deliberate.example"):
        requests = []

        def respond(connection, method, url, **kwargs):
            requests.append(
                (connection.proxy is not None, dict(kwargs.get("headers", {})))
            )
            if len(requests) == 1:
                return HTTPResponse(
                    status=303,
                    headers={"Location": "http://localhost:54321/next"},
                    body=b"",
                    preload_content=False,
                )
            return HTTPResponse(status=200, body=b"ok")

        monkeypatch.setattr(actions_http.urllib3.HTTPConnectionPool, "urlopen", respond)
        headers = {
            "Authorization": "synthetic",
            "Cookie": "synthetic",
            "Proxy-Authorization": "synthetic",
        }
        if explicit_host:
            headers["Host"] = explicit_host
        assert (
            config._build_connection_pool()
            .request("GET", "http://public.example/start", headers=headers)
            .status
            == 200
        )
        assert [entry[0] for entry in requests] == [True, False]
        final_headers = requests[-1][1]
        assert final_headers.get("Host") == explicit_host
        assert not {"authorization", "cookie", "proxy-authorization"}.intersection(
            name.lower() for name in final_headers
        )
