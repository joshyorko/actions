"""Actual loopback HTTP output probes; no Runtime, SQL or authentication fallback.

Construct OutputHttpProbe with an in-memory owned credential and retained output.
Call qualify(), perform explicit operator revocation externally, then call
after_revocation() on the same object. Receipts contain no credentials or URLs.
An absent positive route fails. Simulated HTTP tests do not qualify an installed
Runtime; the caller must retain its independently verified installed identity.
The credential must be the configured installation owner bearer accepted by both
ordinary outer middleware/endpoint dependencies and the managed authenticator.
An arbitrary managed credential is not sufficient for the output HTTP path.
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import secrets
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx2

DENIED = frozenset({401, 403, 404})
HANDLE = re.compile(r"art_[A-Za-z0-9_-]{22}")


class OutputHttpFailure(Exception):
    """Safe failure carrying the partial nonsecret receipt, never request details."""

    def __init__(self, receipt):
        super().__init__("output HTTP qualification failed")
        self.receipt = receipt


class OutputHttpProbe:
    def __init__(
        self,
        base_url,
        credential,
        workspace_id,
        handle,
        expected_bytes,
        *,
        app_session=None,
        timeout_seconds=15,
    ):
        url = urlsplit(base_url)
        if (
            url.scheme != "http"
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or not url.hostname
            or not ipaddress.ip_address(url.hostname).is_loopback
            or url.port is None
        ):
            raise ValueError("explicit numeric loopback HTTP origin required")
        if (
            not isinstance(credential, str)
            or not credential
            or any(c in credential for c in "\r\n")
            or str(UUID(workspace_id)) != workspace_id
            or not HANDLE.fullmatch(handle)
            or not isinstance(expected_bytes, bytes)
            or len(expected_bytes) > 16 * 1024**2
            or isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 60
        ):
            raise ValueError("bounded owned output probe configuration required")
        if app_session is not None and (
            not isinstance(app_session, str)
            or not app_session
            or app_session == credential
            or any(c in app_session for c in "\r\n")
        ):
            raise ValueError("distinct optional AppSession credential required")
        self._base = base_url.rstrip("/")
        self._credential = credential
        self._workspace = workspace_id
        self._handle = handle
        self._expected = expected_bytes
        self._app_session = app_session
        self._timeout = timeout_seconds
        self._qualified = False

    def _headers(self):
        return {"Authorization": "Bearer " + self._credential}

    async def _read(
        self, client, receipt, name, headers, *, workspace=None, handle=None
    ):
        record = {"probe": name, "status": "RUNNING"}
        receipt["probes"].append(record)
        path = f"/api/workspaces/{workspace or self._workspace}/outputs/{handle or self._handle}"
        raw, digest = bytearray(), hashlib.sha256()
        try:
            async with asyncio.timeout(self._timeout):
                async with client.stream(
                    "GET", self._base + path, headers=headers
                ) as response:
                    record["http_status"] = response.status_code
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        digest.update(chunk)
                        raw.extend(chunk)
                        if len(raw) > max(len(self._expected) + 1, 65536):
                            raise ValueError("response exceeds probe budget")
                    record.update(bytes=len(raw), sha256=digest.hexdigest())
                    return response.status_code, response.headers, bytes(raw), record
        except Exception as error:
            record.update(
                status="FAIL",
                error_type=type(error).__name__,
                bytes=len(raw),
                sha256=digest.hexdigest(),
            )
            receipt["status"] = "FAIL"
            raise OutputHttpFailure(receipt) from None

    @staticmethod
    def _check(receipt, record, condition):
        record["status"] = "PASS" if condition else "FAIL"
        if not condition:
            receipt["status"] = "FAIL"
            raise OutputHttpFailure(receipt)

    def _receipt(self, scope):
        return {
            "status": "RUNNING",
            "scope": scope,
            "probes": [],
            "installed_identity": "caller must supply independent evidence",
        }

    async def qualify(self):
        """Read exact bytes and exercise denial boundaries with real HTTP requests."""
        self._qualified = False
        receipt = self._receipt("authenticated HTTP output readback and denial probes")
        async with httpx2.AsyncClient(
            timeout=self._timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            code, headers, raw, record = await self._read(
                client, receipt, "valid", self._headers()
            )
            controls = {
                part.strip().lower()
                for part in headers.get("cache-control", "").split(",")
            }
            self._check(
                receipt,
                record,
                code == 200
                and raw == self._expected
                and "no-store" in controls
                and headers.get("x-content-type-options", "").lower() == "nosniff",
            )
            invalid = secrets.token_urlsafe(32)
            while invalid == self._credential or invalid == self._app_session:
                invalid = secrets.token_urlsafe(32)
            cases = [
                ("missing_credential", {}),
                ("invalid_credential", {"Authorization": "Bearer " + invalid}),
            ]
            receipt["app_session"] = (
                "NOT_RUN" if self._app_session is None else "REQUESTED"
            )
            if self._app_session is not None:
                cases.extend(
                    [
                        (
                            "app_session_bearer_only",
                            {"Authorization": "Bearer " + self._app_session},
                        ),
                        (
                            "app_session_header_only",
                            {"X-App-Session": self._app_session},
                        ),
                    ]
                )
            for name, supplied in cases:
                code, _, _, record = await self._read(client, receipt, name, supplied)
                self._check(receipt, record, code in DENIED)
            if self._app_session is not None:
                receipt["app_session"] = "PASS"
            other_workspace = str(uuid4())
            while other_workspace == self._workspace:
                other_workspace = str(uuid4())
            unknown = "art_" + secrets.token_urlsafe(16)
            while unknown == self._handle:
                unknown = "art_" + secrets.token_urlsafe(16)
            for name, selection in (
                ("cross_workspace", {"workspace": other_workspace}),
                ("unknown_handle", {"handle": unknown}),
            ):
                code, _, _, record = await self._read(
                    client, receipt, name, self._headers(), **selection
                )
                self._check(receipt, record, code in DENIED)
            code, _, _, record = await self._read(
                client, receipt, "range", dict(self._headers(), Range="bytes=0-0")
            )
            self._check(receipt, record, code == 416)
        receipt["status"] = "PASS"
        self._qualified = True
        return receipt

    async def after_revocation(self):
        """Prove the same credential/Workspace/handle is denied after external revoke.

        The caller owns and records operator revocation. This method performs no
        mutation and cannot by itself prove which grant was revoked.
        """
        if not self._qualified:
            raise ValueError(
                "successful positive baseline required before revocation probe"
            )
        receipt = self._receipt("same retained output after caller-owned revocation")
        async with httpx2.AsyncClient(
            timeout=self._timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            code, _, _, record = await self._read(
                client, receipt, "after_revocation", self._headers()
            )
            self._check(receipt, record, code in DENIED)
        receipt["status"] = "PASS"
        return receipt
