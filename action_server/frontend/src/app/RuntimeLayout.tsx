import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { RuntimeNavigation } from "./RuntimeNavigation";

export const RuntimeLayout = ({ children }: { children: ReactNode }) => {
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const location = useLocation();

  useEffect(() => {
    if (!mobileNavigationOpen) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileNavigationOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [mobileNavigationOpen]);

  useEffect(() => {
    setMobileNavigationOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileNavigationOpen) menuButtonRef.current?.focus();
  }, [mobileNavigationOpen]);

  return (
    <div className="flex min-h-screen bg-background">
      <div id="runtime-navigation">
        <RuntimeNavigation isMobileOpen={mobileNavigationOpen} />
      </div>
      {mobileNavigationOpen && (
        <button
          type="button"
          className="fixed inset-0 z-10 bg-black/20 md:hidden"
          aria-label="Close navigation"
          onClick={() => setMobileNavigationOpen(false)}
        />
      )}
      <main className="min-w-0 flex-1 overflow-auto">
        <button
          ref={menuButtonRef}
          type="button"
          className="m-3 rounded-md border border-border px-3 py-2 text-sm md:hidden"
          onClick={() => setMobileNavigationOpen(!mobileNavigationOpen)}
          aria-expanded={mobileNavigationOpen}
          aria-controls="runtime-navigation"
          aria-label={mobileNavigationOpen ? "Close menu" : "Open menu"}
        >
          {mobileNavigationOpen ? "Close" : "Menu"}
        </button>
        {children}
      </main>
    </div>
  );
};
