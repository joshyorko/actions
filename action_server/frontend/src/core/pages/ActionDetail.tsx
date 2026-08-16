import { Link, useNavigate, useParams } from "react-router-dom";
import { useActionRunMutation } from "@/queries/actions";
import { useActionServerContext } from "@/shared/context/actionServerContext";

export const ActionDetailPage = () => {
  const { actionId } = useParams();
  const navigate = useNavigate();
  const { loadedActions, loadedRuns } = useActionServerContext();
  const packages = loadedActions.data ?? [];
  const pkg = packages.find((item) =>
    item.actions.some((action) => action.id === actionId),
  );
  const action = pkg?.actions.find((item) => item.id === actionId);
  const runs = (loadedRuns.data ?? [])
    .filter((run) => run.action_id === actionId)
    .sort((a, b) => b.numbered_id - a.numbered_id);
  const { mutateAsync: runAction, isPending } = useActionRunMutation();
  if (loadedActions.isPending)
    return (
      <div className="workbench-page" aria-busy="true">
        <p>Loading action…</p>
      </div>
    );
  if (!action || !pkg)
    return (
      <div className="workbench-page">
        <p className="eyebrow">Actions / missing</p>
        <h1>Action not found</h1>
        <Link className="text-link" to="/actions">
          Back to Actions
        </Link>
      </div>
    );
  const run = async () => {
    const result = await runAction({
      actionPackageName: pkg.name,
      actionName: action.name,
      args: {},
    });
    if (result.runId) navigate(`/runs/${result.runId}`);
  };
  return (
    <div className="workbench-page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/actions">Actions</Link>
        <span>/</span>
        <span>{pkg.name}</span>
        <span>/</span>
        <strong>{action.name}</strong>
      </nav>
      <header className="workbench-header action-header">
        <div>
          <p className="eyebrow">
            {pkg.name} · {action.file}:{action.lineno}
          </p>
          <h1>{action.name}</h1>
          <p className="lede">{action.docs || "No description supplied."}</p>
        </div>
        <button
          className="button-primary"
          type="button"
          onClick={run}
          disabled={isPending || !action.enabled}
        >
          {isPending ? "Starting…" : "Run action"}
        </button>
      </header>
      <div className="workbench-tabs" role="tablist" aria-label="Action views">
        <a className="selected" href="#run">
          Run
        </a>
        <a href="#documentation">Documentation</a>
        <a href="#history">History</a>
        <a href={`/artifacts/${runs[0]?.id || "run-passed"}`}>Artifacts</a>
      </div>
      <section id="run" className="workbench-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Input</p>
            <h2>Run this action</h2>
          </div>
          <span className="mono">
            POST /api/actions/{pkg.name}/{action.name}/run
          </span>
        </div>
        <div className="code-panel">
          <p className="eyebrow">Input schema</p>
          <pre>{action.input_schema}</pre>
        </div>
      </section>
      <section id="documentation" className="workbench-section">
        <p className="eyebrow">Documentation</p>
        <h2>What this action does</h2>
        <p className="prose">
          {action.docs || "Documentation is not available for this action."}
        </p>
      </section>
      <section id="history" className="workbench-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">History</p>
            <h2>Recent runs</h2>
          </div>
          <Link
            to={`/runs?search=${encodeURIComponent(action.name)}`}
            className="text-link"
          >
            Open global history
          </Link>
        </div>
        {runs.length ? (
          <div className="object-list">
            {runs.slice(0, 5).map((run) => (
              <Link className="object-row" to={`/runs/${run.id}`} key={run.id}>
                <span>
                  <strong>Run #{run.numbered_id}</strong>
                  <small className="mono">
                    {run.run_time
                      ? `${run.run_time.toFixed(2)} s`
                      : "In progress"}
                  </small>
                </span>
                <span className="status">
                  {run.status === 3
                    ? "Failed"
                    : run.status === 2
                      ? "Passed"
                      : "Running"}
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-frame">
            <h3>No runs yet</h3>
            <p>Run the action to create the first evidence trail.</p>
          </div>
        )}
      </section>
    </div>
  );
};
