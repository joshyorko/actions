import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ActionsPage } from "@/core/pages/Actions";
import { ArtifactsPage } from "@/core/pages/Artifacts";
import { LogsPage } from "@/core/pages/Logs";
import { RunHistoryPage } from "@/core/pages/RunHistory";
import { OverviewPage } from "@/core/pages/Overview";

export const RuntimeRoutes = () => {
  const location = useLocation();
  return (
    <div key={location.pathname} className="page-transition-wrapper h-full">
      <Routes location={location}>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/actions" element={<ActionsPage />} />
        <Route path="/runs" element={<RunHistoryPage />} />
        {/* Optional routes stay fail-closed until /config exposes capabilities. */}
        <Route
          path="/schedules"
          element={<Navigate to="/overview" replace />}
        />
        <Route path="/robots" element={<Navigate to="/overview" replace />} />
        <Route
          path="/work-items"
          element={<Navigate to="/overview" replace />}
        />
        <Route
          path="/analytics"
          element={<Navigate to="/overview" replace />}
        />
        <Route path="/logs/:runId" element={<LogsPage />} />
        <Route path="/artifacts/:runId" element={<ArtifactsPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </div>
  );
};
