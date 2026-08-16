import { Link } from "react-router-dom";
import { useActionServerContext } from "@/shared/context/actionServerContext";
import { RunStatus } from "@/shared/types";

const status = (value: RunStatus) =>
  ({
    [RunStatus.PASSED]: ["Passed", "✓"],
    [RunStatus.FAILED]: ["Failed", "!"],
    [RunStatus.RUNNING]: ["Running", "…"],
    [RunStatus.CANCELLED]: ["Cancelled", "×"],
    [RunStatus.NOT_RUN]: ["Not run", "·"],
  })[value] ?? ["Unknown", "?"];

export const OverviewPage = () => {
  const { loadedActions, loadedRuns, loadedServerConfig } =
    useActionServerContext();
  const actions =
    loadedActions.data?.flatMap((pkg) =>
      pkg.actions.filter((action) => action.enabled),
    ) ?? [];
  const packages = loadedActions.data ?? [];
  const runs = [...(loadedRuns.data ?? [])].sort(
    (a, b) => b.numbered_id - a.numbered_id,
  );
  const failed = runs.find((run) => run.status === RunStatus.FAILED);
  const actionName = (id: string) =>
    actions.find((action) => action.id === id)?.name ?? id;
  return (
    <div className="runtime-page">
      <header className="runtime-page-header">
        <div>
          <p className="runtime-eyebrow">Actions Runtime / overview</p>
          <h1>Execution console</h1>
          <p className="runtime-lede">
            Run local actions, follow their trace, and inspect the evidence they
            leave behind.
          </p>
        </div>
        <div className="runtime-context" aria-label="Runtime context">
          <span className="runtime-dot" />
          <strong>{loadedServerConfig.data?.version ?? "fixture-v1"}</strong>
          <span>local runtime</span>
        </div>
      </header>
      <section className="runtime-attention" aria-labelledby="attention-title">
        <div>
          <p className="runtime-section-label">Attention queue</p>
          <h2 id="attention-title">
            {failed ? "A run needs inspection" : "All systems ready"}
          </h2>
          <p>
            {failed
              ? `${actionName(failed.action_id)} reported an actionable failure.`
              : "No failed executions are waiting for review."}
          </p>
        </div>
        {failed && (
          <Link className="runtime-link-button" to={`/logs/${failed.id}`}>
            Inspect failure <span aria-hidden="true">→</span>
          </Link>
        )}
      </section>
      <div className="runtime-grid">
        <section className="runtime-panel" aria-labelledby="runs-title">
          <div className="runtime-panel-heading">
            <div>
              <p className="runtime-section-label">Latest evidence</p>
              <h2 id="runs-title">Recent runs</h2>
            </div>
            <Link to="/runs">View history</Link>
          </div>
          <div className="runtime-run-list">
            {runs.slice(0, 4).map((run) => {
              const [label, icon] = status(run.status);
              return (
                <Link
                  className="runtime-run-row"
                  key={run.id}
                  to={`/logs/${run.id}`}
                >
                  <span
                    className={`runtime-status status-${label.toLowerCase()}`}
                  >
                    <span aria-hidden="true">{icon}</span>
                    {label}
                  </span>
                  <span className="runtime-run-name">
                    {actionName(run.action_id)}
                  </span>
                  <span className="runtime-mono">#{run.numbered_id}</span>
                  <span className="runtime-mono">
                    {run.run_time ? `${run.run_time.toFixed(2)}s` : "active"}
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
        <section className="runtime-panel" aria-labelledby="actions-title">
          <div className="runtime-panel-heading">
            <div>
              <p className="runtime-section-label">Available work</p>
              <h2 id="actions-title">Action inventory</h2>
            </div>
            <Link to="/actions">Open catalog</Link>
          </div>
          <p className="runtime-count">
            <strong>{actions.length}</strong> enabled actions <span>/</span>{" "}
            {packages.length} packages
          </p>
          {actions.slice(0, 3).map((action) => (
            <Link className="runtime-action-row" key={action.id} to="/actions">
              <span className="runtime-action-mark" aria-hidden="true">
                ↯
              </span>
              <span>
                <strong>{action.name}</strong>
                <small>
                  {action.file}:{action.lineno}
                </small>
              </span>
              <span aria-hidden="true">→</span>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
};
