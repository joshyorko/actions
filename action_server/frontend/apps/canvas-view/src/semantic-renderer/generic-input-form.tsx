import { useState } from "react";
import type {
    GenericExecutionContext,
    createGenericExecutionAdapter,
} from "./generic-execution";
export function GenericInputForm({
    binding,
    controller,
}: {
    binding: GenericExecutionContext["inputBindings"][number];
    controller: ReturnType<typeof createGenericExecutionAdapter>;
}) {
    const [selected, setSelected] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);
    const page = controller.inputPages.get(binding.bindingId);
    const act = async (operation: () => Promise<unknown>) => {
        setBusy(true);
        setError(null);
        try {
            await operation();
        } catch {
            setError(
                "Input selection unavailable or changed. Refresh status before retrying an uncertain selection.",
            );
        } finally {
            setBusy(false);
        }
    };
    const load = (cursor: string | null = null) =>
        act(async () => {
            await controller.loadInputs(binding.bindingId, cursor);
            setSelected("");
        });
    return (
        <form
            className="semantic-form"
            aria-label={`Work Item input for ${binding.bindingId}`}
            onSubmit={(event) => {
                event.preventDefault();
                void act(async () => {
                    await controller.submitInput(binding.bindingId, selected);
                    setSelected("");
                });
            }}
        >
            <h3>Input for {binding.bindingId}</h3>
            <p>
                This action consumes the saved input of one selected Work Item.
                Form fields cannot replace it.
            </p>
            <p>Queue: {binding.queue.queue_id}</p>
            <button type="button" disabled={busy} onClick={() => void load()}>
                Load inputs
            </button>
            <label className="semantic-form__field">
                Input item
                <select
                    aria-label={`Input item for ${binding.bindingId}`}
                    value={selected}
                    disabled={busy}
                    onChange={(event) => setSelected(event.target.value)}
                >
                    <option value="">Select an input</option>
                    {page?.items.map((item) => (
                        <option
                            key={item.itemId}
                            value={item.itemId}
                            disabled={!item.selectable}
                        >
                            {item.itemId} — {item.state}
                        </option>
                    ))}
                </select>
            </label>
            {page?.items.length === 0 ? (
                <p>No input items in this page.</p>
            ) : null}
            {page?.nextCursor ? (
                <button
                    type="button"
                    disabled={busy}
                    onClick={() => void load(page.nextCursor)}
                >
                    Next inputs
                </button>
            ) : null}
            {selected ? (
                <pre>
                    {
                        page?.items.find((item) => item.itemId === selected)
                            ?.preview
                    }
                </pre>
            ) : null}
            {page?.items.find((item) => item.itemId === selected)
                ?.previewTruncated ? (
                <p>
                    Input preview truncated; the Run consumes the full saved
                    input.
                </p>
            ) : null}
            <button type="submit" disabled={busy || !selected}>
                Claim selected input
            </button>
            <p>
                Claiming prepares a Run. Choose Continue execution to launch it.
            </p>
            {error ? <p role="alert">{error}</p> : null}
        </form>
    );
}
