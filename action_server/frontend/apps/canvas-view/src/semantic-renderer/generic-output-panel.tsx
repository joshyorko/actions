import { useState } from "react";
import type {
    GenericExecutionContext,
    createGenericExecutionAdapter,
} from "./generic-execution";
export function GenericOutputPanel({
    binding,
    controller,
}: {
    binding: GenericExecutionContext["outputBindings"][number];
    controller: ReturnType<typeof createGenericExecutionAdapter>;
}) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const page = controller.outputPages.get(binding.bindingId);
    const load = async (cursor: string | null = null) => {
        setBusy(true);
        setError(null);
        try {
            await controller.loadOutputs(binding.bindingId, cursor);
        } catch {
            setError(
                "Produced items unavailable or changed. Refresh the Run before continuing.",
            );
        } finally {
            setBusy(false);
        }
    };
    return (
        <section aria-label={`Produced Work Items for ${binding.bindingId}`}>
            <h3>Produced Work Items</h3>
            <p>
                Read-only output items from this Run. Queue:{" "}
                {binding.queue.queue_id}
            </p>
            <button type="button" disabled={busy} onClick={() => void load()}>
                Load produced items
            </button>
            {page?.items.length === 0 ? (
                <p>No Work Items were produced.</p>
            ) : null}
            {page?.items.map((item) => (
                <article key={item.itemId}>
                    <p>
                        {item.itemId} — {item.queueState}
                    </p>
                    {item.cancelRequested ? (
                        <p>Cancellation requested</p>
                    ) : null}
                    {item.parentId ? (
                        <p>Parent input: {item.parentId}</p>
                    ) : null}
                    <pre>{item.preview}</pre>
                    {item.previewTruncated ? (
                        <p>Output preview truncated.</p>
                    ) : null}
                </article>
            ))}
            {page?.nextCursor ? (
                <button
                    type="button"
                    disabled={busy}
                    onClick={() => void load(page.nextCursor)}
                >
                    Next produced items
                </button>
            ) : null}
            {error ? <p role="alert">{error}</p> : null}
        </section>
    );
}
