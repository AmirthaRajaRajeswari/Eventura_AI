import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Zap, Ban, TrendingDown } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { sessionsApi } from "@/api/sessions";
import { formatINR } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";

export default function DisruptionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [disruptType, setDisruptType] = useState<"vendor_cancelled" | "budget_reduced">("vendor_cancelled");
  const [selectedVendorId, setSelectedVendorId] = useState("");
  const [reductionPct, setReductionPct] = useState("15");

  const { data: session } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
  });

  const disruptMutation = useMutation({
    mutationFn: (data: Parameters<typeof sessionsApi.disrupt>[1]) =>
      sessionsApi.disrupt(sessionId!, data),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["session", sessionId] });
      toast({
        title: "Disruption triggered",
        description: result.message,
      });
      navigate(`/events/${sessionId}`);
    },
    onError: () => toast({ variant: "destructive", title: "Disruption failed" }),
  });

  function handleDisrupt() {
    if (disruptType === "vendor_cancelled") {
      if (!selectedVendorId) {
        toast({ variant: "destructive", title: "Select a vendor to cancel" });
        return;
      }
      disruptMutation.mutate({
        disruption_type: "vendor_cancelled",
        vendor_id: selectedVendorId,
        reason: "Vendor cancelled due to double booking",
      });
    } else {
      const pct = parseFloat(reductionPct);
      if (isNaN(pct) || pct <= 0 || pct >= 100) {
        toast({ variant: "destructive", title: "Enter a valid reduction % (1-99)" });
        return;
      }
      disruptMutation.mutate({
        disruption_type: "budget_reduced",
        reduction_pct: pct,
      });
    }
  }

  const req = session?.requirements as Record<string, unknown> | undefined;
  const currentBudget = req?.budget as number | undefined;
  const previewBudget = currentBudget && disruptType === "budget_reduced"
    ? currentBudget * (1 - parseFloat(reductionPct || "0") / 100)
    : null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/events/${sessionId}`}><ArrowLeft className="mr-2 h-4 w-4" />Dashboard</Link>
        </Button>
        <Separator orientation="vertical" className="h-5" />
        <h2 className="text-xl font-bold">Disruption Simulator</h2>
        <Badge variant="warning" className="gap-1">
          <Zap className="h-3 w-3" /> Demo Tool
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Simulate a Disruption</CardTitle>
          <CardDescription>
            Test how the system handles real-world disruptions. The agents will detect the change,
            identify affected categories, and selectively replan without disturbing unaffected vendors.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>Disruption Type</Label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDisruptType("vendor_cancelled")}
                className={`flex flex-col gap-1.5 rounded-lg border p-4 text-left transition-colors ${
                  disruptType === "vendor_cancelled"
                    ? "border-primary bg-primary/5"
                    : "hover:border-primary/40"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Ban className="h-4 w-4 text-destructive" />
                  <span className="text-sm font-medium">Vendor Cancelled</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  A vendor cancels their commitment. Agents replan that category only.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setDisruptType("budget_reduced")}
                className={`flex flex-col gap-1.5 rounded-lg border p-4 text-left transition-colors ${
                  disruptType === "budget_reduced"
                    ? "border-primary bg-primary/5"
                    : "hover:border-primary/40"
                }`}
              >
                <div className="flex items-center gap-2">
                  <TrendingDown className="h-4 w-4 text-orange-500" />
                  <span className="text-sm font-medium">Budget Reduced</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Budget decreases by a percentage. Over-budget categories are replanned.
                </p>
              </button>
            </div>
          </div>

          {disruptType === "vendor_cancelled" && (
            <div className="space-y-2">
              <Label>Select Vendor to Cancel</Label>
              {session?.vendor_selections.length === 0 ? (
                <p className="text-sm text-muted-foreground">No vendors selected yet</p>
              ) : (
                <Select value={selectedVendorId} onValueChange={setSelectedVendorId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a vendor…" />
                  </SelectTrigger>
                  <SelectContent>
                    {session?.vendor_selections.map((sel) => (
                      <SelectItem key={sel.vendor_id} value={sel.vendor_id}>
                        {sel.name} ({sel.category.replace("_", " ")}) — {formatINR(sel.final_price ?? sel.quoted_price)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}

          {disruptType === "budget_reduced" && (
            <div className="space-y-2">
              <Label>Reduction Percentage</Label>
              <div className="flex items-center gap-3">
                <Input
                  type="number"
                  min={1}
                  max={50}
                  value={reductionPct}
                  onChange={(e) => setReductionPct(e.target.value)}
                  className="w-32"
                />
                <span className="text-sm text-muted-foreground">%</span>
              </div>
              {currentBudget && previewBudget && (
                <div className="rounded-md border bg-muted/50 p-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Current budget:</span>
                    <span className="font-medium">{formatINR(currentBudget)}</span>
                  </div>
                  <div className="flex justify-between text-orange-700">
                    <span>After reduction:</span>
                    <span className="font-semibold">{formatINR(previewBudget)}</span>
                  </div>
                  <div className="flex justify-between text-destructive">
                    <span>Reduction amount:</span>
                    <span className="font-medium">−{formatINR(currentBudget - previewBudget)}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          <Button
            onClick={handleDisrupt}
            disabled={disruptMutation.isPending}
            variant="destructive"
            className="w-full gap-2"
          >
            <Zap className="h-4 w-4" />
            {disruptMutation.isPending ? "Triggering…" : "Trigger Disruption"}
          </Button>
        </CardContent>
      </Card>

      <Card className="border-blue-200 bg-blue-50/50">
        <CardContent className="pt-4 pb-4">
          <p className="text-xs text-blue-800">
            <strong>Demo note:</strong> This simulator directly triggers the agents' disruption
            handling logic. Watch the Agent Activity feed to see selective replanning in action.
            The system will only replan affected categories — unaffected vendors stay booked.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
