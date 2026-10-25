import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/lane-b-actions/action_server/scripts")
from lane_b_installed_knowledge_lifecycle import Lifecycle


async def main():
    manifest = json.loads(Path("/workspace/lane-b-state/knowledge-a39-corrected/lifecycle-manifest.json").read_bytes())
    manifest["output_root"] = "/workspace/lane-b-state/knowledge-a39-task-probe"
    runner = Lifecycle(manifest)
    receipt = {"status": "RUNNING", "stage": "installed_origin", "http": "NOT_RUN", "source": manifest["source_checkpoint"]}
    try:
        runner.origin()
        receipt["stage"] = "start"
        await runner.start("ingestion")
        receipt["stage"] = "canvas"
        snapshots = await runner.connect(runner.canvas)
        receipt["stage"] = "ingestion_task"
        args = dict(mode="detached", snapshot=snapshots["ingestion"], inputs={}, idempotencyKey="lane-b-a39-ingestion-before-route")
        terminal = await runner.connect(lambda session: runner.invoke(session, args))
        (runner.root / "terminal.json").write_text(json.dumps(terminal, indent=2))
        (runner.root / "invocation.json").write_text(json.dumps(args, indent=2))
        receipt.update(status="PASS", stage="completed", task_id=terminal["taskId"])
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__)
    finally:
        try:
            await runner.stop()
        except BaseException as error:
            receipt.update(status="FAIL", cleanup_error_type=type(error).__name__)
        receipt["shutdowns"] = runner.receipt.get("shutdowns", [])
        (runner.root / "task-receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    os.umask(0o077)
    raise SystemExit(asyncio.run(main()))
