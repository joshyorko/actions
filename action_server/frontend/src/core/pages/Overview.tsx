import { Link } from "react-router-dom";
import { useActionServerContext } from "@/shared/context/actionServerContext";

export const OverviewPage = () => {
  const { loadedActions, loadedRuns, loadedServerConfig } =
    useActionServerContext();
  const unavailable = Boolean(loadedServerConfig.errorMessage);
  const dataUnavailable = Boolean(
    loadedActions.errorMessage || loadedRuns.errorMessage,
  );
  const loading =
    loadedActions.isPending ||
    loadedRuns.isPending ||
    loadedServerConfig.isPending;

  if (unavailable) {
    return (
      <section
        className="mx-auto max-w-5xl p-6"
        aria-labelledby="runtime-unavailable-title"
      >
        <p className="text-sm font-medium text-muted-foreground">
          Actions Runtime
        </p>
        <h1
          id="runtime-unavailable-title"
          className="mt-2 text-3xl font-semibold"
        >
          Runtime unavailable
        </h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Runtime configuration could not be loaded. Check the server connection
          and try again.
        </p>
      </section>
    );
  }

  if (dataUnavailable) {
    return (
      <section
        className="mx-auto max-w-5xl p-6"
        aria-labelledby="overview-data-unavailable-title"
      >
        <p className="text-sm font-medium text-muted-foreground">
          Actions Runtime
        </p>
        <h1
          id="overview-data-unavailable-title"
          className="mt-2 text-3xl font-semibold"
        >
          Overview data unavailable
        </h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Some Runtime data could not be loaded. The navigation remains
          available for supported capabilities.
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-5xl p-6" aria-labelledby="overview-title">
      <header className="mb-8">
        <p className="text-sm font-medium text-muted-foreground">
          Actions Runtime
        </p>
        <h1 id="overview-title" className="mt-2 text-3xl font-semibold">
          Overview
        </h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          See what is available in this Runtime and get to the work that
          matters.
        </p>
      </header>
      {loading ? (
        <p role="status" className="text-muted-foreground">
          Loading Runtime data…
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <Link
            to="/actions"
            className="rounded-xl border border-border p-5 transition-colors hover:bg-muted/50 focus-ring"
          >
            <h2 className="font-medium">Actions</h2>
            <p className="mt-2 text-2xl font-semibold">
              {loadedActions.data?.length ?? 0}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {loadedActions.data?.length
                ? "Available action packages"
                : "No actions available"}
            </p>
          </Link>
          <Link
            to="/runs"
            className="rounded-xl border border-border p-5 transition-colors hover:bg-muted/50 focus-ring"
          >
            <h2 className="font-medium">Runs</h2>
            <p className="mt-2 text-2xl font-semibold">
              {loadedRuns.data?.length ?? 0}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {loadedRuns.data?.length ? "Recent Runtime runs" : "No runs yet"}
            </p>
          </Link>
        </div>
      )}
    </section>
  );
};
