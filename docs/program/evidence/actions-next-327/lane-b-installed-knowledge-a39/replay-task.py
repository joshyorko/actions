import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/lane-b-actions/action_server/scripts")
from lane_b_installed_knowledge_lifecycle import Lifecycle


async def main():
    original = Path("/workspace/lane-b-state/knowledge-a39-task-probe")
    expected = json.loads((original / "terminal.json").read_bytes())
    invocation = json.loads((original / "invocation.json").read_bytes())
    manifest = json.loads(Path("/workspace/lane-b-state/knowledge-a39-corrected/lifecycle-manifest.json").read_bytes())
    manifest["output_root"] = "/workspace/lane-b-state/knowledge-a39-task-replay"
    runner = Lifecycle(manifest)
    receipt = {"status": "RUNNING", "stage": "restart", "http": "NOT_RUN", "source": manifest["source_checkpoint"]}
    try:
        runner.origin()
        await runner.start("replay")
        receipt["stage"] = "task_replay"
        terminal = await runner.connect(lambda session: runner.invoke(session, invocation))
        (runner.root / "terminal.json").write_text(json.dumps(terminal, indent=2))
        assert terminal == expected
        receipt.update(status="PASS", stage="completed", task_id=terminal["taskId"], attempt_id=terminal["result"]["structuredContent"]["attemptId"], exact_terminal_equal=True)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__)
    finally:
        try:
            await runner.stop()
        except BaseException as error:
            receipt.update(status="FAIL", cleanup_error_type=type(error).__name__)
        receipt["shutdowns"] = runner.receipt.get("shutdowns", [])
        (runner.root / "receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    os.umask(0o077)
    raise SystemExit(asyncio.run(main()))
