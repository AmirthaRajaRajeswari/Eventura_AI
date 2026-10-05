import { useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bell, CircleDot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { sessionsApi } from "@/api/sessions";

const STATUS_LABELS: Record<string, string> = {
  created: "Created",
  planning: "Planning",
  researching: "Researching",
  budgeting: "Budgeting",
  negotiating: "Negotiating",
  reviewing: "Reviewing",
  awaiting_approval: "Awaiting approval",
  booking: "Booking",
  completed: "Completed",
  failed: "Failed",
  infeasible: "Infeasible",
  disrupted: "Disrupted",
};

const ACTIVE_STATUSES = [
  "planning",
  "researching",
  "budgeting",
  "negotiating",
  "reviewing",
  "booking",
];

const STATUS_DOTS: Record<string, string> = {
  created: "bg-[#aaa098]",
  planning: "bg-[#7c8e9b]",
  researching: "bg-[#6f9488]",
  budgeting: "bg-[#a48659]",
  negotiating: "bg-[#8b7890]",
  reviewing: "bg-[#77789a]",
  awaiting_approval: "bg-[#b28a4f]",
  booking: "bg-[#77789a]",
  completed: "bg-[#718467]",
  failed: "bg-[#a7625b]",
  infeasible: "bg-[#a7625b]",
  disrupted: "bg-[#a47752]",
};

function eventLabel(value?: string) {
  if (!value) return "New Event";

  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function providerLabel(value?: string) {
  if (!value) return "AI";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function ragLabel(value?: string) {
  if (value === "agentic") return "Agentic RAG";
  if (value === "basic") return "Basic RAG";
  if (value === "none") return "No RAG";
  return "Agentic RAG";
}

export default function TopNav() {
  const location = useLocation();

  if (location.pathname === "/events/new") {
    return null;
  }

  const { sessionId } = useParams<{ sessionId: string }>();

  const { data: session } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;

      const active =
        status &&
        ![
          "completed",
          "failed",
          "infeasible",
          "awaiting_approval",
        ].includes(status);

      return active ? 3000 : false;
    },
  });

  const status = session?.status;

  const statusLabel = status
    ? STATUS_LABELS[status] ?? status
    : null;

  const isActive = status
    ? ACTIVE_STATUSES.includes(status)
    : false;

  return (
    <header className="flex h-[68px] shrink-0 items-center justify-between border-b border-[#ded6cc] bg-[#f8f5ef]/95 px-7 backdrop-blur">
      <div className="flex min-w-0 items-center">
        {session && (
          <div className="min-w-0">
            <p className="truncate font-serif text-[19px] leading-none tracking-[-0.01em] text-[#2b2030]">
              {eventLabel(session.event_type)}
            </p>

            <p className="mt-1 text-[9px] uppercase tracking-[0.12em] text-[#a09891]">
              Event workspace
            </p>
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {session && statusLabel && (
          <div className="flex h-8 w-[112px] items-center justify-center gap-2 rounded-full border border-[#ded6cc] bg-white/70 px-3">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                STATUS_DOTS[status] ?? "bg-[#aaa098]"
              } ${isActive ? "animate-pulse" : ""}`}
            />

            <span className="text-[10px] font-medium text-[#625952]">
              {statusLabel}
            </span>
          </div>
        )}

        {session && (
          <div className="hidden h-8 w-[112px] items-center justify-center gap-2 rounded-full border border-[#ded6cc] bg-white/50 px-3 sm:flex">
            <CircleDot className="h-3 w-3 text-[#718467]" />

            <span className="text-[9px] font-medium uppercase tracking-[0.08em] text-[#756c65]">
              {providerLabel(session.llm_provider)}
            </span>
          </div>
        )}

        {session && (
          <div className="hidden h-8 w-[112px] items-center justify-center rounded-full border border-[#d9cdbd] bg-[#f1eadf] px-3 md:flex">
            <span className="text-[9px] font-semibold uppercase tracking-[0.08em] text-[#866a45]">
              {ragLabel(session.rag_mode)}
            </span>
          </div>
        )}

        {session?.awaiting_human && sessionId && (
          <Button
            size="sm"
            onClick={() => {
              window.location.href = `/events/${sessionId}/plan`;
            }}
            className="h-9 rounded-full bg-[#2b2030] px-4 text-[10px] font-medium uppercase tracking-[0.08em] text-white shadow-none hover:bg-[#3a2a40]"
          >
            <Bell className="mr-2 h-3.5 w-3.5 text-[#d0ad6e]" />
            Approval required
          </Button>
        )}
      </div>
    </header>
  );
}