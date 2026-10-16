import { BrowserRouter } from "react-router-dom";
import { RuntimeLayout } from "./RuntimeLayout";
import { RuntimeProviders } from "./RuntimeProviders";
import { RuntimeAuthentication } from "./RuntimeAuthentication";
import { RuntimeRoutes } from "./RuntimeRoutes";

export const RuntimeShell = () => (
    <RuntimeAuthentication>
        <RuntimeProviders>
            <BrowserRouter>
                <RuntimeLayout>
                    <RuntimeRoutes />
                </RuntimeLayout>
            </BrowserRouter>
        </RuntimeProviders>
    </RuntimeAuthentication>
);
