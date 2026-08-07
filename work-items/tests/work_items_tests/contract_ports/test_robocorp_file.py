# Copyright 2022-2026 Robocorp and contributors.
# Licensed under the Apache License, Version 2.0.
# Executable compatibility port adapted to actions-work-items.
# ruff: noqa
# ruff: noqa: E501
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

from actions.work_items._adapters import FileAdapter
from actions.work_items._types import State

ITEMS_JSON = [{"payload": {"a-key": "a-value"}, "files": {"a-file": "file.txt"}}]


class TestFileAdapter:
    """Tests the local dev env `FileAdapter` on Work Items."""

    @contextmanager
    def _mock_work_items(self):
        with tempfile.TemporaryDirectory() as items_dir:
            items_dir = Path(items_dir)

            items_in = items_dir / "items.json"
            items_out = items_dir / "items.out.json"

            with open(items_in, "w") as fd:
                json.dump(ITEMS_JSON, fd)
            with open(os.path.join(items_dir, "file.txt"), "w") as fd:
                fd.write("some mock content")

            yield items_in, items_out

    @pytest.fixture(
        params=[
            ("RC_WORKITEM_INPUT_PATH", "RC_WORKITEM_OUTPUT_PATH"),
            ("RPA_INPUT_WORKITEM_PATH", "RPA_OUTPUT_WORKITEM_PATH"),
        ]
    )
    def adapter(self, monkeypatch, request):
        with self._mock_work_items() as (items_in, items_out):
            monkeypatch.setenv(request.param[0], str(items_in))
            monkeypatch.setenv(request.param[1], str(items_out))
            yield FileAdapter()

    @pytest.fixture
    def workitems(self, adapter):
        from actions import workitems

        workitems.init(adapter)
        yield workitems

    def test_load_data(self, adapter):
        item_id = adapter.reserve_input()
        data = adapter.load_payload(item_id)
        assert data == {"a-key": "a-value"}

    def test_list_files(self, adapter):
        item_id = adapter.reserve_input()
        files = adapter.list_files(item_id)
        assert files == ["a-file"]

    def test_get_file(self, adapter):
        item_id = adapter.reserve_input()
        content = adapter.get_file(item_id, "a-file")
        assert content == b"some mock content"

    def test_add_file(self, adapter):
        item_id = adapter.create_output("0")
        adapter.add_file(
            item_id,
            "secondfile.txt",
            content=b"somedata",
        )
        assert adapter._outputs[0]["files"]["secondfile.txt"] == "secondfile.txt"
        assert os.path.isfile(Path(adapter._output_path).parent / "secondfile.txt")

    def test_save_data_input(self, adapter):
        item_id = adapter.reserve_input()
        adapter.save_payload(item_id, {"key": "value"})
        with open(adapter._input_path) as fd:
            data = json.load(fd)
            assert data == [
                {"payload": {"key": "value"}, "files": {"a-file": "file.txt"}}
            ]

    def test_save_data_output(self, adapter):
        item_id = adapter.create_output("0", {})
        adapter.save_payload(item_id, {"key": "value"})

        output = adapter._output_path
        assert os.path.isfile(output)
        with open(output) as fd:
            data = json.load(fd)
            assert data == [{"payload": {"key": "value"}, "files": {}}]

    def test_missing_file(self, monkeypatch):
        monkeypatch.setenv("RC_WORKITEM_INPUT_PATH", "not-exist.json")
        with pytest.raises(ValueError):
            FileAdapter()

    def test_empty_queue(self, monkeypatch):
        with tempfile.TemporaryDirectory() as items_dir:
            items = os.path.join(items_dir, "items.json")
            with open(items, "w") as fd:
                json.dump([], fd)

            monkeypatch.setenv("RC_WORKITEM_INPUT_PATH", items)
            with pytest.raises(ValueError):
                FileAdapter()

    def test_malformed_queue(self, monkeypatch):
        with tempfile.TemporaryDirectory() as items_dir:
            items = os.path.join(items_dir, "items.json")
            with open(items, "w") as fd:
                json.dump(["not-an-item"], fd)

            monkeypatch.setenv("RC_WORKITEM_INPUT_PATH", items)
            with pytest.raises(ValueError):
                FileAdapter()

    def test_missing_parent_directory(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "not-exist", "output.json")
            monkeypatch.setenv("RC_WORKITEM_OUTPUT_PATH", output_dir)

            # Should not raise
            adapter = FileAdapter()
            adapter.create_output("0", {"key": "value"})

    def test_invalid_reporter(self, workitems):
        results = []
        for work_item in workitems.inputs:
            with work_item:
                results.append(work_item.payload)

        with pytest.raises(ValueError):
            output = workitems.outputs.create()
            output.payload = {"results": results}
            output.save()

    def test_valid_reporter(self, workitems):
        output = workitems.outputs.create()

        results = []
        for work_item in workitems.inputs:
            with work_item:
                results.append(work_item.payload)

        output.payload = {"results": results}
        output.save()


class TestRobocorpAdapter:
    """Test control room API calls and retrying behaviour."""

    ENV = {
        "RC_WORKSPACE_ID": "1",
        "RC_PROCESS_RUN_ID": "2",
        "RC_ACTIVITY_RUN_ID": "3",
        "RC_WORKITEM_ID": "4",
        "RC_API_WORKITEM_HOST": "https://api.workitem.com",
        "RC_API_WORKITEM_TOKEN": "workitem-token",
        "RC_API_PROCESS_HOST": "https://api.process.com",
        "RC_API_PROCESS_TOKEN": "process-token",
        "RC_PROCESS_ID": "5",
    }

    HEADERS_WORKITEM = {
        "Authorization": f"Bearer {ENV['RC_API_WORKITEM_TOKEN']}",
        "Content-Type": "application/json",
    }
    HEADERS_PROCESS = {
        "Authorization": f"Bearer {ENV['RC_API_PROCESS_TOKEN']}",
        "Content-Type": "application/json",
    }

    @pytest.fixture
    def adapter(self, monkeypatch):
        for name, value in self.ENV.items():
            monkeypatch.setenv(name, value)

        with (
            mock.patch("robocorp.workitems._requests.requests.get") as mock_get,
            mock.patch("robocorp.workitems._requests.requests.post") as mock_post,
            mock.patch("robocorp.workitems._requests.requests.put") as mock_put,
            mock.patch("robocorp.workitems._requests.requests.delete") as mock_delete,
            mock.patch("time.sleep", return_value=None) as mock_sleep,
        ):
            self.mock_get = mock_get
            self.mock_post = mock_post
            self.mock_put = mock_put
            self.mock_delete = mock_delete

            self.mock_get.__name__ = "get"
            self.mock_post.__name__ = "post"
            self.mock_put.__name__ = "put"
            self.mock_delete.__name__ = "delete"

            self.mock_get.return_value.status_code = 200
            self.mock_post.return_value.status_code = 200
            self.mock_put.return_value.status_code = 200


