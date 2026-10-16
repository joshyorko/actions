import { createRoot } from "react-dom/client";
import { McpCanvasView } from "./McpCanvasView";

const container = document.getElementById("root");

if (container) {
    createRoot(container).render(<McpCanvasView />);
}
