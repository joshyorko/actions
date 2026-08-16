import { Link, useLocation } from "react-router-dom";
import { cn } from "@/shared/utils/cn";
import { useLocalStorage } from "@/shared/hooks/useLocalStorage";
import { useTheme } from "@/shared/hooks/useTheme";

const primary = [
  ["Overview", "/"],
  ["Actions", "/actions"],
  ["Runs", "/runs"],
] as const;
const operations = [
  ["Schedules", "/schedules"],
  ["Robots", "/robots"],
  ["Work Items", "/work-items"],
] as const;

export const RuntimeNavigation = ({
  menuOpen = false,
  onMenuChange,
}: {
  menuOpen?: boolean;
  onMenuChange?: (open: boolean) => void;
}) => {
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useLocalStorage(
    "sidebar-collapsed",
    false,
  );
  const { theme, cycleTheme } = useTheme();
  const links = (items: readonly (readonly [string, string])[]) =>
    items.map(([label, path]) => (
      <Link
        key={path}
        to={path}
        onClick={() => onMenuChange?.(false)}
        className={cn(
          "sidebar-nav-item",
          location.pathname === path ||
            (path !== "/" && location.pathname.startsWith(path))
            ? "active"
            : "",
        )}
        aria-current={location.pathname === path ? "page" : undefined}
      >
        {label}
      </Link>
    ));
  return (
    <>
      <div
        data-testid="mobile-menu-backdrop"
        className={cn("menu-backdrop", menuOpen && "visible")}
        onClick={() => onMenuChange?.(false)}
      />
      <aside
        className={cn(
          "sidebar",
          menuOpen && "open",
          isCollapsed && "collapsed",
        )}
        onKeyDown={(event) => {
          if (event.key === "Escape") onMenuChange?.(false);
        }}
      >
        <div className="sidebar-head">
          <div>
            <p className="eyebrow">Local tool</p>
            <strong>Actions Runtime</strong>
          </div>
          <button
            type="button"
            className="menu-close"
            aria-label="Close Runtime menu"
            autoFocus={menuOpen}
            onClick={() => onMenuChange?.(false)}
          >
            ×
          </button>
          <button
            type="button"
            className="theme-toggle"
            onClick={cycleTheme}
            aria-label={`Toggle theme (current: ${theme})`}
          >
            {theme === "dark" ? "☾" : "☀"}
          </button>
        </div>
        <nav className="sidebar-nav" aria-label="Runtime navigation">
          <p className="nav-group-label">Primary</p>
          {links(primary)}
          <p className="nav-group-label">Operations</p>
          {links(operations)}
          <p className="nav-group-label">Reference</p>
          {links([["Analytics", "/analytics"]])}
          <button
            type="button"
            className="sidebar-nav-item"
            onClick={() => window.open("/openapi.json", "_blank")}
          >
            OpenAPI spec
          </button>
        </nav>
        <button
          type="button"
          className="collapse-toggle"
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? "→" : "Collapse"}
        </button>
      </aside>
    </>
  );
};
