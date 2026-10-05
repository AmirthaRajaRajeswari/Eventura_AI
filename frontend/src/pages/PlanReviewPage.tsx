import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Edit3,
  Heart,
  MapPin,
  ShieldCheck,
  Sparkles,
  ThumbsUp,
  TrendingDown,
  Users,
  Wallet,
  X,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  sessionsApi,
  type VendorSelection,
  type CriticIssue,
} from "@/api/sessions";
import { formatINR, formatDate } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";

const CATEGORY_COLORS: Record<string, string> = {
  venue: "#8b6b45",
  catering: "#b78b62",
  decoration: "#a47b3d",
  photography: "#75636b",
  makeup: "#b68c83",
  music: "#66536b",
  ritual_services: "#8d7861",
  transport: "#8b765f",
  cake: "#9a6b72",
  entertainer: "#6f6a62",
  sound_lights: "#74656d",
  stage: "#8a7a61",
  performers: "#91775d",
  permissions_security: "#68645e",
  banners_printing: "#77716a",
};

const CATEGORY_LABELS: Record<string, string> = {
  venue: "Venue",
  catering: "Catering",
  decoration: "Decoration",
  photography: "Photography",
  makeup: "Makeup",
  music: "Music",
  ritual_services: "Ritual Services",
  transport: "Transport",
  cake: "Cake",
  entertainer: "Entertainment",
  sound_lights: "Sound & Lights",
  stage: "Stage",
  performers: "Performers",
  permissions_security: "Permissions & Security",
  banners_printing: "Printing",
};

function eventTypeLabel(value?: unknown) {
  if (!value) return "Your Event";

  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function categoryLabel(category: string) {
  return (
    CATEGORY_LABELS[category] ??
    category.replace(/_/g, " ")
  );
}

function categoryColor(category: string) {
  return CATEGORY_COLORS[category] ?? "#91877e";
}

export default function PlanReviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [feedback, setFeedback] = useState("");
  const [rejectedVendors, setRejectedVendors] = useState<string[]>(
    []
  );

  const { data: session, isLoading } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
  });

  const { data: approval } = useQuery({
    queryKey: ["approval", sessionId],
    queryFn: () => sessionsApi.getApproval(sessionId!),
    enabled: !!sessionId && session?.awaiting_human,
  });

  const approveMutation = useMutation({
    mutationFn: (
      data: Parameters<typeof sessionsApi.approve>[1]
    ) => sessionsApi.approve(sessionId!, data),

    onSuccess: (_, vars) => {
      qc.invalidateQueries({
        queryKey: ["session", sessionId],
      });

      toast({
        title:
          vars.action === "approve"
            ? "Plan approved"
            : "Feedback sent",
        description:
          vars.action === "approve"
            ? "Agents are now booking vendors…"
            : "Agents will replan with your feedback.",
      });

      navigate(`/events/${sessionId}`);
    },

    onError: () =>
      toast({
        variant: "destructive",
        title: "Submission failed",
      }),
  });

  if (isLoading) {
    return <PlanReviewSkeleton />;
  }

  if (!session) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center bg-[#f8f5ef]">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#eee8df]">
            <Heart className="h-5 w-5 text-[#8b6b45]" />
          </div>

          <h2 className="mt-4 font-serif text-2xl text-[#2b2030]">
            Session not found
          </h2>

          <p className="mt-2 text-sm text-[#817870]">
            We couldn't load this event plan.
          </p>
        </div>
      </div>
    );
  }

  const req =
    session.requirements as Record<string, unknown> | undefined;

  const lastCritic =
    session.critic_feedback[
      session.critic_feedback.length - 1
    ];

  const highIssues =
    lastCritic?.issues?.filter(
      (i: CriticIssue) => i.severity === "high"
    ) ?? [];

  const isAwaitingApproval =
    session.awaiting_human ||
    session.status === "awaiting_approval";

  const selectedSpend = session.vendor_selections.reduce(
    (sum, vendor) =>
      sum + (vendor.final_price ?? vendor.quoted_price),
    0
  );

  const totalSavings =
    session.vendor_selections.reduce(
      (sum, vendor) => sum + vendor.negotiation_savings,
      0
    );

  const eventType = eventTypeLabel(req?.event_type);

  function toggleReject(vendorId: string) {
    setRejectedVendors((prev) =>
      prev.includes(vendorId)
        ? prev.filter((v) => v !== vendorId)
        : [...prev, vendorId]
    );
  }

  function handleApprove() {
    approveMutation.mutate({
      action: "approve",
    });
  }

  function handleModify() {
    if (!feedback.trim()) {
      toast({
        variant: "destructive",
        title: "Please enter your modification request",
      });

      return;
    }

    approveMutation.mutate({
      action: "modify",
      message: feedback,
    });
  }

  function handleRejectVendors() {
    if (rejectedVendors.length === 0) {
      toast({
        variant: "destructive",
        title: "Select at least one vendor to reject",
      });

      return;
    }

    approveMutation.mutate({
      action: "reject_vendor",
      rejected_vendor_ids: rejectedVendors,
    });
  }

  return (
    <div className="min-h-full bg-[#f8f5ef] text-[#2b2030]">
      <div className="mx-auto max-w-[1320px] px-4 py-6 sm:px-6 lg:px-8">

        {/* ─────────────────────────────────────
            TOP NAV
        ───────────────────────────────────── */}

        <div className="flex items-center justify-between">
          <Link
            to={`/events/${sessionId}`}
            className="inline-flex items-center text-xs font-medium text-[#756d67] transition-colors hover:text-[#2b2030]"
          >
            <ArrowLeft className="mr-2 h-3.5 w-3.5" />
            Back to event
          </Link>

          <div className="flex items-center gap-2">
            <span className="text-[9px] uppercase tracking-[0.16em] text-[#a19891]">
              Eventura
            </span>

            <span className="h-1 w-1 rounded-full bg-[#c3b8ab]" />

            <span className="text-[9px] uppercase tracking-[0.16em] text-[#a19891]">
              Plan Review
            </span>
          </div>
        </div>

        {/* ─────────────────────────────────────
            HERO
        ───────────────────────────────────── */}

        <section className="relative mt-5 overflow-hidden rounded-[28px] bg-[#2b2030] px-6 py-9 text-white shadow-[0_18px_50px_rgba(43,32,48,0.14)] sm:px-9 sm:py-11">
          <div className="absolute -right-20 -top-28 h-72 w-72 rounded-full border border-[#d0ad6e]/20" />
          <div className="absolute -right-2 -top-12 h-48 w-48 rounded-full border border-[#d0ad6e]/10" />

          <div className="relative max-w-4xl">
            <div className="flex flex-wrap items-center gap-3">
              <span className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#d0ad6e]">
                <Sparkles className="h-3.5 w-3.5" />
                Your Eventura Proposal
              </span>

              {isAwaitingApproval && (
                <>
                  <span className="h-1 w-1 rounded-full bg-white/30" />

                  <span className="flex items-center gap-1.5 rounded-full border border-[#d0ad6e]/30 bg-[#d0ad6e]/10 px-3 py-1.5 text-[9px] font-medium uppercase tracking-[0.1em] text-[#e5d2aa]">
                    <AlertTriangle className="h-3 w-3" />
                    Your review is needed
                  </span>
                </>
              )}
            </div>

            <h1 className="mt-4 font-serif text-4xl leading-[1.08] text-[#fffdf9] sm:text-5xl">
              Here's what we've planned.
            </h1>

            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/55">
              Eventura has researched your options, balanced the
              budget, negotiated where possible and run the plan
              through an independent quality review.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs text-white/60">
              {req?.date && (
                <span className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#d0ad6e]" />
                  {formatDate(String(req.date))}
                </span>
              )}

              {req?.guest_count && (
                <span className="flex items-center gap-2">
                  <Users className="h-3.5 w-3.5 text-[#d0ad6e]" />
                  {Number(req.guest_count).toLocaleString()} guests
                </span>
              )}

              {req?.city && (
                <span className="flex items-center gap-2">
                  <MapPin className="h-3.5 w-3.5 text-[#d0ad6e]" />
                  {String(req.city)}
                </span>
              )}
            </div>
          </div>
        </section>

        {/* ─────────────────────────────────────
            EVENT SUMMARY
        ───────────────────────────────────── */}

        <section className="mt-7">
          <div className="mb-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#a77b3d]">
              The brief
            </p>

            <h2 className="mt-1 font-serif text-2xl text-[#2b2030]">
              {eventType}
            </h2>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <SummaryItem
              label="Event type"
              value={eventType}
            />

            <SummaryItem
              label="City"
              value={req?.city ? String(req.city) : "—"}
            />

            <SummaryItem
              label="Guests"
              value={
                req?.guest_count
                  ? Number(req.guest_count).toLocaleString()
                  : "—"
              }
            />

            <SummaryItem
              label="Budget"
              value={
                req?.budget
                  ? formatINR(Number(req.budget))
                  : "—"
              }
            />

            <SummaryItem
              label="Date"
              value={
                req?.date
                  ? formatDate(String(req.date))
                  : "—"
              }
            />

            <SummaryItem
              label="Duration"
              value={
                req?.duration_days
                  ? `${req.duration_days} day${
                      Number(req.duration_days) > 1
                        ? "s"
                        : ""
                    }`
                  : "—"
              }
            />
          </div>
        </section>

        {/* ─────────────────────────────────────
            BUDGET STORY
        ───────────────────────────────────── */}

        {session.budget_summary && (
          <section className="mt-8">
            <div className="mb-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#a77b3d]">
                Financial picture
              </p>

              <h2 className="mt-1 font-serif text-2xl text-[#2b2030]">
                Your budget at a glance
              </h2>
            </div>

            <div
              className={`rounded-[24px] border bg-white p-5 sm:p-6 ${
                session.budget_summary.over_budget
                  ? "border-red-200"
                  : "border-[#ddd4c9]"
              }`}
            >
              <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#f1ece5]">
                      <Wallet className="h-5 w-5 text-[#8b6b45]" />
                    </div>

                    <div>
                      <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[#9a9088]">
                        Total budget
                      </p>

                      <p className="font-serif text-2xl text-[#2b2030]">
                        {formatINR(
                          session.budget_summary.total_budget
                        )}
                      </p>
                    </div>

                    <Badge
                      className={
                        session.budget_summary.over_budget
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-[#d8e4d2] bg-[#edf3e9] text-[#65785d]"
                      }
                    >
                      {session.budget_summary.over_budget
                        ? "Over budget"
                        : "Within budget"}
                    </Badge>
                  </div>

                  <div className="mt-6">
                    <div className="mb-2 flex items-center justify-between text-xs">
                      <span className="text-[#817870]">
                        Allocated
                      </span>

                      <span className="font-medium text-[#3b3238]">
                        {formatINR(
                          session.budget_summary.spent
                        )}
                      </span>
                    </div>

                    <div className="h-2 overflow-hidden rounded-full bg-[#eee8df]">
                      <div
                        className={`h-full rounded-full ${
                          session.budget_summary.over_budget
                            ? "bg-[#b66a61]"
                            : "bg-[#8b6b45]"
                        }`}
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(
                              0,
                              Number(
                                session.budget_summary.pct_used ??
                                  0
                              )
                            )
                          )}%`,
                        }}
                      />
                    </div>

                    <div className="mt-2 flex items-center justify-between text-[10px] text-[#938981]">
                      <span>
                        {Number(
                          session.budget_summary.pct_used ?? 0
                        ).toFixed(0)}
                        % allocated
                      </span>

                      <span>
                        {formatINR(
                          Math.abs(
                            session.budget_summary.remaining
                          )
                        )}{" "}
                        {session.budget_summary.remaining >= 0
                          ? "remaining"
                          : "over"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:min-w-[420px]">
                  <FinancialMetric
                    label="Allocated"
                    value={formatINR(
                      session.budget_summary.spent
                    )}
                  />

                  <FinancialMetric
                    label={
                      session.budget_summary.remaining >= 0
                        ? "Remaining"
                        : "Over budget"
                    }
                    value={formatINR(
                      Math.abs(
                        session.budget_summary.remaining
                      )
                    )}
                    alert={
                      session.budget_summary.remaining < 0
                    }
                  />

                  <FinancialMetric
                    label="Negotiated savings"
                    value={formatINR(
                      session.budget_summary
                        .negotiation_savings
                    )}
                    positive
                  />
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ─────────────────────────────────────
            VENDORS
        ───────────────────────────────────── */}

        <section className="mt-8">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#a77b3d]">
                Curated selections
              </p>

              <h2 className="mt-1 font-serif text-3xl text-[#2b2030]">
                The team we've chosen
              </h2>

              <p className="mt-1 text-xs text-[#827970]">
                Select a vendor to mark it for replacement.
              </p>
            </div>

            <span className="text-xs text-[#817870]">
              {session.vendor_selections.length} selections
            </span>
          </div>

          {session.vendor_selections.length === 0 ? (
            <div className="rounded-[24px] border border-[#ddd4c9] bg-white px-6 py-14 text-center">
              <Sparkles className="mx-auto h-7 w-7 text-[#b5a99d]" />

              <h3 className="mt-4 font-serif text-xl text-[#2b2030]">
                Your selections are still being prepared
              </h3>

              <p className="mt-2 text-sm text-[#817870]">
                Eventura will show the recommended vendors here
                once the planning process is complete.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {session.vendor_selections.map((sel) => (
                <ReviewVendorCard
                  key={sel.vendor_id}
                  sel={sel}
                  rejected={rejectedVendors.includes(
                    sel.vendor_id
                  )}
                  onToggle={() =>
                    toggleReject(sel.vendor_id)
                  }
                />
              ))}
            </div>
          )}
        </section>

        {/* ─────────────────────────────────────
            QUALITY REVIEW
        ───────────────────────────────────── */}

        {lastCritic && (
          <section className="mt-8">
            <div className="mb-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#a77b3d]">
                Independent review
              </p>

              <h2 className="mt-1 font-serif text-2xl text-[#2b2030]">
                A second set of eyes
              </h2>
            </div>

            <div
              className={`rounded-[24px] border bg-white p-5 sm:p-6 ${
                lastCritic.passed
                  ? "border-[#d6dfd1]"
                  : "border-[#e5d7c0]"
              }`}
            >
              <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex gap-4">
                  <div
                    className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${
                      lastCritic.passed
                        ? "bg-[#e8efe4]"
                        : "bg-[#f4ead8]"
                    }`}
                  >
                    {lastCritic.passed ? (
                      <CheckCircle2 className="h-5 w-5 text-[#6d8265]" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-[#a77b3d]" />
                    )}
                  </div>

                  <div>
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[#a77b3d]">
                      Critic iteration{" "}
                      {lastCritic.iteration}
                    </p>

                    <h3 className="mt-1 font-serif text-xl text-[#2b2030]">
                      {lastCritic.passed
                        ? "The plan passed its quality checks"
                        : "A few things were flagged for review"}
                    </h3>
                  </div>
                </div>

                {lastCritic.passed && (
                  <div className="flex items-center gap-2 rounded-full bg-[#edf3e9] px-3 py-1.5 text-[10px] font-medium text-[#65785d]">
                    <Check className="h-3 w-3" />
                    Passed
                  </div>
                )}
              </div>

              {lastCritic.issues.length === 0 ? (
                <div className="mt-5 border-t border-[#e8e2d9] pt-4">
                  <p className="flex items-center gap-2 text-xs text-[#687860]">
                    <ShieldCheck className="h-4 w-4" />
                    Budget, constraints and planning checks
                    passed successfully.
                  </p>
                </div>
              ) : (
                <div className="mt-5 space-y-2 border-t border-[#e8e2d9] pt-4">
                  {lastCritic.issues.map(
                    (issue: CriticIssue, index: number) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 rounded-xl bg-[#faf7f1] px-4 py-3"
                      >
                        <Badge
                          className={
                            issue.severity === "high"
                              ? "border-red-200 bg-red-50 text-red-700"
                              : issue.severity === "medium"
                              ? "border-[#ead8b9] bg-[#fbf5e8] text-[#96713f]"
                              : "border-[#ddd8d1] bg-white text-[#77706a]"
                          }
                        >
                          {issue.severity}
                        </Badge>

                        <p className="text-xs leading-5 text-[#6f665f]">
                          {issue.detail}
                        </p>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        {/* ─────────────────────────────────────
            DECISION AREA
        ───────────────────────────────────── */}

        {isAwaitingApproval && (
          <section className="mt-9 pb-8">
            <div className="relative overflow-hidden rounded-[28px] border border-[#d8c8ad] bg-[#fffdf8] shadow-[0_15px_50px_rgba(78,59,42,0.07)]">
              <div className="absolute left-0 right-0 top-0 h-1 bg-[#c5a365]" />

              <div className="p-6 sm:p-8">
                <div className="flex flex-col gap-7 lg:flex-row lg:justify-between">
                  <div className="max-w-xl">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#f1e9da]">
                        <Heart className="h-5 w-5 text-[#9a7747]" />
                      </div>

                      <div>
                        <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#a77b3d]">
                          Your decision
                        </p>

                        <h2 className="font-serif text-2xl text-[#2b2030]">
                          Does this feel right?
                        </h2>
                      </div>
                    </div>

                    <p className="mt-4 text-sm leading-6 text-[#756d67]">
                      Review the selections above. You can approve
                      everything, ask Eventura to adjust the plan,
                      or mark specific vendors for replacement.
                    </p>

                    {highIssues.length > 0 && (
                      <div className="mt-4 flex gap-3 rounded-xl border border-[#ead9ba] bg-[#fbf5e9] p-3">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#a77b3d]" />

                        <p className="text-xs leading-5 text-[#806b4c]">
                          There are {highIssues.length} high-priority
                          issue
                          {highIssues.length > 1 ? "s" : ""} in the
                          latest review. Consider reviewing the
                          flagged items before approving.
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="lg:w-[430px]">
                    <div className="space-y-2">
                      <Label className="text-xs font-medium text-[#4c4147]">
                        Want something changed?
                      </Label>

                      <Textarea
                        placeholder="Tell Eventura what you'd like different…"
                        value={feedback}
                        onChange={(e) =>
                          setFeedback(e.target.value)
                        }
                        rows={4}
                        className="resize-none rounded-2xl border-[#dcd2c6] bg-white text-sm placeholder:text-[#aaa098] focus:border-[#a77b3d] focus:ring-[#a77b3d]/20"
                      />
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        onClick={handleApprove}
                        disabled={approveMutation.isPending}
                        className="rounded-full bg-[#2b2030] px-5 text-white hover:bg-[#3a2a40]"
                      >
                        <ThumbsUp className="mr-2 h-4 w-4" />
                        {approveMutation.isPending
                          ? "Processing…"
                          : "Approve & Book"}
                      </Button>

                      {feedback.trim() && (
                        <Button
                          variant="outline"
                          onClick={handleModify}
                          disabled={approveMutation.isPending}
                          className="rounded-full border-[#d8cfc4] bg-white px-5 text-[#493d45]"
                        >
                          <Edit3 className="mr-2 h-4 w-4" />
                          Modify Plan
                        </Button>
                      )}

                      {rejectedVendors.length > 0 && (
                        <Button
                          variant="outline"
                          onClick={handleRejectVendors}
                          disabled={approveMutation.isPending}
                          className="rounded-full border-red-200 bg-red-50 px-5 text-red-700 hover:bg-red-100"
                        >
                          <XCircle className="mr-2 h-4 w-4" />
                          Replace{" "}
                          {rejectedVendors.length} vendor
                          {rejectedVendors.length > 1
                            ? "s"
                            : ""}
                        </Button>
                      )}
                    </div>

                    <p className="mt-3 text-[10px] leading-4 text-[#9a9189]">
                      Booking will only proceed after you approve
                      the current plan.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ─────────────────────────────────────
            NON-HITL STATUS
        ───────────────────────────────────── */}

        {!isAwaitingApproval && (
          <section className="mt-9 pb-8">
            <div className="flex items-center gap-4 rounded-[24px] border border-[#ddd4c9] bg-white p-5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#f0ebe4]">
                {session.status === "completed" ||
                session.status === "booked" ? (
                  <CheckCircle2 className="h-5 w-5 text-[#6d8265]" />
                ) : (
                  <Sparkles className="h-5 w-5 text-[#8b6b45]" />
                )}
              </div>

              <div>
                <p className="text-sm font-medium text-[#393039]">
                  {session.status === "completed" ||
                  session.status === "booked"
                    ? "This plan has already been approved."
                    : "This plan is currently being processed."}
                </p>

                <p className="mt-1 text-xs text-[#817870]">
                  Return to your event workspace for the latest
                  planning status.
                </p>
              </div>

              <Button
                asChild
                variant="ghost"
                size="sm"
                className="ml-auto rounded-full"
              >
                <Link to={`/events/${sessionId}`}>
                  Event workspace
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   SUMMARY ITEM
───────────────────────────────────────────── */

function SummaryItem({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[18px] border border-[#ded6cc] bg-white px-5 py-4">
      <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#9b9189]">
        {label}
      </p>

      <p className="mt-1.5 text-sm font-medium text-[#3c3339]">
        {value}
      </p>
    </div>
  );
}

/* ─────────────────────────────────────────────
   FINANCIAL METRIC
───────────────────────────────────────────── */

function FinancialMetric({
  label,
  value,
  alert = false,
  positive = false,
}: {
  label: string;
  value: string;
  alert?: boolean;
  positive?: boolean;
}) {
  return (
    <div className="rounded-[18px] bg-[#f6f2ec] px-4 py-4">
      <p className="text-[9px] uppercase tracking-[0.12em] text-[#968c84]">
        {label}
      </p>

      <p
        className={`mt-1 font-serif text-lg ${
          alert
            ? "text-red-700"
            : positive
            ? "text-[#66795f]"
            : "text-[#302830]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

/* ─────────────────────────────────────────────
   VENDOR REVIEW CARD
───────────────────────────────────────────── */

function ReviewVendorCard({
  sel,
  rejected,
  onToggle,
}: {
  sel: VendorSelection;
  rejected: boolean;
  onToggle: () => void;
}) {
  const price = sel.final_price ?? sel.quoted_price;
  const color = categoryColor(sel.category);

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`group w-full text-left transition-all duration-300 ${
        rejected
          ? "rounded-[24px] border border-red-300 bg-red-50/60 shadow-[0_8px_25px_rgba(150,70,60,0.06)]"
          : "rounded-[24px] border border-[#ddd4c9] bg-white hover:-translate-y-0.5 hover:border-[#c9bba9] hover:shadow-[0_15px_40px_rgba(64,48,40,0.07)]"
      }`}
    >
      <div
        className="h-1.5 rounded-t-[24px]"
        style={{
          backgroundColor: rejected
            ? "#b66a61"
            : color,
        }}
      />

      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
              style={{
                backgroundColor: `${color}18`,
                color,
              }}
            >
              <span className="text-[10px] font-bold">
                {categoryLabel(sel.category)
                  .slice(0, 2)
                  .toUpperCase()}
              </span>
            </div>

            <div className="min-w-0">
              <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#9b9189]">
                {categoryLabel(sel.category)}
              </p>

              <h3 className="mt-1 truncate font-serif text-xl text-[#302730]">
                {sel.name}
              </h3>

              <p className="mt-1 flex items-center gap-1 text-xs text-[#827970]">
                <MapPin className="h-3 w-3" />
                {sel.city}
              </p>
            </div>
          </div>

          {rejected ? (
            <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-red-100 px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-red-700">
              <X className="h-3 w-3" />
              Replace
            </span>
          ) : (
            <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-[#f1ece5] px-3 py-1.5 text-[9px] font-medium uppercase tracking-[0.08em] text-[#786d64] opacity-0 transition-opacity group-hover:opacity-100">
              Select to replace
            </span>
          )}
        </div>

        <div className="mt-5 flex items-end justify-between border-t border-[#eee8df] pt-4">
          <div>
            <p className="text-[9px] uppercase tracking-[0.12em] text-[#9b9189]">
              Final price
            </p>

            <p className="mt-1 font-serif text-2xl text-[#2f2630]">
              {formatINR(price)}
            </p>
          </div>

          {sel.negotiation_savings > 0 && (
            <div className="text-right">
              <p className="flex items-center justify-end gap-1 text-[9px] uppercase tracking-[0.1em] text-[#718467]">
                <TrendingDown className="h-3 w-3" />
                Negotiated
              </p>

              <p className="mt-1 text-xs font-semibold text-[#65765d]">
                Saved {formatINR(sel.negotiation_savings)}
              </p>
            </div>
          )}
        </div>

        {sel.evidence_ids.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
            <span className="text-[9px] uppercase tracking-[0.1em] text-[#a09891]">
              Evidence
            </span>

            {sel.evidence_ids.map((evidence) => (
              <span
                key={evidence}
                className="rounded-full bg-[#f4f0ea] px-2 py-1 font-mono text-[9px] text-[#756c65]"
              >
                {evidence}
              </span>
            ))}
          </div>
        )}

        {sel.critic_warnings.length > 0 && (
          <div className="mt-4 rounded-xl bg-[#fbf6eb] px-3 py-2.5">
            <div className="flex gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#a77b3d]" />

              <div className="space-y-1">
                {sel.critic_warnings.map((warning, index) => (
                  <p
                    key={index}
                    className="text-[10px] leading-4 text-[#80643b]"
                  >
                    {warning}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </button>
  );
}

/* ─────────────────────────────────────────────
   SKELETON
───────────────────────────────────────────── */

function PlanReviewSkeleton() {
  return (
    <div className="min-h-full animate-pulse bg-[#f8f5ef] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1320px]">
        <div className="h-5 w-28 rounded bg-[#e4ddd4]" />

        <div className="mt-5 h-64 rounded-[28px] bg-[#30243a]" />

        <div className="mt-8 h-8 w-48 rounded bg-[#e4ddd4]" />

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((item) => (
            <div
              key={item}
              className="h-24 rounded-[18px] bg-white"
            />
          ))}
        </div>

        <div className="mt-8 h-36 rounded-[24px] bg-white" />

        <div className="mt-8 h-8 w-64 rounded bg-[#e4ddd4]" />

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((item) => (
            <div
              key={item}
              className="h-60 rounded-[24px] bg-white"
            />
          ))}
        </div>
      </div>
    </div>
  );
}