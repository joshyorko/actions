import type { ReactNode } from "react";
import { RuntimeNavigation } from "./RuntimeNavigation";

export const RuntimeLayout = ({ children }: { children: ReactNode }) => (
  <div className="flex min-h-screen bg-background">
    <RuntimeNavigation />
    <main className="flex-1 overflow-auto">{children}</main>
  </div>
);
