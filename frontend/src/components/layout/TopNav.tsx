import { useParams, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { sessionsApi } from "@/api/sessions";

const STATUS_LABELS: Record<string, { label: string; variant: "default" | "success" | "warning" | "destructive" | "info" | "outline" | "secondary" }> = {
  created: { label: "Created", variant: "secondary" },
  planning: { label: "Planning…", variant: "info" },
  researching: { label: "Researching…", variant: "info" },
  budgeting: { label: "Budgeting…", variant: "info" },
  negotiating: { label: "Negotiating…", variant: "info" },
  reviewing: { label: "Reviewing…", variant: "info" },
  awaiting_approval: { label: "Awaiting Approval", variant: "warning" },
  booking: { label: "Booking…", variant: "info" },
  completed: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  infeasible: { label: "Infeasible", variant: "destructive" },
  disrupted: { label: "Disrupted", variant: "warning" },
};

export default function TopNav() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const location = useLocation();

  const { data: session } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const active = status && !["completed", "failed", "infeasible", "awaiting_approval"].includes(status);
      return active ? 3000 : false;
    },
  });

  const statusInfo = session ? (STATUS_LABELS[session.status] ?? { label: session.status, variant: "secondary" as const }) : null;

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-muted-foreground">
          Eventura AI — Agentic Event Planning
        </h1>
        {session && statusInfo && (
          <>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm font-medium">
              {session.event_type
                ? session.event_type.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
                : "New Event"}
            </span>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        {session && statusInfo && (
          <Badge variant={statusInfo.variant} className="gap-1.5">
            {["planning","researching","budgeting","negotiating","reviewing","booking"].includes(session.status) && (
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
            )}
            {statusInfo.label}
          </Badge>
        )}

        {session && (
          <Badge variant="outline" className="gap-1 text-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
            {session.llm_provider.charAt(0).toUpperCase() + session.llm_provider.slice(1)}
          </Badge>
        )}

        <Badge variant="info" className="text-xs">
          {session?.rag_mode === "agentic" ? "Agentic RAG" : session?.rag_mode === "basic" ? "Basic RAG" : session?.rag_mode === "none" ? "No RAG" : "Agentic RAG"}
        </Badge>

        {session?.awaiting_human && (
          <Button variant="default" size="sm" className="animate-pulse gap-1.5" onClick={() => {
            if (sessionId) window.location.href = `/events/${sessionId}/plan`;
          }}>
            <Bell className="h-3.5 w-3.5" />
            Approval Required
          </Button>
        )}
      </div>
    </header>
  );
}
