import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { RuntimeNavigation } from "./RuntimeNavigation";

export const RuntimeLayout = ({ children }: { children: ReactNode }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const hadMenuOpen = useRef(false);
  const mainRef = useRef<HTMLElement>(null);
  const location = useLocation();
  useEffect(() => {
    if (menuOpen) {
      window.setTimeout(() => {
        document
          .querySelector<HTMLButtonElement>('[aria-label="Close Runtime menu"]')
          ?.focus();
      }, 0);
    } else if (hadMenuOpen.current) {
      window.setTimeout(() => menuButtonRef.current?.focus(), 20);
    }
    hadMenuOpen.current = menuOpen;
  }, [menuOpen]);
  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.toggleAttribute("inert", menuOpen);
      if (menuOpen) mainRef.current.setAttribute("aria-hidden", "true");
      else mainRef.current.removeAttribute("aria-hidden");
    }
  }, [menuOpen]);
  return (
    <div className="runtime-frame">
      <RuntimeNavigation menuOpen={menuOpen} onMenuChange={setMenuOpen} />
      <div className="runtime-content">
        <div className="mobile-toolbar">
          <button
            ref={menuButtonRef}
            type="button"
            className="menu-trigger"
            aria-label="Open Runtime menu"
            onClick={() => setMenuOpen(true)}
          >
            Menu
          </button>
          <Link to="/" className="mobile-brand">
            Actions Runtime
          </Link>
        </div>
        <main ref={mainRef} className="runtime-main">
          <nav className="breadcrumb-shell" aria-label="Breadcrumb">
            <Link to="/">Overview</Link>
            <span>/</span>
            <span>
              {location.pathname === "/"
                ? "Ready"
                : location.pathname.split("/")[1] || "Runtime"}
            </span>
          </nav>
          {children}
        </main>
      </div>
    </div>
  );
};
