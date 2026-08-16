import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ActionsPage } from "@/core/pages/Actions";
import { AnalyticsPage } from "@/core/pages/Analytics";
import { ArtifactsPage } from "@/core/pages/Artifacts";
import { LogsPage } from "@/core/pages/Logs";
import { RobotsPage } from "@/core/pages/Robots";
import { RunHistoryPage } from "@/core/pages/RunHistory";
import { SchedulesPage } from "@/core/pages/Schedules";
import { WorkItemsPage } from "@/core/pages/WorkItems";
import { OverviewPage } from "@/core/pages/Overview";
import { ActionDetailPage } from "@/core/pages/ActionDetail";
import { RunInspectionPage } from "@/core/pages/RunInspection";

export const RuntimeRoutes = () => {
  const location = useLocation();
  return (
    <div key={location.pathname} className="page-transition-wrapper h-full">
      <Routes location={location}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/actions" element={<ActionsPage />} />
        <Route path="/actions/:actionId" element={<ActionDetailPage />} />
        <Route path="/runs" element={<RunHistoryPage />} />
        <Route path="/runs/:runId" element={<RunInspectionPage />} />
        <Route path="/schedules" element={<SchedulesPage />} />
        <Route path="/robots" element={<RobotsPage />} />
        <Route path="/work-items" element={<WorkItemsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/logs/:runId" element={<LogsPage />} />
        <Route path="/artifacts/:runId" element={<ArtifactsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
};
