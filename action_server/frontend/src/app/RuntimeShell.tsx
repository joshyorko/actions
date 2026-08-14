import { BrowserRouter } from "react-router-dom";
import { RuntimeLayout } from "./RuntimeLayout";
import { RuntimeProviders } from "./RuntimeProviders";
import { RuntimeRoutes } from "./RuntimeRoutes";

export const RuntimeShell = () => (
  <RuntimeProviders>
    <BrowserRouter>
      <RuntimeLayout>
        <RuntimeRoutes />
      </RuntimeLayout>
    </BrowserRouter>
  </RuntimeProviders>
);
