import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/toaster";
import Layout from "@/components/layout/Layout";
import NewEventPage from "@/pages/NewEventPage";
import DashboardPage from "@/pages/DashboardPage";
import AgentActivityPage from "@/pages/AgentActivityPage";
import PlanReviewPage from "@/pages/PlanReviewPage";
import DisruptionPage from "@/pages/DisruptionPage";
import EvalConsolePage from "@/pages/EvalConsolePage";

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/events/new" replace />} />
          <Route path="events/new" element={<NewEventPage />} />
          <Route path="events/:sessionId" element={<DashboardPage />} />
          <Route path="events/:sessionId/activity" element={<AgentActivityPage />} />
          <Route path="events/:sessionId/plan" element={<PlanReviewPage />} />
          <Route path="events/:sessionId/disrupt" element={<DisruptionPage />} />
          <Route path="eval" element={<EvalConsolePage />} />
        </Route>
      </Routes>
      <Toaster />
    </>
  );
}
