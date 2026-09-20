import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2, XCircle, AlertTriangle, ArrowLeft,
  ChevronRight, ThumbsUp, ThumbsDown, Edit2,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { sessionsApi, type VendorSelection, type CriticIssue } from "@/api/sessions";
import { formatINR, formatDate } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";

export default function PlanReviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [feedback, setFeedback] = useState("");
  const [rejectedVendors, setRejectedVendors] = useState<string[]>([]);

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
    mutationFn: (data: Parameters<typeof sessionsApi.approve>[1]) =>
      sessionsApi.approve(sessionId!, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["session", sessionId] });
      toast({
        title: vars.action === "approve" ? "Plan approved" : "Feedback sent",
        description: vars.action === "approve"
          ? "Agents are now booking vendors…"
          : "Agents will replan with your feedback.",
      });
      navigate(`/events/${sessionId}`);
    },
    onError: () => toast({ variant: "destructive", title: "Submission failed" }),
  });

  if (isLoading) return <div className="p-8 text-muted-foreground">Loading…</div>;
  if (!session) return <div className="p-8 text-muted-foreground">Session not found</div>;

  const req = session.requirements as Record<string, unknown> | undefined;
  const lastCritic = session.critic_feedback[session.critic_feedback.length - 1];
  const highIssues = lastCritic?.issues?.filter((i: CriticIssue) => i.severity === "high") ?? [];

  function toggleReject(vendorId: string) {
    setRejectedVendors((prev) =>
      prev.includes(vendorId) ? prev.filter((v) => v !== vendorId) : [...prev, vendorId]
    );
  }

  function handleApprove() {
    approveMutation.mutate({ action: "approve" });
  }

  function handleModify() {
    if (!feedback.trim()) {
      toast({ variant: "destructive", title: "Please enter your modification request" });
      return;
    }
    approveMutation.mutate({ action: "modify", message: feedback });
  }

  function handleRejectVendors() {
    if (rejectedVendors.length === 0) {
      toast({ variant: "destructive", title: "Select at least one vendor to reject" });
      return;
    }
    approveMutation.mutate({ action: "reject_vendor", rejected_vendor_ids: rejectedVendors });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/events/${sessionId}`}><ArrowLeft className="mr-2 h-4 w-4" />Dashboard</Link>
        </Button>
        <Separator orientation="vertical" className="h-5" />
        <h2 className="text-xl font-bold">Plan Review</h2>
        {session.awaiting_human && (
          <Badge variant="warning" className="gap-1">
            <AlertTriangle className="h-3 w-3" /> Approval Required
          </Badge>
        )}
      </div>

      {/* Event summary */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Event Summary</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
          {[
            { label: "Type", value: req?.event_type ? String(req.event_type).replace("_"," ").replace(/\b\w/g,c=>c.toUpperCase()) : "—" },
            { label: "City", value: req?.city as string ?? "—" },
            { label: "Guests", value: req?.guest_count ? Number(req.guest_count).toLocaleString() : "—" },
            { label: "Budget", value: req?.budget ? formatINR(Number(req.budget)) : "—" },
            { label: "Date", value: req?.date ? formatDate(String(req.date)) : "—" },
            { label: "Duration", value: req?.duration_days ? `${req.duration_days} day(s)` : "—" },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="font-medium">{value}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Budget summary */}
      {session.budget_summary && (
        <Card className={session.budget_summary.over_budget ? "border-destructive/40" : ""}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Budget</CardTitle>
              {session.budget_summary.over_budget
                ? <Badge variant="destructive">Over Budget</Badge>
                : <Badge variant="success">Within Budget</Badge>}
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-3 gap-3 text-sm">
            {[
              { label: "Total Budget", value: formatINR(session.budget_summary.total_budget) },
              { label: "Allocated", value: formatINR(session.budget_summary.spent) },
              { label: "Remaining", value: formatINR(session.budget_summary.remaining) },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="font-semibold">{value}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Vendor selections */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold">
          Vendor Selections
          <span className="ml-2 font-normal text-muted-foreground">
            (click to reject)
          </span>
        </h3>
        {session.vendor_selections.map((sel) => {
          const isRejected = rejectedVendors.includes(sel.vendor_id);
          return (
            <div
              key={sel.vendor_id}
              onClick={() => toggleReject(sel.vendor_id)}
              className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                isRejected ? "border-destructive bg-destructive/5" : "hover:border-primary/40"
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium">{sel.name}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {sel.category.replace("_"," ")} · {sel.city}
                  </p>
                  {sel.evidence_ids.length > 0 && (
                    <div className="mt-1 flex gap-1">
                      {sel.evidence_ids.map((e) => (
                        <Badge key={e} variant="outline" className="px-1 py-0 text-[10px] font-mono">{e}</Badge>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">{formatINR(sel.final_price ?? sel.quoted_price)}</p>
                  {sel.negotiation_savings > 0 && (
                    <p className="text-xs text-green-600">saved {formatINR(sel.negotiation_savings)}</p>
                  )}
                  {isRejected && <Badge variant="destructive" className="mt-1">Rejected</Badge>}
                </div>
              </div>
              {sel.critic_warnings.map((w, i) => (
                <p key={i} className="mt-1.5 text-xs text-yellow-700">⚠ {w}</p>
              ))}
            </div>
          );
        })}
      </div>

      {/* Critic results */}
      {lastCritic && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              {lastCritic.passed
                ? <CheckCircle2 className="h-4 w-4 text-green-600" />
                : <AlertTriangle className="h-4 w-4 text-yellow-600" />}
              <CardTitle className="text-sm">
                Critic Evaluation — Iteration {lastCritic.iteration}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {lastCritic.issues.length === 0
              ? <p className="text-sm text-green-700">All checks passed ✓</p>
              : lastCritic.issues.map((issue: CriticIssue, i: number) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <Badge
                    variant={issue.severity === "high" ? "destructive" : issue.severity === "medium" ? "warning" : "secondary"}
                    className="mt-0.5 shrink-0 px-1.5 py-0 text-[10px]"
                  >
                    {issue.severity}
                  </Badge>
                  <span className="text-muted-foreground">{issue.detail}</span>
                </div>
              ))
            }
          </CardContent>
        </Card>
      )}

      {/* Action panel */}
      {session.awaiting_human && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle className="text-base">Your Decision</CardTitle>
            <CardDescription>
              Review the plan and choose an action. Bookings are irreversible and will only proceed after approval.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Modification request (optional)</Label>
              <Textarea
                placeholder="e.g. Find a different venue, prefer outdoor garden setting…"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={3}
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                onClick={handleApprove}
                disabled={approveMutation.isPending}
                className="gap-2"
              >
                <ThumbsUp className="h-4 w-4" />
                Approve & Book
              </Button>

              {feedback && (
                <Button
                  variant="outline"
                  onClick={handleModify}
                  disabled={approveMutation.isPending}
                  className="gap-2"
                >
                  <Edit2 className="h-4 w-4" />
                  Modify Plan
                </Button>
              )}

              {rejectedVendors.length > 0 && (
                <Button
                  variant="destructive"
                  onClick={handleRejectVendors}
                  disabled={approveMutation.isPending}
                  className="gap-2"
                >
                  <XCircle className="h-4 w-4" />
                  Reject {rejectedVendors.length} Vendor(s) & Replan
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
