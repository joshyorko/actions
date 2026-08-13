import { Link, useLocation } from "react-router-dom";
import { cn } from "@/shared/utils/cn";

const items = [
  ["Actions", "/actions"],
  ["Runs", "/runs"],
  ["Schedules", "/schedules"],
  ["Robots", "/robots"],
  ["Work Items", "/work-items"],
  ["Analytics", "/analytics"],
] as const;

export const RuntimeNavigation = () => {
  const location = useLocation();
  return (
    <aside className="sidebar flex w-64 flex-col border-r border-sidebar-border/50">
      <div className="flex h-16 items-center border-b border-sidebar-border/30 px-4 text-base font-semibold text-sidebar-foreground">
        Action Server
      </div>
      <nav
        className="flex-1 space-y-1 px-3 py-2"
        aria-label="Runtime navigation"
      >
        {items.map(([label, path]) => (
          <Link
            key={path}
            to={path}
            className={cn(
              "sidebar-nav-item sidebar-nav-item-lg",
              location.pathname.startsWith(path) && "active",
            )}
          >
            {label}
          </Link>
        ))}
        <button
          type="button"
          className="sidebar-nav-item sidebar-nav-item-lg w-full"
          onClick={() => window.open("/openapi.json", "_blank")}
        >
          OpenAPI spec
        </button>
      </nav>
    </aside>
  );
};
