import { createRoot } from "react-dom/client";

const CanvasViewBoundary = () => (
    <main aria-labelledby="canvas-view-title">
        <h1 id="canvas-view-title">Canvas View</h1>
        <p>The independent Canvas View application boundary is ready.</p>
    </main>
);

const container = document.getElementById("root");

if (container) {
    createRoot(container).render(<CanvasViewBoundary />);
}
