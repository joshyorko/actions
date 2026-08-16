import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/shared/utils/cn";
import { useLocalStorage } from "@/shared/hooks/useLocalStorage";
import { useTheme } from "@/shared/hooks/useTheme";

const groups = [
  {
    label: "Workbench",
    items: [
      ["Overview", "/overview"],
      ["Actions", "/actions"],
    ],
  },
  {
    label: "Evidence",
    items: [
      ["Runs", "/runs"],
      ["Logs & artifacts", "/runs"],
    ],
  },
  {
    label: "Operations",
    items: [
      ["Schedules", "/schedules"],
      ["Robots", "/robots"],
      ["Work Items", "/work-items"],
    ],
  },
  { label: "Reference", items: [["Analytics", "/analytics"]] },
] as const;

export const RuntimeNavigation = () => {
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useLocalStorage(
    "sidebar-collapsed",
    false,
  );
  const [isMobileOpen, setMobileOpen] = useState(false);
  const { theme, cycleTheme } = useTheme();
  useEffect(() => {
    const close = (event: KeyboardEvent) =>
      event.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  return (
    <>
      <button
        type="button"
        className="runtime-mobile-menu"
        onClick={() => setMobileOpen(true)}
        aria-label="Open Runtime navigation"
      >
        <span aria-hidden="true">☰</span> Menu
      </button>
      {isMobileOpen && (
        <button
          type="button"
          className="runtime-mobile-scrim"
          aria-label="Close Runtime navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        className={cn(
          "sidebar flex flex-col border-r border-sidebar-border/50 transition-all duration-200",
          isCollapsed ? "w-16" : "w-64",
          isMobileOpen && "open",
        )}
      >
        <div
          className={cn(
            "flex h-16 items-center border-b border-sidebar-border/30",
            isCollapsed ? "justify-center px-2" : "justify-between px-4",
          )}
        >
          {!isCollapsed && (
            <span className="text-base font-semibold tracking-tight text-sidebar-foreground">
              Actions Runtime
            </span>
          )}
          <button
            type="button"
            onClick={cycleTheme}
            className="rounded-lg p-2 text-sidebar-foreground/70 hover:bg-sidebar-accent/20"
            aria-label={`Toggle theme (current: ${theme})`}
            title={`Theme: ${theme}`}
          >
            {theme === "dark" ? "☾" : theme === "light" ? "☀" : "◐"}
          </button>
        </div>
        <div
          className={cn(
            "flex py-2",
            isCollapsed ? "justify-center" : "justify-end px-3",
          )}
        >
          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="rounded-md px-2 py-1 text-sidebar-foreground/70 hover:bg-sidebar-accent/20"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? "→" : "←"}
          </button>
        </div>
        <nav
          className={cn("flex-1 space-y-1 py-2", isCollapsed ? "px-2" : "px-3")}
          aria-label="Runtime navigation"
        >
          {groups.map((group) => (
            <div key={group.label} className="mb-4">
              {!isCollapsed && (
                <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-sidebar-foreground/40">
                  {group.label}
                </p>
              )}
              {group.items.map(([label, path]) => (
                <Link
                  key={`${label}-${path}`}
                  to={path}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "sidebar-nav-item",
                    location.pathname.startsWith(path) && "active",
                    isCollapsed && "justify-center px-0",
                  )}
                  title={isCollapsed ? label : undefined}
                >
                  {!isCollapsed && label}
                </Link>
              ))}
            </div>
          ))}
          <button
            type="button"
            className="sidebar-nav-item w-full"
            onClick={() => window.open("/openapi.json", "_blank")}
            title={isCollapsed ? "OpenAPI spec" : undefined}
          >
            {!isCollapsed && "OpenAPI spec"}
          </button>
        </nav>
      </aside>
    </>
  );
};
