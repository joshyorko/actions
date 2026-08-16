import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { RuntimeNavigation } from "./RuntimeNavigation";

export const RuntimeLayout = ({ children }: { children: ReactNode }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const hadMenuOpen = useRef(false);
  const location = useLocation();
  useEffect(() => {
    if (menuOpen) {
      window.setTimeout(() => {
        document
          .querySelector<HTMLButtonElement>('[aria-label="Close Runtime menu"]')
          ?.focus();
      }, 0);
    } else if (hadMenuOpen.current) menuButtonRef.current?.focus();
    hadMenuOpen.current = menuOpen;
  }, [menuOpen]);
  return (
    <div className="runtime-frame">
      <RuntimeNavigation menuOpen={menuOpen} onMenuChange={setMenuOpen} />
      <main className="runtime-main">
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
  );
};
