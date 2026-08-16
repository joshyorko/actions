import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useActionRunMutation } from "@/queries/actions";
import { useActionServerContext } from "@/shared/context/actionServerContext";
import { formDataToPayload, propertiesToFormData } from "@/shared/utils/formData";
import { ErrorBanner } from "@/core/components/ui/ErrorBanner";
import { Loading } from "@/core/components/ui/Loading";

export const ActionDetailPage = () => {
  const { actionId } = useParams();
  const navigate = useNavigate();
  const { loadedActions, loadedRuns } = useActionServerContext();
  const { mutateAsync: runAction, isPending } = useActionRunMutation();
  const [values, setValues] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const packages = loadedActions.data ?? [];
  const pkg = packages.find((item) => item.actions.some((action) => action.id === actionId));
  const action = pkg?.actions.find((item) => item.id === actionId);
  const fields = useMemo(() => {
    if (!action?.input_schema) return [];
    try {
      return propertiesToFormData(JSON.parse(action.input_schema));
    } catch {
      return [];
    }
  }, [action]);
  const runs = (loadedRuns.data ?? [])
    .filter((run) => run.action_id === actionId)
    .sort((a, b) => b.numbered_id - a.numbered_id);

  if (loadedActions.isPending) return <Loading text="Loading action…" />;
  if (!action || !pkg) {
    return <div className="workbench-page"><p className="eyebrow">Actions / missing</p><h1>Action not found</h1><Link className="text-link" to="/actions">Back to Actions</Link></div>;
  }

  const run = async (event: FormEvent) => {
    event.preventDefault();
    setFailure(null);
    setFeedback(null);
    try {
      const formData = fields.map((field) => ({
        ...field,
        value: values[field.name] ?? String(field.value ?? ""),
      }));
      const result = await runAction({
        actionPackageName: pkg.name,
        actionName: action.name,
        args: formDataToPayload(formData),
      });
      if (!result.runId) {
        setFailure("The runtime accepted the request but did not return a run ID.");
        return;
      }
      setFeedback(`Run started: ${result.runId}`);
      navigate(`/runs/${result.runId}`);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "The runtime could not start this action.");
    }
  };

  return (
    <div className="workbench-page">
      <nav className="breadcrumb" aria-label="Breadcrumb"><Link to="/actions">Actions</Link><span>/</span><span>{pkg.name}</span><span>/</span><strong>{action.name}</strong></nav>
      <header className="workbench-header action-header"><div><p className="eyebrow">{pkg.name} · {action.file}:{action.lineno}</p><h1>{action.name}</h1><p className="lede">{action.docs || "No description supplied."}</p></div></header>
      <div className="workbench-tabs" aria-label="Action views">
        <a className="selected" href="#run">Run</a><a href="#documentation">Documentation</a><a href="#history">History</a>
      </div>
      <section id="run" className="workbench-section">
        <div className="section-heading"><div><p className="eyebrow">Input</p><h2>Run this action</h2></div><span className="mono">POST /api/actions/{pkg.name}/{action.name}/run</span></div>
        <form className="schema-form" onSubmit={run}>
          {fields.length ? fields.map((field) => <label className="schema-field" key={field.name}><span>{field.title || field.name}{field.required ? " *" : ""}</span><input aria-label={field.title || field.name} required={field.required} value={values[field.name] ?? String(field.value ?? "")} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))} /></label>) : <pre className="code-panel">{action.input_schema || "No input schema supplied."}</pre>}
          {failure && <ErrorBanner message={failure} />}
          {feedback && <p className="run-feedback" role="status">{feedback}</p>}
          <button className="button-primary" type="submit" disabled={isPending || !action.enabled}>{isPending ? "Starting…" : "Run action"}</button>
        </form>
      </section>
      <section id="documentation" className="workbench-section"><p className="eyebrow">Documentation</p><h2>What this action does</h2><p className="prose">{action.docs || "Documentation is not available for this action."}</p><div className="code-panel"><p className="eyebrow">Input schema</p><pre>{action.input_schema}</pre></div></section>
      <section id="history" className="workbench-section"><div className="section-heading"><div><p className="eyebrow">History</p><h2>Recent runs</h2></div><Link to={`/runs?search=${encodeURIComponent(action.name)}`} className="text-link">Open global history</Link></div>{runs.length ? <div className="object-list">{runs.slice(0, 5).map((item) => <Link className="object-row" to={`/runs/${item.id}`} key={item.id}><span><strong>Run #{item.numbered_id}</strong><small className="mono">{item.run_time ? `${item.run_time.toFixed(2)} s` : "In progress"}</small></span><span className="status">{item.status === 3 ? "Failed" : item.status === 2 ? "Passed" : "Running"}</span></Link>)}</div> : <div className="empty-frame"><h3>No runs yet</h3><p>Run the action to create the first evidence trail.</p></div>}</section>
    </div>
  );
};
