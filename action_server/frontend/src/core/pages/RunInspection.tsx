import { Link, useParams } from "react-router-dom";
import { useRuntimeRun } from "@/queries/runtime";
import { useActionServerContext } from "@/shared/context/actionServerContext";

export const RunInspectionPage = () => {
  const { runId = "" } = useParams();
  const { data: run, isPending, error } = useRuntimeRun(runId);
  const { loadedActions } = useActionServerContext();
  const action = loadedActions.data
    ?.flatMap((pkg) => pkg.actions)
    .find((item) => item.id === run?.action_id);
  if (isPending)
    return (
      <div className="workbench-page" aria-busy="true" role="status">
        <p className="eyebrow">Run inspection</p>
        <h1>Loading run evidence</h1>
      </div>
    );
  if (error || !run)
    return (
      <div className="workbench-page state-unavailable" role="alert">
        <p className="eyebrow">Run inspection / unavailable</p>
        <h1>Run evidence is unavailable</h1>
        <p className="lede">
          Keep the run ID and try again when the runtime is connected.
        </p>
        <Link className="button-primary" to="/runs">
          Back to runs
        </Link>
      </div>
    );
  const failed = run.status === 3;
  const passed = run.status === 2;
  const label = failed
    ? "Failed"
    : passed
      ? "Passed"
      : run.status === 1
        ? "Running"
        : "Cancelled";
  return (
    <div className="workbench-page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/actions">Actions</Link>
        <span>/</span>
        {action ? (
          <Link to={`/actions/${action.id}`}>{action.name}</Link>
        ) : (
          <span>Run</span>
        )}
        <span>/</span>
        <strong>Run #{run.numbered_id}</strong>
      </nav>
      <header className="workbench-header">
        <div>
          <p className="eyebrow">
            Run inspection · <span className="mono">{run.id}</span>
          </p>
          <h1>{run.action_name || action?.name || "Action run"}</h1>
          <p className="lede">
            {new Date(run.start_time).toISOString()} ·{" "}
            {run.run_time
              ? `${run.run_time.toFixed(2)} seconds`
              : "still running"}
          </p>
        </div>
        <span
          className={`status status-${failed ? "failed" : passed ? "passed" : "running"}`}
        >
          <span aria-hidden="true">{failed ? "×" : passed ? "✓" : "•"}</span>{" "}
          {label}
        </span>
      </header>
      <section className="trace-layout">
        <div className="trace-main">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Lifecycle evidence</p>
              <h2>Recorded run state</h2>
            </div>
            <span className="mono">run/{run.numbered_id}</span>
          </div>
          <p className="trace-unavailable" role="status">Trace telemetry is unavailable for this run; the runtime currently exposes lifecycle fields only.</p>
          <ol className="trace-list">
            <li>
              <span className="trace-dot" aria-hidden="true" />
              <div>
                <strong>Run recorded</strong>
                <small className="mono">lifecycle evidence</small>
              </div>
            </li>
            <li className={failed ? "trace-failed" : ""}>
              <span className="trace-dot" aria-hidden="true" />
              <div>
                <strong>
                  {failed
                    ? "Run marked failed"
                    : passed
                       ? "Run marked passed"
                       : "Run remains active"}
                </strong>
                <small>
                  {run.error_message ||
                    run.result ||
                    "Waiting for the next runtime event."}
                </small>
              </div>
            </li>
          </ol>
        </div>
        <aside className="trace-side">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Evidence</p>
              <h2>Logs & output</h2>
            </div>
          </div>
          <pre className="code-panel">
            {run.error_message ||
              run.stdout ||
              run.result ||
              "No output recorded yet."}
          </pre>
          <div className="side-links">
            <Link to={`/runs/${run.id}`}>Run overview</Link>
            <Link to={`/logs/${run.id}`}>Open full logs</Link>
            <Link to={`/artifacts/${run.id}`}>View artifacts</Link>
          </div>
        </aside>
      </section>
    </div>
  );
};
