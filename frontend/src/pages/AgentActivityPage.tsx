import { useParams, Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, CheckCircle2, XCircle, Clock, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
  waiting: Clock,
};

const STATUS_COLOR: Record<string, string> = {
  success: "text-green-600",
  error: "text-destructive",
  running: "text-blue-600 animate-spin",
  waiting: "text-yellow-600",
};

const AGENT_COLORS: Record<string, string> = {
  IntakeAgent: "bg-purple-100 text-purple-800",
  FeasibilityAgent: "bg-orange-100 text-orange-800",
  PlannerAgent: "bg-blue-100 text-blue-800",
  ResearchAgent: "bg-teal-100 text-teal-800",
  BudgetAgent: "bg-green-100 text-green-800",
  NegotiatorAgent: "bg-yellow-100 text-yellow-800",
  CriticAgent: "bg-red-100 text-red-800",
  BookingAgent: "bg-indigo-100 text-indigo-800",
  System: "bg-gray-100 text-gray-700",
};

export default function AgentActivityPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) return;

    const url = `/api/v1/sessions/${sessionId}/stream`;
    const sse = new EventSource(url);

    sse.onopen = () => setConnected(true);

    sse.addEventListener("activity", (e) => {
      const data: ActivityEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, data]);
    });

    sse.onerror = () => {
      setConnected(false);
      sse.close();
    };

    return () => sse.close();
  }, [sessionId]);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link to={`/events/${sessionId}`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Dashboard
            </Link>
          </Button>
          <Separator orientation="vertical" className="h-5" />
          <h2 className="text-lg font-semibold">Agent Activity</h2>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              connected ? "bg-green-500 animate-pulse" : "bg-gray-400"
            )}
          />
          <span className="text-xs text-muted-foreground">
            {connected ? "Live" : "Disconnected"}
          </span>
        </div>
      </div>

      {/* Activity feed */}
      <Card className="h-[calc(100vh-14rem)]">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">
            Live Event Feed
            <span className="ml-2 font-normal text-muted-foreground">
              {events.length} events
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[calc(100vh-20rem)] px-4">
            {events.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-muted-foreground">
                <div className="text-center">
                  <Clock className="mx-auto mb-3 h-8 w-8 opacity-30" />
                  <p className="text-sm">
                    {connected
                      ? "Waiting for agent activity…"
                      : "Connect to a session to see activity"}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-1 py-2">
                {events.map((event) => (
                  <ActivityRow key={event.id} event={event} />
                ))}
                <div ref={bottomRef} />
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const StatusIcon = STATUS_ICON[event.status] ?? Clock;
  const agentColor = AGENT_COLORS[event.agent] ?? "bg-gray-100 text-gray-700";

  return (
    <div className="flex items-start gap-3 rounded-md px-2 py-2 hover:bg-muted/50">
      <StatusIcon
        className={cn("mt-0.5 h-4 w-4 shrink-0", STATUS_COLOR[event.status])}
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={cn("px-2 py-0 text-[10px] font-medium", agentColor)}>
            {event.agent}
          </Badge>
          <span className="text-sm font-medium">{event.action}</span>
        </div>
        {event.detail && (
          <p className="mt-0.5 text-xs text-muted-foreground">{event.detail}</p>
        )}
      </div>
      <time className="shrink-0 text-[10px] text-muted-foreground">
        {new Date(event.timestamp).toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}
      </time>
    </div>
  );
}
