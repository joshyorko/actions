"""Experimental HTTP adapter for a Yorko Control Room deployment.

This module is deliberately not exported until the Yorko optional dependency and
normalized adapter protocol are integrated.  It implements the current adapter
boundary only so its HTTP behavior can be tested in isolation.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urljoin

try:  # pragma: no cover - the optional extra owns this dependency at integration.
    import requests
except ImportError as error:  # pragma: no cover
    raise ImportError(
        "Yorko support requires requests. Install actions-work-items[yorko]."
    ) from error

from .._exceptions import ApplicationException, EmptyQueue
from .._types import ExceptionType, JSONType, State
from .._utils import required_env
from ._base import BaseAdapter


class YorkoAdapter(BaseAdapter):
    """Experimental adapter for Yorko's workspace work-item HTTP API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_token: str | None = None,
        workspace_id: str | None = None,
        worker_id: str | None = None,
        timeout: float | None = None,
        session: Any | None = None,
    ) -> None:
        self.api_url = (api_url or required_env("YORKO_API_URL")).rstrip("/")
        self._api_token = api_token or required_env("YORKO_API_TOKEN")
        self.workspace_id = workspace_id or required_env("YORKO_WORKSPACE_ID")
        self.worker_id = worker_id or required_env("YORKO_WORKER_ID")
        self.timeout = timeout if timeout is not None else float(os.getenv("YORKO_REQUEST_TIMEOUT", "30"))
        self.session = session or requests.Session()

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}"}

    def _url(self, *parts: str) -> str:
        path = "/".join(quote(part, safe="") for part in parts)
        return urljoin(f"{self.api_url}/", path)

    def _request(self, method: str, *parts: str, **kwargs: Any) -> Any:
        kwargs.setdefault("headers", self._headers)
        kwargs.setdefault("timeout", self.timeout)
        try:
            response = getattr(self.session, method)(self._url(*parts), **kwargs)
        except (TimeoutError, requests.RequestException) as error:
            raise ApplicationException("Yorko request timed out") from error
        if not 200 <= response.status_code < 300:
            raise ApplicationException(f"Yorko HTTP {response.status_code}")
        return response

    def _json_object(self, response: Any) -> Mapping[str, Any]:
        try:
            payload = response.json()
        except ValueError as error:
            raise ApplicationException("Yorko returned invalid JSON") from error
        if not isinstance(payload, Mapping):
            raise ApplicationException("Yorko returned malformed JSON")
        return payload

    def reserve_input(self) -> str:
        response = self._request(
            "get",
            "api",
            "v1",
            "workspaces",
            self.workspace_id,
            "work-items",
            "next",
            params={"worker_id": self.worker_id},
        )
        item_id = self._json_object(response).get("id")
        if not isinstance(item_id, str) or not item_id:
            raise EmptyQueue("No Yorko work items are available")
        return item_id

    def release_input(
        self,
        item_id: str,
        state: State,
        exception_type: ExceptionType | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        base = ("api", "v1", "workspaces", self.workspace_id, "work-items", item_id)
        if state in (State.DONE, State.COMPLETED):
            self._request(
                "post", *base, "complete", json={"worker_id": self.worker_id, "output_data": {}}
            )
            return
        exception_data = {
            key: value
            for key, value in {
                "type": exception_type.value if exception_type else None,
                "code": code,
                "message": message,
            }.items()
            if value
        }
        self._request(
            "post",
            *base,
            "fail",
            json={
                "worker_id": self.worker_id,
                "error_message": message or "Unknown error",
                "exception_data": exception_data,
            },
        )

    def create_output(self, parent_id: str, payload: JSONType | None = None) -> str:
        response = self._request(
            "post",
            "api",
            "v1",
            "workspaces",
            self.workspace_id,
            "work-items",
            json={
                "name": f"Output from {parent_id}",
                "parent_id": parent_id,
                "payload": payload if payload is not None else {},
            },
        )
        item_id = self._json_object(response).get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ApplicationException("Yorko returned a malformed output response")
        return item_id

    def load_payload(self, item_id: str) -> JSONType:
        response = self._request(
            "get", "api", "v1", "workspaces", self.workspace_id, "work-items", item_id
        )
        return self._json_object(response).get("payload", {})

    def save_payload(self, item_id: str, payload: JSONType) -> None:
        self._request(
            "patch",
            "api",
            "v1",
            "workspaces",
            self.workspace_id,
            "work-items",
            item_id,
            json={"payload": payload},
        )

    def list_files(self, item_id: str) -> list[str]:
        response = self._request(
            "get", "api", "v1", "workspaces", self.workspace_id, "work-items", item_id, "files"
        )
        files = self._json_object(response).get("files", [])
        if not isinstance(files, list):
            raise ApplicationException("Yorko returned malformed file metadata")
        names = []
        for file in files:
            if isinstance(file, Mapping):
                name = file.get("name")
                if not isinstance(name, str) or not name:
                    raise ApplicationException("Yorko returned malformed file metadata")
                names.append(name)
            elif isinstance(file, str) and file:
                names.append(file)
            else:
                raise ApplicationException("Yorko returned malformed file metadata")
        return names

    def get_file(self, item_id: str, name: str) -> bytes:
        return self._request(
            "get",
            "api",
            "v1",
            "workspaces",
            self.workspace_id,
            "work-items",
            item_id,
            "files",
            name,
        ).content

    def add_file(self, item_id: str, name: str, original_name: str, content: bytes) -> None:
        self._request(
            "post",
            "api",
            "v1",
            "workspaces",
            self.workspace_id,
            "work-items",
            item_id,
            "files",
            files={"file": (original_name, content)},
            params={"name": name},
        )

    def remove_file(self, item_id: str, name: str) -> None:
        self._request(
            "delete",
            "api",
            "v1",
            "workspaces",
            self.workspace_id,
            "work-items",
            item_id,
            "files",
            name,
        )


YorkoControlRoomAdapter = YorkoAdapter
