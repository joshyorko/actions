import type { ReactNode } from "react";
import { useState } from "react";
import { RuntimeNavigation } from "./RuntimeNavigation";

export const RuntimeLayout = ({ children }: { children: ReactNode }) => {
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  return (
    <div className="flex min-h-screen bg-background">
      <div id="runtime-navigation">
        <RuntimeNavigation isMobileOpen={mobileNavigationOpen} />
      </div>
      <main className="min-w-0 flex-1 overflow-auto">
        <button
          type="button"
          className="m-3 rounded-md border border-border px-3 py-2 text-sm md:hidden"
          onClick={() => setMobileNavigationOpen(!mobileNavigationOpen)}
          aria-expanded={mobileNavigationOpen}
          aria-controls="runtime-navigation"
        >
          Menu
        </button>
        {children}
      </main>
    </div>
  );
};
