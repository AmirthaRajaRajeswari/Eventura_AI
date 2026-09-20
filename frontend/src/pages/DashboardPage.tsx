import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, Calendar, Users, Wallet, Clock, ArrowRight,
  CheckCircle2, AlertTriangle, XCircle, TrendingDown, Zap,
} from "lucide-react";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { sessionsApi, type SessionOut, type VendorSelection } from "@/api/sessions";
import { formatINR, formatDate } from "@/lib/utils";

const CATEGORY_COLORS: Record<string, string> = {
  venue: "#6366f1", catering: "#10b981", decoration: "#f59e0b",
  photography: "#3b82f6", makeup: "#ec4899", music: "#8b5cf6",
  ritual_services: "#14b8a6", transport: "#f97316",
  cake: "#e11d48", entertainer: "#06b6d4", sound_lights: "#a855f7",
  stage: "#84cc16", performers: "#eab308", permissions_security: "#64748b",
  banners_printing: "#78716c",
};

export default function DashboardPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const { data: session, isLoading } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !["completed","failed","infeasible","awaiting_approval"].includes(status) ? 3000 : false;
    },
  });

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (!session) {
    return <div className="text-muted-foreground text-sm p-8">Session not found</div>;
  }

  const req = session.requirements as Record<string, unknown> | undefined;
  const budget = req?.budget as number | undefined;
  const budgetSummary = session.budget_summary;

  // Budget pie chart data
  const pieData = Object.entries(session.vendor_selections.reduce((acc, sel) => {
    const price = sel.final_price ?? sel.quoted_price;
    acc[sel.category] = (acc[sel.category] ?? 0) + price;
    return acc;
  }, {} as Record<string, number>)).map(([name, value]) => ({ name, value }));

  // Negotiation savings bar data
  const savingsData = session.negotiation_logs
    .filter((n) => n.savings > 0)
    .map((n) => ({ name: n.category, savings: n.savings }));

  const lastCritic = session.critic_feedback[session.critic_feedback.length - 1];
  const highIssues = lastCritic?.issues?.filter((i) => i.severity === "high") ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            {req?.event_type
              ? String(req.event_type).replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
              : "Event Dashboard"}
          </h2>
          <p className="text-sm text-muted-foreground">
            Session {sessionId?.slice(0, 8)}… · {session.rag_mode.toUpperCase()} RAG
          </p>
        </div>
        <div className="flex items-center gap-2">
          {session.awaiting_human && (
            <Button size="sm" asChild className="gap-1.5 animate-pulse">
              <Link to={`/events/${sessionId}/plan`}>
                <AlertTriangle className="h-4 w-4" />
                Review Plan
              </Link>
            </Button>
          )}
          <Button variant="outline" size="sm" asChild>
            <Link to={`/events/${sessionId}/activity`}>
              <Activity className="mr-2 h-4 w-4" />
              Agent Activity
            </Link>
          </Button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Calendar}
          label="Event Date"
          value={req?.date ? formatDate(String(req.date)) : "—"}
        />
        <StatCard
          icon={Users}
          label="Guests"
          value={req?.guest_count ? `${Number(req.guest_count).toLocaleString()}` : "—"}
        />
        <StatCard
          icon={Wallet}
          label="Budget"
          value={budget ? formatINR(budget) : "—"}
          sub={budgetSummary ? `${budgetSummary.pct_used.toFixed(0)}% allocated` : undefined}
          subColor={budgetSummary?.over_budget ? "text-destructive" : "text-green-600"}
        />
        <StatCard
          icon={Clock}
          label="Duration"
          value={req?.duration_days ? `${req.duration_days} day${Number(req.duration_days) > 1 ? "s" : ""}` : "—"}
          sub={`${session.retrieval_rounds} retrieval round(s)`}
        />
      </div>

      {/* Status row */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm">
          <span className="text-muted-foreground">Evidence items:</span>
          <strong>{session.evidence_count}</strong>
        </div>
        <div className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm">
          <span className="text-muted-foreground">Critic iterations:</span>
          <strong>{session.critic_iterations}</strong>
        </div>
        <div className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm">
          <span className="text-muted-foreground">Vendors selected:</span>
          <strong>{session.vendor_selections.length}</strong>
        </div>
        {budgetSummary?.negotiation_savings ? (
          <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">
            <TrendingDown className="h-4 w-4" />
            <span>Saved {formatINR(budgetSummary.negotiation_savings)} via negotiation</span>
          </div>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Vendor selections */}
        <div className="lg:col-span-2 space-y-3">
          <h3 className="text-sm font-semibold">Selected Vendors</h3>
          {session.vendor_selections.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center text-sm text-muted-foreground">
                <Activity className="mx-auto mb-2 h-6 w-6 opacity-30" />
                {["planning", "researching", "created"].includes(session.status)
                  ? "Agents are selecting vendors…"
                  : "No vendors selected yet"}
              </CardContent>
            </Card>
          ) : (
            session.vendor_selections.map((sel) => (
              <VendorCard key={sel.vendor_id} sel={sel} />
            ))
          )}
        </div>

        {/* Budget chart */}
        <div className="space-y-4">
          {pieData.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Budget Allocation</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((entry, i) => (
                        <Cell
                          key={entry.name}
                          fill={CATEGORY_COLORS[entry.name] ?? "#94a3b8"}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v: number) => formatINR(v)}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-2 space-y-1">
                  {pieData.slice(0, 4).map((d) => (
                    <div key={d.name} className="flex items-center gap-2 text-xs">
                      <span
                        className="h-2 w-2 rounded-full shrink-0"
                        style={{ backgroundColor: CATEGORY_COLORS[d.name] ?? "#94a3b8" }}
                      />
                      <span className="capitalize truncate">{d.name.replace("_", " ")}</span>
                      <span className="ml-auto font-medium">{formatINR(d.value)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Critic status */}
          {lastCritic && (
            <Card className={lastCritic.passed ? "border-green-200" : "border-yellow-200"}>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  {lastCritic.passed
                    ? <CheckCircle2 className="h-4 w-4 text-green-600" />
                    : <AlertTriangle className="h-4 w-4 text-yellow-600" />}
                  <CardTitle className="text-sm">Critic Evaluation</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-1">
                {lastCritic.issues.slice(0, 3).map((issue, i) => (
                  <div key={i} className="text-xs text-muted-foreground">
                    <Badge
                      variant={issue.severity === "high" ? "destructive" : issue.severity === "medium" ? "warning" : "secondary"}
                      className="mr-1 px-1 py-0 text-[10px]"
                    >
                      {issue.severity}
                    </Badge>
                    {issue.detail.slice(0, 60)}…
                  </div>
                ))}
                {lastCritic.passed && (
                  <p className="text-xs text-green-700">All checks passed ✓</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Negotiation savings */}
          {savingsData.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Negotiation Savings</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={savingsData}>
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v: number) => formatINR(v)} />
                    <Bar dataKey="savings" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Errors */}
      {session.errors.length > 0 && (
        <Card className="border-destructive/30">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-destructive" />
              <CardTitle className="text-sm text-destructive">Errors</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-1">
            {session.errors.map((e, i) => (
              <p key={i} className="text-xs text-muted-foreground">{e}</p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function VendorCard({ sel }: { sel: VendorSelection }) {
  const price = sel.final_price ?? sel.quoted_price;
  const hasSavings = sel.negotiation_savings > 0;

  return (
    <div className="flex items-start gap-3 rounded-lg border bg-card p-4">
      <div
        className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: CATEGORY_COLORS[sel.category] ?? "#94a3b8" }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium">{sel.name}</p>
            <p className="text-xs text-muted-foreground capitalize">
              {sel.category.replace("_", " ")} · {sel.city}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-sm font-semibold">{formatINR(price)}</p>
            {hasSavings && (
              <p className="text-xs text-green-600">−{formatINR(sel.negotiation_savings)}</p>
            )}
          </div>
        </div>
        {sel.evidence_ids.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {sel.evidence_ids.map((eid) => (
              <Badge key={eid} variant="outline" className="px-1 py-0 text-[10px] font-mono">
                {eid}
              </Badge>
            ))}
          </div>
        )}
        {sel.critic_warnings.length > 0 && (
          <p className="mt-1 text-[11px] text-yellow-700">
            ⚠ {sel.critic_warnings[0]}
          </p>
        )}
      </div>
      <StatusDot status={sel.status} />
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    selected: "bg-blue-400",
    approved: "bg-green-400",
    booked: "bg-green-600",
    rejected: "bg-red-400",
  };
  return (
    <span
      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${colors[status] ?? "bg-gray-300"}`}
      title={status}
    />
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  subColor = "text-muted-foreground",
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-base font-semibold leading-tight">{value}</p>
            {sub && <p className={`text-[11px] ${subColor}`}>{sub}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 rounded bg-muted" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  );
}
