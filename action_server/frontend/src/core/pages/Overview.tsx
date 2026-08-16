import { Link } from "react-router-dom";
import { useActionServerContext } from "@/shared/context/actionServerContext";
import { RunStatus } from "@/shared/types";

const labels: Record<RunStatus, string> = {
  [RunStatus.NOT_RUN]: "Not run",
  [RunStatus.RUNNING]: "Running",
  [RunStatus.PASSED]: "Passed",
  [RunStatus.FAILED]: "Failed",
  [RunStatus.CANCELLED]: "Cancelled",
};

export const OverviewPage = () => {
  const { loadedActions, loadedRuns, loadedServerConfig } =
    useActionServerContext();
  const packages = loadedActions.data ?? [];
  const actions = packages
    .flatMap((pkg) => pkg.actions)
    .filter((action) => action.enabled);
  const runs = [...(loadedRuns.data ?? [])].sort(
    (a, b) => b.numbered_id - a.numbered_id,
  );
  const failures = runs
    .filter((run) => run.status === RunStatus.FAILED)
    .slice(0, 3);

  if (loadedActions.isPending || loadedRuns.isPending)
    return (
      <div className="workbench-page" aria-busy="true">
        <p className="eyebrow">Actions Runtime</p>
        <h1>Loading your workbench</h1>
        <p className="lede">
          Connecting to the local runtime and collecting recent runs.
        </p>
      </div>
    );
  if (loadedActions.errorMessage || loadedRuns.errorMessage)
    return (
      <div className="workbench-page">
        <p className="eyebrow">Actions Runtime / unavailable</p>
        <h1>The workbench needs a connection</h1>
        <p className="lede">
          {loadedActions.errorMessage || loadedRuns.errorMessage}
        </p>
        <Link className="button-primary" to="/actions">
          Open Actions
        </Link>
      </div>
    );

  return (
    <div className="workbench-page">
      <header className="workbench-header">
        <div>
          <p className="eyebrow">Actions Runtime</p>
          <h1>Ready for the next run</h1>
          <p className="lede">
            A quiet place to prepare actions, inspect results, and keep the
            thread intact.
          </p>
        </div>
        <div className="runtime-note">
          <span className="status-mark status-running" aria-hidden="true" />
          <span>{loadedServerConfig.data?.version || "Local runtime"}</span>
          <span className="mono">offline-safe</span>
        </div>
      </header>
      <section
        className="workbench-section"
        aria-labelledby="attention-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Signal</p>
            <h2 id="attention-heading">What needs attention</h2>
          </div>
          <Link to="/runs" className="text-link">
            View all runs
          </Link>
        </div>
        {failures.length ? (
          <div className="object-list">
            {failures.map((run) => (
              <Link className="object-row" to={`/runs/${run.id}`} key={run.id}>
                <span>
                  <strong>{run.action_name || "Action run"}</strong>
                  <small className="mono">Run #{run.numbered_id}</small>
                </span>
                <span className="status status-failed">
                  <span aria-hidden="true">×</span> {labels[run.status]}
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-frame">
            <h3>No failures in the latest runs</h3>
            <p>Keep moving, or open the action catalog to start a new run.</p>
          </div>
        )}
      </section>
      <section className="workbench-section" aria-labelledby="actions-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Catalog</p>
            <h2 id="actions-heading">Actions ready to run</h2>
          </div>
          <Link to="/actions" className="text-link">
            Open Actions
          </Link>
        </div>
        {actions.length ? (
          <div className="object-list">
            {actions.slice(0, 4).map((action) => {
              const pkg = packages.find(
                (item) => item.id === action.action_package_id,
              );
              const latest = runs.find((run) => run.action_id === action.id);
              return (
                <Link
                  className="object-row"
                  to={`/actions/${action.id}`}
                  key={action.id}
                >
                  <span>
                    <strong>{action.name}</strong>
                    <small>
                      {pkg?.name} · {action.file}:{action.lineno}
                    </small>
                  </span>
                  <span
                    className={
                      latest
                        ? `status status-${labels[latest.status].toLowerCase()}`
                        : "status status-muted"
                    }
                  >
                    {latest ? labels[latest.status] : "Never run"}
                  </span>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="empty-frame">
            <h3>No actions available yet</h3>
            <p>Install an action package, then return here to run it.</p>
          </div>
        )}
      </section>
      <section className="next-action">
        <div>
          <p className="eyebrow">Next action</p>
          <h2>Choose an action and keep its evidence close.</h2>
          <p>
            Actions, runs, logs, and artifacts stay connected as you move
            through the workbench.
          </p>
        </div>
        <Link
          className="button-primary"
          to={actions[0] ? `/actions/${actions[0].id}` : "/actions"}
        >
          {actions[0] ? "Open first action" : "Open Actions"}
        </Link>
      </section>
    </div>
  );
};
