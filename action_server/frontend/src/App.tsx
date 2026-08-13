import { RuntimeShell } from './app/RuntimeShell';
import { RuntimeRoutes } from './app/RuntimeRoutes';

// RuntimeRoutes is exported as a feature boundary; RuntimeShell composes it
// with the shared provider and browser shell.
export const App = RuntimeShell;

export { RuntimeRoutes };
