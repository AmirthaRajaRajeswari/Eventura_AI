import { useParams, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Calendar,
  Users,
  Wallet,
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  TrendingDown,
  MapPin,
  Sparkles,
  ShieldCheck,
  Search,
  Database,
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { sessionsApi, type VendorSelection } from "@/api/sessions";
import { formatINR, formatDate } from "@/lib/utils";

const CATEGORY_COLORS: Record<string, string> = {
  venue: "#8b6f4e",
  catering: "#718467",
  decoration: "#b28a4f",
  photography: "#756579",
  makeup: "#a78372",
  music: "#6f6876",
  ritual_services: "#8c806e",
  transport: "#92745b",
  cake: "#9a756c",
  entertainer: "#777467",
  sound_lights: "#756579",
  stage: "#8a7b5f",
  performers: "#9a835c",
  permissions_security: "#77736d",
  banners_printing: "#837a72",
};

const CATEGORY_LABELS: Record<string, string> = {
  venue: "Venue",
  catering: "Catering",
  decoration: "Decoration",
  photography: "Photography",
  makeup: "Makeup",
  music: "Music",
  ritual_services: "Ritual services",
  transport: "Transport",
  cake: "Cake",
  entertainer: "Entertainment",
  sound_lights: "Sound & lights",
  stage: "Stage",
  performers: "Performers",
  permissions_security: "Permissions & security",
  banners_printing: "Banners & printing",
};


export default function DashboardPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [showBookingConfirmed, setShowBookingConfirmed] = useState(false);

  const { data: session, isLoading } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;

      return status &&
        ![
          "completed",
          "failed",
          "infeasible",
          "awaiting_approval",
        ].includes(status)
        ? 3000
        : false;
    },
  });

  useEffect(() => {
  if (session?.status === "completed") {
    setShowBookingConfirmed(true);
  }
  }, [session?.status]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (!session) {
    return (
      <div className="p-8 text-sm text-muted-foreground">
        Session not found
      </div>
    );
  }

  const req = session.requirements as Record<string, unknown> | undefined;
  const budget = req?.budget as number | undefined;
  const budgetSummary = session.budget_summary;

  const totalSelectedSpend = session.vendor_selections.reduce(
    (sum, sel) => sum + (sel.final_price ?? sel.quoted_price),
    0
  );

  const budgetRemaining =
    budget != null ? budget - totalSelectedSpend : null;

  const pieData = Object.entries(
    session.vendor_selections.reduce((acc, sel) => {
      const price = sel.final_price ?? sel.quoted_price;
      acc[sel.category] = (acc[sel.category] ?? 0) + price;
      return acc;
    }, {} as Record<string, number>)
  ).map(([name, value]) => ({
    name,
    value,
  }));

  const lastCritic =
    session.critic_feedback[
      session.critic_feedback.length - 1
    ];

  const highIssues =
    lastCritic?.issues?.filter(
      (issue) => issue.severity === "high"
    ) ?? [];

  const eventName = req?.event_type
    ? String(req.event_type)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase())
    : "Event";

  const city = req?.city ? String(req.city) : "—";

  const guestCount = req?.guest_count
    ? Number(req.guest_count).toLocaleString()
    : "—";

  const duration = req?.duration_days
    ? `${req.duration_days} day${
        Number(req.duration_days) > 1 ? "s" : ""
      }`
    : "—";

  return (
    <div className="min-h-full bg-[#f8f5ef] text-[#2b2030]">
      <div className="mx-auto max-w-[1440px] px-6 py-7 lg:px-8">
        {/* HERO */}
        <section className="relative overflow-hidden rounded-[26px] bg-[#2b2030] px-7 py-7 text-white shadow-[0_18px_45px_rgba(43,32,48,0.12)] lg:px-9 lg:py-8">
          <div className="pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full border border-[#d0ad6e]/20" />
          <div className="pointer-events-none absolute -right-8 -top-12 h-56 w-56 rounded-full border border-[#d0ad6e]/10" />

          <div className="relative flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-[#d0ad6e]" />

                <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#d0ad6e]">
                  Event plan
                </span>
              </div>

              <h1 className="font-serif text-4xl tracking-[-0.03em] lg:text-5xl">
                {eventName}
              </h1>

              <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-white/70">
                <span className="flex items-center gap-2">
                  <Calendar className="h-3.5 w-3.5 text-[#d0ad6e]" />
                  {req?.date
                    ? formatDate(String(req.date))
                    : "Date not set"}
                </span>

                <span className="flex items-center gap-2">
                  <Users className="h-3.5 w-3.5 text-[#d0ad6e]" />
                  {guestCount} guests
                </span>

                <span className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5 text-[#d0ad6e]" />
                  {city}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                asChild
                className="h-10 rounded-full bg-white px-5 text-xs font-medium text-[#2b2030] shadow-none hover:bg-[#f2eee7]"
              >
                <Link to={`/events/${sessionId}/plan`}>
                  <ArrowRight className="mr-2 h-3.5 w-3.5" />
                  View Full Plan
                </Link>
              </Button>

              <Button
                asChild
                variant="outline"
                className="h-10 rounded-full border-white/20 bg-white/5 px-5 text-xs font-medium text-white shadow-none hover:bg-white/10 hover:text-white"
              >
                <Link to={`/events/${sessionId}/activity`}>
                  <Activity className="mr-2 h-3.5 w-3.5" />
                  Agent Activity
                </Link>
              </Button>

              <Button
                asChild
                variant="outline"
                className="h-10 rounded-full border-white/20 bg-transparent px-5 text-xs font-medium text-white shadow-none hover:bg-white/10 hover:text-white"
              >
                <Link to={`/events/${sessionId}/disrupt`}>
                  Simulate Change
                  <ArrowRight className="ml-2 h-3.5 w-3.5" />
                </Link>
              </Button>
            </div>
          </div>
        </section>

        {/* EVENT FACTS */}
        <section className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <SnapshotCard
            icon={Calendar}
            label="Event date"
            value={
              req?.date
                ? formatDate(String(req.date))
                : "Not set"
            }
          />

          <SnapshotCard
            icon={Users}
            label="Guest count"
            value={guestCount}
            suffix="people"
          />

          <SnapshotCard
            icon={Wallet}
            label="Planning budget"
            value={budget ? formatINR(budget) : "—"}
            suffix={
              budgetSummary?.pct_used != null
                ? `${Number(budgetSummary.pct_used).toFixed(0)}% allocated`
                : undefined
            }
          />

          <SnapshotCard
            icon={Clock}
            label="Event duration"
            value={duration}
          />
        </section>

        {/* MAIN CONTENT */}
        <section className="mt-8 grid items-stretch gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          {/* LEFT */}
          <div className="min-w-0">
            <div className="mb-4 flex items-end justify-between">
              <div>
                <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-[#a77b3d]">
                  Your plan
                </p>

                <h2 className="mt-1 font-serif text-3xl tracking-[-0.025em]">
                  Selected services
                </h2>
              </div>

              <span className="text-xs text-[#8f857e]">
                {session.vendor_selections.length} services selected
              </span>
            </div>

            {session.vendor_selections.length === 0 ? (
              <Card className="border-[#ded6cc] bg-white shadow-none">
                <CardContent className="py-12 text-center text-sm text-[#8f857e]">
                  <Activity className="mx-auto mb-3 h-6 w-6 opacity-30" />

                  {["planning", "researching", "created"].includes(
                    session.status
                  )
                    ? "Agents are selecting vendors…"
                    : "No vendors selected yet"}
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {session.vendor_selections.map((sel) => (
                  <VendorCard
                    key={sel.vendor_id}
                    sel={sel}
                  />
                ))}
              </div>
            )}

            {/* NEGOTIATION + QUALITY REVIEW */}
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <NegotiationCard
                budgetSummary={budgetSummary}
                savingsData={session.negotiation_logs
                  .filter((n) => n.savings > 0)
                  .map((n) => ({
                    name: n.category,
                    savings: n.savings,
                  }))}
              />

              <QualityCard
                lastCritic={lastCritic}
                highIssues={highIssues}
              />
            </div>
          </div>

          {/* RIGHT RAIL */}
          <aside className="h-full">
            {/* BUDGET */}
            <Card className="flex h-full min-h-[540px] flex-col overflow-hidden rounded-[20px] border-[#ded6cc] bg-[#fffdfa] shadow-none">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#a77b3d]">
                      Financial view
                    </p>

                    <CardTitle className="mt-1 font-serif text-2xl font-normal text-[#2b2030]">
                      Budget
                    </CardTitle>
                  </div>

                  <Wallet className="h-4 w-4 text-[#a77b3d]" />
                </div>
              </CardHeader>

              <CardContent className="flex flex-1 flex-col">
                {pieData.length > 0 ? (
                  <>
                    {/* Budget chart */}
                    <div className="relative h-[205px] shrink-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={62}
                            outerRadius={86}
                            paddingAngle={2}
                            dataKey="value"
                            stroke="none"
                          >
                            {pieData.map((entry) => (
                              <Cell
                                key={entry.name}
                                fill={
                                  CATEGORY_COLORS[entry.name] ??
                                  "#9a9189"
                                }
                              />
                            ))}
                          </Pie>

                          <Tooltip
                            formatter={(value: number) =>
                              formatINR(value)
                            }
                          />
                        </PieChart>
                      </ResponsiveContainer>

                      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-[9px] uppercase tracking-[0.15em] text-[#938981]">
                          Allocated
                        </span>

                        <span className="mt-1 font-serif text-[25px] text-[#2b2030]">
                          {budgetSummary?.pct_used != null
                            ? `${Number(
                                budgetSummary.pct_used
                              ).toFixed(0)}%`
                            : "—"}
                        </span>
                      </div>
                    </div>

                    {/* Budget overview */}
                    <div className="border-t border-[#eee8df] py-4">
                      <div className="flex items-end justify-between">
                        <div>
                          <p className="text-[8px] font-semibold uppercase tracking-[0.16em] text-[#9a9189]">
                            Budget overview
                          </p>

                          <p className="mt-1 font-serif text-[21px] text-[#2b2030]">
                            {budget != null
                              ? formatINR(budget)
                              : "—"}
                          </p>

                          <p className="mt-0.5 text-[9px] text-[#91877f]">
                            Total planning budget
                          </p>
                        </div>

                        <div className="text-right">
                          <p className="text-[8px] font-semibold uppercase tracking-[0.14em] text-[#9a9189]">
                            {budgetRemaining != null &&
                            budgetRemaining < 0
                              ? "Over budget"
                              : "Remaining"}
                          </p>

                          <p
                            className={`mt-1 font-serif text-[16px] ${
                              budgetRemaining != null &&
                              budgetRemaining < 0
                                ? "text-[#a7625b]"
                                : "text-[#2b2030]"
                            }`}
                          >
                            {budgetRemaining != null
                              ? formatINR(
                                  Math.abs(budgetRemaining)
                                )
                              : "—"}
                          </p>
                        </div>
                      </div>

                      {/* Allocation progress */}
                      <div className="mt-4">
                        <div className="mb-1.5 flex items-center justify-between">
                          <span className="text-[8px] uppercase tracking-[0.12em] text-[#91877f]">
                            Planned spend
                          </span>

                          <span className="text-[9px] font-medium text-[#6f6258]">
                            {budgetSummary?.pct_used != null
                              ? `${Number(
                                  budgetSummary.pct_used
                                ).toFixed(0)}%`
                              : "—"}
                          </span>
                        </div>

                        <div className="h-1.5 overflow-hidden rounded-full bg-[#eee8df]">
                          <div
                            className="h-full rounded-full bg-[#a77b3d] transition-all"
                            style={{
                              width:
                                budget != null && budget > 0
                                  ? `${Math.min(
                                      (totalSelectedSpend /
                                        budget) *
                                        100,
                                      100
                                    )}%`
                                  : "0%",
                            }}
                          />
                        </div>

                        <div className="mt-1.5 flex justify-between text-[8px] text-[#9a9189]">
                          <span>
                            {formatINR(totalSelectedSpend)} planned
                          </span>

                          <span>
                            {budget != null
                              ? formatINR(budget)
                              : "—"}{" "}
                            total
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Agent insight */}
                    <div className="rounded-xl bg-[#f3eee6] px-3.5 py-3">
                      <div className="flex gap-2.5">
                        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#2b2030]">
                          <Sparkles className="h-3 w-3 text-[#d0ad6e]" />
                        </div>

                        <div>
                          <p className="text-[8px] font-semibold uppercase tracking-[0.14em] text-[#806b52]">
                            Planning insight
                          </p>

                          <p className="mt-1 text-[9px] leading-4 text-[#665c55]">
                            {budgetSummary?.negotiation_savings &&
                            budgetSummary.negotiation_savings > 0
                              ? `Negotiation saved ${formatINR(
                                  budgetSummary.negotiation_savings
                                )} across selected services.`
                              : budgetRemaining != null &&
                                budgetRemaining >= 0
                              ? "The selected services remain within the allocated budget."
                              : "The selected services currently exceed the allocated budget."}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Category breakdown */}
                    <div className="mt-4 space-y-2 border-t border-[#eee8e0] pt-4">
                      {pieData.map((item) => (
                        <div
                          key={item.name}
                          className="flex items-center gap-2 text-xs"
                        >
                          <span
                            className="h-2 w-2 shrink-0 rounded-full"
                            style={{
                              backgroundColor:
                                CATEGORY_COLORS[item.name] ??
                                "#9a9189",
                            }}
                          />

                          <span className="flex-1 capitalize text-[#716761]">
                            {CATEGORY_LABELS[item.name] ??
                              item.name.replace(/_/g, " ")}
                          </span>

                          <span className="font-medium text-[#2b2030]">
                            {formatINR(item.value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="flex h-52 items-center justify-center text-center">
                    <div>
                      <Wallet className="mx-auto h-7 w-7 text-[#c8bfb6]" />

                      <p className="mt-3 text-xs text-[#827970]">
                        Budget allocation will appear
                        <br />
                        as your plan develops.
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </aside>
        </section>

        {/* PLANNING INTELLIGENCE */}
        <section className="mt-6">
          <Card className="rounded-[20px] border-[#ded6cc] bg-[#eee8df] shadow-none">
            <CardContent className="px-5 py-5 lg:px-6">
              <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
                <div className="flex min-w-0 flex-1 items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#2b2030]">
                    <Sparkles className="h-4 w-4 text-[#d0ad6e]" />
                  </div>

                  <div>
                    <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#a77b3d]">
                      Planning intelligence
                    </p>

                    <h3 className="mt-1 font-serif text-xl text-[#2b2030]">
                      Evidence-backed planning
                    </h3>

                    <p className="mt-1 max-w-2xl text-xs leading-5 text-[#776d66]">
                      Eventura combined vendor retrieval, planning
                      evidence, budget reasoning and critic validation
                      to refine the current plan.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-x-8 gap-y-3 border-t border-[#d8d0c6] pt-4 sm:grid-cols-4 lg:border-l lg:border-t-0 lg:pl-7 lg:pt-0">
                  <Metric
                    icon={Database}
                    label="Evidence"
                    value={String(session.evidence_count)}
                  />

                  <Metric
                    icon={Search}
                    label="Retrieval"
                    value={`${session.retrieval_rounds} rounds`}
                  />

                  <Metric
                    icon={ShieldCheck}
                    label="Critic"
                    value={`${session.critic_iterations} checks`}
                  />

                  <Metric
                    icon={Users}
                    label="Vendors"
                    value={String(
                      session.vendor_selections.length
                    )}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* ERRORS */}
        {session.errors.length > 0 && (
          <Card className="mt-5 rounded-[20px] border-red-200 bg-red-50 shadow-none">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-600" />

                <CardTitle className="text-sm text-red-700">
                  Planning errors
                </CardTitle>
              </div>
            </CardHeader>

            <CardContent className="space-y-1">
              {session.errors.map((error, index) => (
                <p
                  key={index}
                  className="text-xs text-red-700/80"
                >
                  {error}
                </p>
              ))}
            </CardContent>
          </Card>
        )}

        {/* BOOKING CONFIRMATION */}
        {showBookingConfirmed && (
          <div className="fixed bottom-5 right-5 z-50 w-[min(380px,calc(100vw-40px))] rounded-2xl border border-[#d7c9b7] bg-[#2b2030] p-5 text-white shadow-[0_20px_50px_rgba(43,32,48,0.25)]">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#d0ad6e]">
                <CheckCircle2 className="h-5 w-5 text-[#2b2030]" />
              </div>

              <div className="min-w-0">
                <p className="font-serif text-lg">
                  Booking confirmed
                </p>

                <p className="mt-1 text-xs leading-5 text-white/65">
                  Your selected event services have been
                  successfully booked.
                </p>
              </div>

              <button
                onClick={() => setShowBookingConfirmed(false)}
                className="ml-auto text-white/40 hover:text-white"
                aria-label="Close"
              >
                ×
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SnapshotCard({
  icon: Icon,
  label,
  value,
  suffix,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  suffix?: string;
}) {
  return (
    <div className="min-h-[118px] rounded-[18px] border border-[#ded6cc] bg-white px-5 py-5">
      <div className="flex h-full flex-col justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f1eadf]">
            <Icon className="h-3.5 w-3.5 text-[#a77b3d]" />
          </div>

          <span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[#9b9189]">
            {label}
          </span>
        </div>

        <div className="mt-5 flex items-baseline gap-2">
          <span className="font-serif text-[22px] text-[#2b2030]">
            {value}
          </span>

          {suffix && (
            <span className="text-[10px] text-[#938981]">
              {suffix}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function VendorCard({
  sel,
}: {
  sel: VendorSelection;
}) {
  const price = sel.final_price ?? sel.quoted_price;
  const hasSavings = sel.negotiation_savings > 0;

  return (
    <div className="overflow-hidden rounded-[18px] border border-[#ded6cc] bg-white">
      <div
        className="h-1"
        style={{
          backgroundColor:
            CATEGORY_COLORS[sel.category] ?? "#a77b3d",
        }}
      />

      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[#a77b3d]">
              {sel.category.replace("_", " ")}
            </p>

            <h3 className="mt-2 truncate font-serif text-[21px] text-[#2b2030]">
              {sel.name}
            </h3>

            <p className="mt-1 flex items-center gap-1 text-xs text-[#8a8078]">
              <MapPin className="h-3 w-3" />
              {sel.city}
            </p>
          </div>

          <span className="shrink-0 rounded-full bg-[#f3eee6] px-2.5 py-1 text-[8px] font-semibold uppercase tracking-[0.1em] text-[#8c7253]">
            {sel.status}
          </span>
        </div>

        <div className="mt-6 flex items-end justify-between border-t border-[#eee8e0] pt-4">
          <div>
            <p className="text-[8px] uppercase tracking-[0.14em] text-[#a09891]">
              Selected price
            </p>

            <p className="mt-1 font-serif text-xl text-[#2b2030]">
              {formatINR(price)}
            </p>
          </div>

          {hasSavings && (
            <div className="text-right">
              <p className="text-[8px] uppercase tracking-[0.14em] text-[#718467]">
                Negotiated
              </p>

              <p className="mt-1 text-xs font-medium text-[#718467]">
                −{formatINR(sel.negotiation_savings)}
              </p>
            </div>
          )}
        </div>

        {sel.critic_warnings.length > 0 && (
          <div className="mt-4 rounded-lg bg-[#fbf5e8] px-3 py-2">
            <p className="text-[10px] leading-4 text-[#8b6b45]">
              {sel.critic_warnings[0]}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function NegotiationCard({
  budgetSummary,
  savingsData,
}: {
  budgetSummary: any;
  savingsData: {
    name: string;
    savings: number;
  }[];
}) {
  const totalSavings =
    budgetSummary?.negotiation_savings ?? 0;

  return (
    <Card className="rounded-[18px] border-[#ded6cc] bg-[#2b2030] text-white shadow-none">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#d0ad6e]">
              Negotiation
            </p>

            <h3 className="mt-1 font-serif text-xl">
              Savings found
            </h3>
          </div>

          <TrendingDown className="h-4 w-4 text-[#d0ad6e]" />
        </div>

        <p className="mt-5 font-serif text-3xl">
          {formatINR(totalSavings)}
        </p>

        <p className="mt-1 text-[10px] text-white/50">
          Negotiated savings across selected services
        </p>

        {savingsData.length > 0 && (
          <div className="mt-5 grid grid-cols-2 gap-2">
            {savingsData.slice(0, 2).map((item) => (
              <div
                key={item.name}
                className="rounded-lg bg-white/10 px-3 py-2"
              >
                <p className="truncate text-[9px] uppercase tracking-[0.08em] text-white/45">
                  {item.name}
                </p>

                <p className="mt-1 text-xs font-medium text-[#d0ad6e]">
                  −{formatINR(item.savings)}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function QualityCard({
  lastCritic,
  highIssues,
}: {
  lastCritic: any;
  highIssues: any[];
}) {
  const passed = lastCritic?.passed;

  return (
    <Card
      className={`rounded-[18px] shadow-none ${
        passed
          ? "border-[#cbd8c8] bg-[#f4f7f2]"
          : "border-[#e4d3b5] bg-[#fbf6ec]"
      }`}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#a77b3d]">
              Quality review
            </p>

            <h3 className="mt-1 font-serif text-xl text-[#2b2030]">
              {passed
                ? "Plan checks passed"
                : "Plan needs refinement"}
            </h3>
          </div>

          {passed ? (
            <CheckCircle2 className="h-5 w-5 text-[#718467]" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-[#b28a4f]" />
          )}
        </div>

        {passed ? (
          <p className="mt-4 text-xs leading-5 text-[#687265]">
            The critic found no blocking issues in the current
            plan.
          </p>
        ) : (
          <div className="mt-4 space-y-2">
            {highIssues.slice(0, 2).map((issue, index) => (
              <div
                key={index}
                className="text-[10px] leading-4 text-[#7b6a53]"
              >
                <span className="mr-1 font-semibold">
                  {issue.severity.toUpperCase()}
                </span>
                {issue.detail}
              </div>
            ))}

            {highIssues.length === 0 && (
              <p className="text-xs leading-5 text-[#7b6a53]">
                The critic identified items that may require
                another planning pass.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-3.5 w-3.5 text-[#a77b3d]" />

      <div>
        <p className="text-[8px] uppercase tracking-[0.12em] text-[#9b9189]">
          {label}
        </p>

        <p className="mt-0.5 text-xs font-medium text-[#3b3238]">
          {value}
        </p>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-48 rounded-[26px] bg-[#e9e3da]" />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="h-28 rounded-[18px] bg-[#e9e3da]"
          />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <div className="h-40 rounded-[18px] bg-[#e9e3da]" />
          <div className="h-40 rounded-[18px] bg-[#e9e3da]" />
        </div>

        <div className="h-[420px] rounded-[18px] bg-[#e9e3da]" />
      </div>
    </div>
  );
}