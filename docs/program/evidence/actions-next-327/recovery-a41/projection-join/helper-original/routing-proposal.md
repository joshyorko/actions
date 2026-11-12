PROPOSED ONLY; no routing changes applied or tested.

Add app-only canvas_projection to APP_TOOLS, not model tools. Input is AppRunRequest {mode: generic, bindingId, runId}, with existing appSession broker handling. Add CanvasReply.projection and map it to actions.projection metadata. Add the AppRunRequest schema and generic app dispatch allowlist entry.

In GenericCanvasView._app, after the existing _entry block has ended and _selected/_read have resolved the canonical service and ticket, call project_generated_result(service.outputs/base outputs, actor, snapshot=service.snapshot, binding_id=request.bindingId, run_id=request.runId, attempt_id=ticket.fence.attempt_id, require_current=callback). Return its as_dict() in CanvasReply.projection.

The callback must be SQL-only: repository.current must still equal the selected active deployment/app; the current binding must equal the selected capability; _association must still bind this run to this app/binding; _artifact_permission must recheck live read and managed queue READ/ARTIFACT_READ. Do NOT call _selected, _read, registry.load_verified, schema_for, or provider reads in that callback. Helper independently rechecks RunPin, admission principal, snapshot, terminal success, exact current Attempt, attached inventory and receipt.

Wire is {bindingId,runId,attemptId,canonicalJson,data}. requestId is exclusively the trusted frontend generation and is not server authority. Route regressions still required: model catalog exclusion, scoped session denial, wrong app binding, post-read revocation, and adapter generation handling.
