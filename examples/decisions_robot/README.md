# Work Item decisions with Robot Framework

This source-checkout example uses the existing SQLite Work Items SDK and the
Runtime's optional Decisions provider. It classifies synthetic `invoice`,
`credit_note`, and `other` items and persists typed, review-only evidence as
child output Work Items. It leaves source items pending.

After the repository's pinned Doctor, Bootstrap, and ToolkitTest tasks, run
these commands from the repository root with the prepared package interpreter.

```sh
demo_dir=$(mktemp -d "${TMPDIR:-/tmp}/codex-decisions-robot-XXXXXX")
action_server/.venv/bin/python -m robot --outputdir "$demo_dir/first" --variable "STATE_DIR:$demo_dir/state" examples/decisions_robot/tasks.robot
action_server/.venv/bin/python -m robot --outputdir "$demo_dir/replay" --variable "STATE_DIR:$demo_dir/state" examples/decisions_robot/tasks.robot
```

The first process makes three synthetic provider calls. The second makes none.
The retained `state/summary.json` reports three decisions and pending sources.
Robot writes `output.xml`, `log.html`, and `report.html` under each output root.
The supplied RCC manifest includes this checkout's Runtime source on
`PYTHONPATH`; it is not a standalone published package. The prepared-interpreter
commands above are the qualified run path.

This is a serial local demonstration. Its SDK output intent prevents automatic
replay after an interrupted provider call. It does not establish concurrent
managed claim safety, Workspace authorization, decision-bound human approval,
or native Runtime registration. Use a dedicated state directory. Changed
protected input requires a new decision context and never inherits an answer.

The default provider reports `synthetic-document/v1`. OpenAI has no fallback.
The optional `BACKEND:openai` task requires `DECISIONS_OPENAI_LIVE=1`,
`OPENAI_API_KEY_FILE`, and `OPENAI_PROJECT_ID`. That task can make three paid
requests. Do not enable it without explicit approval. Use the separate
single-request live smoke first. Request a fresh key through T3's secret prompt;
never place a key in Robot arguments, Work Items, or source files.
