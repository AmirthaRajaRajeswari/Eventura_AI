import { useParams, Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock3,
  Loader2,
  Radio,
  Sparkles,
  XCircle,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface ActivityEvent {
  id: string;
  session_id: string;
  agent: string;
  action: string;
  status: "success" | "error" | "running" | "waiting";
  detail: string | null;
  timestamp: string;
}

const STATUS_ICON: Record<string, React.ElementType> = {
  success: CheckCircle2,
  error: XCircle,
  running: Loader2,
  waiting: Clock3,
};

const STATUS_LABEL: Record<string, string> = {
  success: "Completed",
  error: "Needs attention",
  running: "Working",
  waiting: "Waiting",
};

const AGENT_META: Record<
  string,
  {
    label: string;
    short: string;
    bg: string;
    text: string;
    dot: string;
  }
> = {
  IntakeAgent: {
    label: "Intake",
    short: "INT",
    bg: "bg-[#eee7f2]",
    text: "text-[#765b7f]",
    dot: "bg-[#8b6b96]",
  },
  FeasibilityAgent: {
    label: "Feasibility",
    short: "FEA",
    bg: "bg-[#f3eadf]",
    text: "text-[#906c47]",
    dot: "bg-[#b18455]",
  },
  PlannerAgent: {
    label: "Planner",
    short: "PLN",
    bg: "bg-[#e8edf2]",
    text: "text-[#536b7c]",
    dot: "bg-[#70899c]",
  },
  ResearchAgent: {
    label: "Research",
    short: "RES",
    bg: "bg-[#e5f0ed]",
    text: "text-[#557c72]",
    dot: "bg-[#6d9b8d]",
  },
  BudgetAgent: {
    label: "Budget",
    short: "BUD",
    bg: "bg-[#e9f0e5]",
    text: "text-[#65785d]",
    dot: "bg-[#7e9674]",
  },
  NegotiatorAgent: {
    label: "Negotiator",
    short: "NEG",
    bg: "bg-[#f3ede0]",
    text: "text-[#8a7148]",
    dot: "bg-[#ae8e5b]",
  },
  CriticAgent: {
    label: "Critic",
    short: "CHK",
    bg: "bg-[#f3e8e6]",
    text: "text-[#8e5f59]",
    dot: "bg-[#ad7168]",
  },
  BookingAgent: {
    label: "Booking",
    short: "BKG",
    bg: "bg-[#e9e8f1]",
    text: "text-[#65647f]",
    dot: "bg-[#77769a]",
  },
  System: {
    label: "Eventura",
    short: "SYS",
    bg: "bg-[#ece9e5]",
    text: "text-[#68625d]",
    dot: "bg-[#858078]",
  },
};

function getAgentMeta(agent: string) {
  return (
    AGENT_META[agent] ?? {
      label: agent.replace("Agent", ""),
      short: "AI",
      bg: "bg-[#ece9e5]",
      text: "text-[#68625d]",
      dot: "bg-[#858078]",
    }
  );
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    success: "text-[#718467]",
    error: "text-[#a45f58]",
    running: "text-[#75657e]",
    waiting: "text-[#a17b46]",
  };

  return colors[status] ?? "text-[#817870]";
}

function formatTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatRelativeTime(timestamp: string) {
  const diff = Math.max(
    0,
    Date.now() - new Date(timestamp).getTime()
  );

  const seconds = Math.floor(diff / 1000);

  if (seconds < 10) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);

  if (minutes < 60) return `${minutes}m ago`;

  return formatTime(timestamp);
}

export default function AgentActivityPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) return;

    const url = `/api/v1/sessions/${sessionId}/stream`;
    const sse = new EventSource(url);

    sse.onopen = () => {
      setConnected(true);
    };

    sse.addEventListener("activity", (e) => {
      const data: ActivityEvent = JSON.parse(e.data);

      setEvents((prev) => [...prev, data]);
    });

    sse.onerror = () => {
      setConnected(false);
      sse.close();
    };

    return () => {
      sse.close();
    };
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [events]);

  const runningEvents = events.filter(
    (event) => event.status === "running"
  );

  const completedEvents = events.filter(
    (event) => event.status === "success"
  );

  const latestEvent = events[events.length - 1];

  const activeAgents = Array.from(
    new Set(
      runningEvents.map((event) => event.agent)
    )
  );

  return (
    <div className="min-h-full bg-[#f8f5ef] text-[#2b2030]">
      <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">

        {/* ─────────────────────────────────────
            HEADER
        ───────────────────────────────────── */}

        <section className="relative overflow-hidden rounded-[28px] bg-[#2b2030] px-6 py-7 text-white shadow-[0_18px_50px_rgba(43,32,48,0.14)] sm:px-9 sm:py-9">
          <div className="absolute -right-20 -top-28 h-72 w-72 rounded-full border border-[#d0ad6e]/20" />
          <div className="absolute -right-4 -top-12 h-48 w-48 rounded-full border border-[#d0ad6e]/10" />

          <div className="relative flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <Link
                to={`/events/${sessionId}`}
                className="mb-5 inline-flex items-center text-xs text-white/50 transition-colors hover:text-white/80"
              >
                <ArrowLeft className="mr-2 h-3.5 w-3.5" />
                Back to event
              </Link>

              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#d0ad6e]">
                <Sparkles className="h-3.5 w-3.5" />
                Eventura Planning Studio
              </div>

              <h1 className="mt-3 font-serif text-4xl leading-tight text-[#fffdf9] sm:text-5xl">
                Behind the plan
              </h1>

              <p className="mt-3 max-w-xl text-sm leading-6 text-white/55">
                Watch Eventura's planning team research, reason,
                negotiate and validate your event in real time.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "h-2 w-2 rounded-full",
                      connected
                        ? "animate-pulse bg-emerald-400"
                        : "bg-white/30"
                    )}
                  />

                  <span className="text-xs font-medium text-white/75">
                    {connected
                      ? "Live planning feed"
                      : "Feed disconnected"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ─────────────────────────────────────
            OVERVIEW
        ───────────────────────────────────── */}

        <section className="mt-5 grid gap-3 sm:grid-cols-3">
          <OverviewCard
            icon={Activity}
            label="Activity events"
            value={events.length}
          />

          <OverviewCard
            icon={CheckCircle2}
            label="Completed actions"
            value={completedEvents.length}
          />

          <OverviewCard
            icon={Zap}
            label="Agents working"
            value={activeAgents.length}
          />
        </section>

        {/* ─────────────────────────────────────
            CURRENT ACTIVITY
        ───────────────────────────────────── */}

        {latestEvent && (
          <section className="mt-6 rounded-[22px] border border-[#ddd4c9] bg-white p-5 shadow-[0_8px_30px_rgba(64,48,40,0.04)]">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#f1ece5]">
                  <Radio className="h-4 w-4 text-[#8b6b45]" />
                </div>

                <div>
                  <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#a77b3d]">
                    Latest activity
                  </p>

                  <p className="mt-0.5 text-sm font-medium text-[#332a30]">
                    {latestEvent.action}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {activeAgents.length > 0 ? (
                  activeAgents.map((agent) => {
                    const meta = getAgentMeta(agent);

                    return (
                      <span
                        key={agent}
                        className={cn(
                          "rounded-full px-3 py-1.5 text-[10px] font-medium",
                          meta.bg,
                          meta.text
                        )}
                      >
                        {meta.label}
                      </span>
                    );
                  })
                ) : (
                  <span className="text-[10px] text-[#938981]">
                    {formatRelativeTime(latestEvent.timestamp)}
                  </span>
                )}
              </div>
            </div>
          </section>
        )}

        {/* ─────────────────────────────────────
            ACTIVITY WORKSPACE
        ───────────────────────────────────── */}

        <section className="mt-7 grid gap-7 lg:grid-cols-[minmax(0,1fr)_260px]">

          {/* TIMELINE */}
          <div className="min-w-0 overflow-hidden rounded-[26px] border border-[#ddd4c9] bg-white shadow-[0_10px_35px_rgba(64,48,40,0.04)]">

            <div className="flex items-center justify-between border-b border-[#eee8df] px-5 py-5 sm:px-6">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#a77b3d]">
                  Live timeline
                </p>

                <h2 className="mt-1 font-serif text-2xl text-[#2b2030]">
                  Planning activity
                </h2>
              </div>

              <span className="rounded-full bg-[#f3eee7] px-3 py-1.5 text-[10px] text-[#776d65]">
                {events.length} events
              </span>
            </div>

            <ScrollArea className="h-[calc(100vh-25rem)] min-h-[480px]">
              <div className="px-5 py-5 sm:px-7">
                {events.length === 0 ? (
                  <EmptyActivityState connected={connected} />
                ) : (
                  <div className="relative">
                    <div className="absolute bottom-0 left-[19px] top-3 w-px bg-[#e8e1d8]" />

                    <div className="space-y-1">
                      {events.map((event, index) => (
                        <ActivityRow
                          key={`${event.id}-${index}`}
                          event={event}
                        />
                      ))}

                      <div ref={bottomRef} />
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>

          {/* AGENT TEAM */}
          <aside className="space-y-4">
            <div className="rounded-[24px] border border-[#ddd4c9] bg-[#f1ede6] p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#2b2030] text-[#d0ad6e]">
                  <Bot className="h-5 w-5" />
                </div>

                <div>
                  <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#a77b3d]">
                    Planning team
                  </p>

                  <h3 className="font-serif text-xl text-[#2b2030]">
                    Your AI team
                  </h3>
                </div>
              </div>

              <p className="mt-4 text-xs leading-5 text-[#776d65]">
                Each specialist handles a different part of
                your event, while the workflow coordinates
                their decisions.
              </p>
            </div>

            <div className="rounded-[24px] border border-[#ddd4c9] bg-white p-4">
              <div className="space-y-1">
                {Object.entries(AGENT_META)
                  .filter(([agent]) => agent !== "System")
                  .map(([agent, meta]) => {
                    const isActive = activeAgents.includes(agent);

                    const hasEvents = events.some(
                      (event) => event.agent === agent
                    );

                    return (
                      <div
                        key={agent}
                        className={cn(
                          "flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors",
                          isActive
                            ? "bg-[#f6f1e9]"
                            : "hover:bg-[#faf8f4]"
                        )}
                      >
                        <div
                          className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-full text-[8px] font-bold",
                            meta.bg,
                            meta.text
                          )}
                        >
                          {meta.short}
                        </div>

                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-[#443a40]">
                            {meta.label}
                          </p>

                          <p className="mt-0.5 text-[9px] text-[#9a9088]">
                            {isActive
                              ? "Working now"
                              : hasEvents
                              ? "Completed a task"
                              : "Standing by"}
                          </p>
                        </div>

                        <span
                          className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            isActive
                              ? "animate-pulse bg-[#a77b3d]"
                              : hasEvents
                              ? "bg-[#8a9b81]"
                              : "bg-[#d2cbc3]"
                          )}
                        />
                      </div>
                    );
                  })}
              </div>
            </div>

            <div className="rounded-[24px] border border-[#ddd4c9] bg-[#2b2030] p-5 text-white">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10">
                  <Sparkles className="h-4 w-4 text-[#d0ad6e]" />
                </div>

                <p className="text-xs font-medium text-white/80">
                  Why this matters
                </p>
              </div>

              <p className="mt-4 text-xs leading-5 text-white/50">
                Eventura doesn't simply generate one answer.
                Agents research evidence, challenge the plan,
                negotiate constraints and pass decisions
                through the workflow.
              </p>
            </div>
          </aside>
        </section>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   ACTIVITY ROW
───────────────────────────────────────────── */

function ActivityRow({
  event,
}: {
  event: ActivityEvent;
}) {
  const StatusIcon =
    STATUS_ICON[event.status] ?? Clock3;

  const meta = getAgentMeta(event.agent);

  return (
    <div className="group relative flex gap-4 rounded-2xl px-1 py-3 transition-colors hover:bg-[#faf8f4]">
      <div className="relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[#e4ddd4] bg-white">
        <StatusIcon
          className={cn(
            "h-4 w-4",
            STATUS_ICON[event.status] === Loader2 &&
              event.status === "running" &&
              "animate-spin",
            getStatusColor(event.status)
          )}
        />
      </div>

      <div className="min-w-0 flex-1 pb-1">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "rounded-full px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.08em]",
                meta.bg,
                meta.text
              )}
            >
              {meta.label}
            </span>

            <span className="text-[9px] uppercase tracking-[0.1em] text-[#a19891]">
              {STATUS_LABEL[event.status] ?? event.status}
            </span>
          </div>

          <time
            className="shrink-0 text-[9px] tabular-nums text-[#aaa19a]"
            title={new Date(event.timestamp).toLocaleString("en-IN")}
          >
            {formatRelativeTime(event.timestamp)}
          </time>
        </div>

        <p className="mt-2 text-sm font-medium leading-5 text-[#383039]">
          {event.action}
        </p>

        {event.detail && (
          <p className="mt-1 max-w-3xl text-xs leading-5 text-[#837a73]">
            {event.detail}
          </p>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   OVERVIEW CARD
───────────────────────────────────────────── */

function OverviewCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-4 rounded-[20px] border border-[#ded6cc] bg-white px-5 py-4">
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#f1ece5]">
        <Icon className="h-4 w-4 text-[#8b6b45]" />
      </div>

      <div>
        <p className="font-serif text-2xl text-[#2b2030]">
          {value}
        </p>

        <p className="text-[9px] font-medium uppercase tracking-[0.13em] text-[#958b83]">
          {label}
        </p>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   EMPTY STATE
───────────────────────────────────────────── */

function EmptyActivityState({
  connected,
}: {
  connected: boolean;
}) {
  return (
    <div className="flex min-h-[440px] items-center justify-center">
      <div className="max-w-sm text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#f1ece5]">
          {connected ? (
            <Radio className="h-6 w-6 animate-pulse text-[#8b6b45]" />
          ) : (
            <Clock3 className="h-6 w-6 text-[#9b9189]" />
          )}
        </div>

        <h3 className="mt-5 font-serif text-2xl text-[#2b2030]">
          {connected
            ? "The planning team is ready"
            : "Waiting for the planning feed"}
        </h3>

        <p className="mt-2 text-sm leading-6 text-[#817870]">
          {connected
            ? "As Eventura's agents work, their decisions and progress will appear here in real time."
            : "Connect to an active planning session to see agent activity."}
        </p>

        {connected && (
          <div className="mt-6 flex justify-center gap-1.5">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#a77b3d]" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#a77b3d] [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#a77b3d] [animation-delay:300ms]" />
          </div>
        )}
      </div>
    </div>
  );
}