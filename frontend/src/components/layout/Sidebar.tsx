import { NavLink, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  Activity,
  FlaskConical,
  Settings,
  Sparkles,
  CalendarDays,
  Zap,
  LayoutDashboard,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { sessionsApi } from "@/api/sessions";

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-500",
  awaiting_approval: "bg-yellow-500",
  planning: "bg-blue-500",
  failed: "bg-red-500",
  disrupted: "bg-orange-500",
};

export default function Sidebar() {
  const navigate = useNavigate();

  const { data: sessionsData } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => sessionsApi.list(),
    refetchInterval: 5000,
  });

  const sessions = sessionsData?.sessions?.slice(0, 8) ?? [];

  return (
    <aside className="flex w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex items-center gap-2 px-6 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-eventura-600">
          <Sparkles className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold leading-none">Eventura AI</p>
          <p className="text-[10px] text-muted-foreground">Agentic Event Planning</p>
        </div>
      </div>

      <Separator />

      <div className="px-4 py-3">
        <Button className="w-full justify-start gap-2" size="sm" onClick={() => navigate("/events/new")}>
          <Plus className="h-4 w-4" />
          New Event
        </Button>
      </div>

      {/* Recent sessions */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Recent Events
        </p>
        <div className="space-y-0.5">
          {sessions.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground italic">No events yet</p>
          ) : (
            sessions.map((s) => (
              <NavLink
                key={s.id}
                to={`/events/${s.id}`}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-xs transition-colors",
                    isActive
                      ? "bg-accent text-accent-foreground font-medium"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )
                }
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 shrink-0 rounded-full",
                    STATUS_COLORS[s.status] ?? "bg-gray-400"
                  )}
                />
                <span className="truncate">
                  {s.event_type
                    ? s.event_type.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
                    : "New Event"}
                </span>
                <span className="ml-auto shrink-0 font-mono text-[9px] opacity-50">
                  {s.id.slice(0, 6)}
                </span>
              </NavLink>
            ))
          )}
        </div>
      </nav>

      <Separator />

      {/* Bottom nav */}
      <nav className="px-3 py-3 space-y-0.5">
        <NavLink
          to="/eval"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-accent text-accent-foreground font-medium"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )
          }
        >
          <FlaskConical className="h-4 w-4" />
          Evaluation
        </NavLink>
      </nav>

      <div className="border-t px-4 py-3">
        <p className="text-[10px] leading-tight text-muted-foreground">
          Demo vendor and pricing data are synthetic and used for demonstration purposes only.
        </p>
      </div>
    </aside>
  );
}
