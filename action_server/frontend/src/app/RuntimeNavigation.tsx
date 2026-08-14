import { Link, useLocation } from "react-router-dom";
import { cn } from "@/shared/utils/cn";
import { useLocalStorage } from "@/shared/hooks/useLocalStorage";
import { useTheme } from "@/shared/hooks/useTheme";

const items = [
  ["Overview", "/overview", "overview"],
  ["Actions", "/actions", "actions"],
  ["Runs", "/runs", "runs"],
  ["Schedules", "/schedules", "schedules"],
  ["Robots", "/robots", "robots"],
  ["Work Items", "/work-items", "work_items"],
  ["Analytics", "/analytics", "analytics"],
] as const;

export const RuntimeNavigation = ({
  isMobileOpen = false,
}: {
  isMobileOpen?: boolean;
}) => {
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useLocalStorage(
    "sidebar-collapsed",
    false,
  );
  const { theme, cycleTheme } = useTheme();
  const visibleItems = items.filter(([, , capability]) => {
    if (capability === "overview") return true;
    return capability === "actions" || capability === "runs";
  });
  return (
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
          <span className="text-base font-semibold text-sidebar-foreground">
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
        {visibleItems.map(([label, path]) => (
          <Link
            key={path}
            to={path}
            className={cn(
              "sidebar-nav-item sidebar-nav-item-lg",
              location.pathname.startsWith(path) && "active",
              isCollapsed && "justify-center px-0",
            )}
            title={isCollapsed ? label : undefined}
          >
            {!isCollapsed && label}
          </Link>
        ))}
        <button
          type="button"
          className="sidebar-nav-item sidebar-nav-item-lg w-full"
          onClick={() => window.open("/openapi.json", "_blank")}
          title={isCollapsed ? "OpenAPI spec" : undefined}
        >
          {!isCollapsed && "OpenAPI spec"}
        </button>
      </nav>
    </aside>
  );
};
