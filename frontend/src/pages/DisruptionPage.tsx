import { useState } from "react";

import {
  useParams,
  Link,
  useNavigate,
} from "react-router-dom";

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import {
  ArrowLeft,
  Zap,
  Ban,
  TrendingDown,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  CircleAlert,
  CheckCircle2,
  WalletCards,
} from "lucide-react";

import { Button } from "@/components/ui/button";

import {
  Input,
} from "@/components/ui/input";

import {
  Label,
} from "@/components/ui/label";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  sessionsApi,
} from "@/api/sessions";

import {
  formatINR,
} from "@/lib/utils";

import {
  toast,
} from "@/hooks/use-toast";

export default function DisruptionPage() {
  const { sessionId } =
    useParams<{ sessionId: string }>();

  const navigate = useNavigate();

  const qc = useQueryClient();

  const [disruptType, setDisruptType] =
    useState<
      "vendor_cancelled" | "budget_reduced"
    >("vendor_cancelled");

  const [selectedVendorId, setSelectedVendorId] =
    useState("");

  const [reductionPct, setReductionPct] =
    useState("15");

  const { data: session } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () =>
      sessionsApi.get(sessionId!),
    enabled: !!sessionId,
  });

  const disruptMutation = useMutation({
    mutationFn: (
      data: Parameters<
        typeof sessionsApi.disrupt
      >[1]
    ) =>
      sessionsApi.disrupt(
        sessionId!,
        data
      ),

    onSuccess: (result) => {
      qc.invalidateQueries({
        queryKey: ["session", sessionId],
      });

      toast({
        title: "Disruption triggered",
        description: result.message,
      });

      navigate(`/events/${sessionId}`);
    },

    onError: () =>
      toast({
        variant: "destructive",
        title: "Disruption failed",
      }),
  });

  function handleDisrupt() {
    if (disruptType === "vendor_cancelled") {
      if (!selectedVendorId) {
        toast({
          variant: "destructive",
          title: "Select a vendor to cancel",
        });

        return;
      }

      disruptMutation.mutate({
        disruption_type:
          "vendor_cancelled",

        vendor_id:
          selectedVendorId,

        reason:
          "Vendor cancelled due to double booking",
      });
    } else {
      const pct =
        parseFloat(reductionPct);

      if (
        isNaN(pct) ||
        pct <= 0 ||
        pct >= 100
      ) {
        toast({
          variant: "destructive",
          title:
            "Enter a valid reduction % (1-99)",
        });

        return;
      }

      disruptMutation.mutate({
        disruption_type:
          "budget_reduced",

        reduction_pct: pct,
      });
    }
  }

  const req =
    session?.requirements as
      | Record<string, unknown>
      | undefined;

  const currentBudget =
    req?.budget as number | undefined;

  const previewBudget =
    currentBudget &&
    disruptType === "budget_reduced"
      ? currentBudget *
        (1 -
          parseFloat(
            reductionPct || "0"
          ) /
            100)
      : null;

  const selectedVendor =
    session?.vendor_selections?.find(
      (vendor) =>
        vendor.vendor_id ===
        selectedVendorId
    );

  return (
    <div className="min-h-full bg-[#f8f5ef]">
      <div className="mx-auto max-w-6xl px-6 py-10 lg:px-10 lg:py-12">

        {/* Top navigation */}

        <div className="mb-10 flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            asChild
            className="text-[#756d74] hover:bg-[#eee8df] hover:text-[#2b2030]"
          >
            <Link
              to={`/events/${sessionId}`}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Event overview
            </Link>
          </Button>

          <span className="text-[#c8c0b8]">
            /
          </span>

          <span className="text-sm text-[#91878d]">
            Recovery Studio
          </span>
        </div>

        {/* Hero */}

        <div className="mb-12 max-w-4xl">
          <div className="mb-5 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.25em] text-[#a77b3d]">
            <Zap className="h-4 w-4" />
            Eventura Recovery Studio
          </div>

          <h1 className="font-serif text-5xl leading-[1.05] tracking-tight text-[#241b2b] md:text-6xl">
            Something changed.
            <span className="block italic text-[#a77b3d]">
              Eventura adapts.
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-base leading-7 text-[#756d74] md:text-lg">
            Real events rarely go exactly according to plan.
            Simulate a disruption and see how Eventura's agents
            detect the change, reason about its impact and
            selectively replan what needs to change.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1fr_340px]">

          {/* Main simulator */}

          <div className="space-y-8">

            <section>
              <div className="mb-5">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#a77b3d]">
                  01
                </p>

                <h2 className="mt-1 font-serif text-2xl text-[#241b2b]">
                  Choose what changed
                </h2>

                <p className="mt-1 text-sm text-[#847b82]">
                  Introduce a realistic event disruption.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">

                <button
                  type="button"
                  onClick={() =>
                    setDisruptType(
                      "vendor_cancelled"
                    )
                  }
                  className={`group relative rounded-2xl border p-6 text-left transition-all duration-300 ${
                    disruptType ===
                    "vendor_cancelled"
                      ? "border-[#a77b3d] bg-[#2b2030] text-white shadow-lg"
                      : "border-[#ded7cd] bg-white hover:-translate-y-1 hover:border-[#b99a6b] hover:shadow-md"
                  }`}
                >
                  {disruptType ===
                    "vendor_cancelled" && (
                    <div className="absolute right-5 top-5 flex h-6 w-6 items-center justify-center rounded-full bg-[#d0ad6e]">
                      <CheckCircle2 className="h-3.5 w-3.5 text-[#2b2030]" />
                    </div>
                  )}

                  <div
                    className={`mb-8 flex h-11 w-11 items-center justify-center rounded-full ${
                      disruptType ===
                      "vendor_cancelled"
                        ? "bg-white/10 text-[#d8b87b]"
                        : "bg-[#f4efe7] text-[#a77b3d]"
                    }`}
                  >
                    <Ban className="h-5 w-5" />
                  </div>

                  <h3 className="font-serif text-2xl">
                    A vendor cancels
                  </h3>

                  <p
                    className={`mt-2 max-w-sm text-sm leading-6 ${
                      disruptType ===
                      "vendor_cancelled"
                        ? "text-white/60"
                        : "text-[#847b82]"
                    }`}
                  >
                    A vendor suddenly becomes unavailable.
                    Eventura should replace the affected
                    vendor without disturbing the rest of
                    the plan.
                  </p>

                  <div
                    className={`mt-5 flex items-center gap-2 text-xs ${
                      disruptType ===
                      "vendor_cancelled"
                        ? "text-[#d8b87b]"
                        : "text-[#a77b3d]"
                    }`}
                  >
                    Select an affected vendor
                    <ArrowRight className="h-3.5 w-3.5" />
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setDisruptType(
                      "budget_reduced"
                    )
                  }
                  className={`group relative rounded-2xl border p-6 text-left transition-all duration-300 ${
                    disruptType ===
                    "budget_reduced"
                      ? "border-[#a77b3d] bg-[#2b2030] text-white shadow-lg"
                      : "border-[#ded7cd] bg-white hover:-translate-y-1 hover:border-[#b99a6b] hover:shadow-md"
                  }`}
                >
                  {disruptType ===
                    "budget_reduced" && (
                    <div className="absolute right-5 top-5 flex h-6 w-6 items-center justify-center rounded-full bg-[#d0ad6e]">
                      <CheckCircle2 className="h-3.5 w-3.5 text-[#2b2030]" />
                    </div>
                  )}

                  <div
                    className={`mb-8 flex h-11 w-11 items-center justify-center rounded-full ${
                      disruptType ===
                      "budget_reduced"
                        ? "bg-white/10 text-[#d8b87b]"
                        : "bg-[#f4efe7] text-[#a77b3d]"
                    }`}
                  >
                    <TrendingDown className="h-5 w-5" />
                  </div>

                  <h3 className="font-serif text-2xl">
                    The budget changes
                  </h3>

                  <p
                    className={`mt-2 max-w-sm text-sm leading-6 ${
                      disruptType ===
                      "budget_reduced"
                        ? "text-white/60"
                        : "text-[#847b82]"
                    }`}
                  >
                    Your available budget suddenly
                    decreases. Eventura should find ways to
                    rebalance the affected categories.
                  </p>

                  <div
                    className={`mt-5 flex items-center gap-2 text-xs ${
                      disruptType ===
                      "budget_reduced"
                        ? "text-[#d8b87b]"
                        : "text-[#a77b3d]"
                    }`}
                  >
                    Set the new constraint
                    <ArrowRight className="h-3.5 w-3.5" />
                  </div>
                </button>
              </div>
            </section>

            {/* Configuration */}

            <section>
              <div className="mb-5">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#a77b3d]">
                  02
                </p>

                <h2 className="mt-1 font-serif text-2xl text-[#241b2b]">
                  Define the disruption
                </h2>
              </div>

              <div className="rounded-2xl border border-[#ded7cd] bg-white p-6 shadow-sm">

                {disruptType ===
                  "vendor_cancelled" && (
                  <div className="space-y-4">
                    <div>
                      <Label className="text-sm text-[#302732]">
                        Vendor to cancel
                      </Label>

                      <p className="mt-1 text-xs text-[#91878d]">
                        Eventura will mark this vendor as
                        unavailable and begin selective
                        replanning.
                      </p>
                    </div>

                    {session?.vendor_selections
                      ?.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-[#d8d0c6] bg-[#faf8f4] px-5 py-6 text-center">
                        <CircleAlert className="mx-auto mb-2 h-5 w-5 text-[#a77b3d]" />

                        <p className="text-sm text-[#756d74]">
                          No vendors selected yet.
                        </p>
                      </div>
                    ) : (
                      <Select
                        value={
                          selectedVendorId
                        }
                        onValueChange={
                          setSelectedVendorId
                        }
                      >
                        <SelectTrigger className="h-12 border-[#ded7cd] bg-[#faf8f4]">
                          <SelectValue placeholder="Choose a vendor…" />
                        </SelectTrigger>

                        <SelectContent>
                          {session?.vendor_selections?.map(
                            (sel) => (
                              <SelectItem
                                key={
                                  sel.vendor_id
                                }
                                value={
                                  sel.vendor_id
                                }
                              >
                                {sel.name} (
                                {sel.category.replace(
                                  "_",
                                  " "
                                )}) —{" "}
                                {formatINR(
                                  sel.final_price ??
                                    sel.quoted_price
                                )}
                              </SelectItem>
                            )
                          )}
                        </SelectContent>
                      </Select>
                    )}

                    {selectedVendor && (
                      <div className="rounded-xl bg-[#f7f2ea] p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-xs uppercase tracking-wider text-[#9a8f95]">
                              Selected vendor
                            </p>

                            <p className="mt-1 font-serif text-lg text-[#2b2030]">
                              {selectedVendor.name}
                            </p>
                          </div>

                          <Ban className="h-5 w-5 text-[#a77b3d]" />
                        </div>

                        <p className="mt-2 text-xs text-[#756d74]">
                          This vendor will be treated as
                          unavailable during replanning.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {disruptType ===
                  "budget_reduced" && (
                  <div className="space-y-5">
                    <div>
                      <Label className="text-sm text-[#302732]">
                        Budget reduction
                      </Label>

                      <p className="mt-1 text-xs text-[#91878d]">
                        Introduce a new financial constraint
                        and let Eventura rebalance the plan.
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <Input
                        type="number"
                        min={1}
                        max={50}
                        value={reductionPct}
                        onChange={(e) =>
                          setReductionPct(
                            e.target.value
                          )
                        }
                        className="h-12 w-28 border-[#ded7cd] bg-[#faf8f4] text-center text-lg"
                      />

                      <span className="text-sm text-[#756d74]">
                        % reduction
                      </span>
                    </div>

                    {currentBudget &&
                      previewBudget && (
                        <div className="grid gap-3 sm:grid-cols-3">
                          <div className="rounded-xl bg-[#f7f3ed] p-4">
                            <p className="text-[11px] uppercase tracking-wider text-[#91878d]">
                              Current budget
                            </p>

                            <p className="mt-2 font-serif text-xl text-[#2b2030]">
                              {formatINR(
                                currentBudget
                              )}
                            </p>
                          </div>

                          <div className="rounded-xl bg-[#f7f3ed] p-4">
                            <p className="text-[11px] uppercase tracking-wider text-[#91878d]">
                              New budget
                            </p>

                            <p className="mt-2 font-serif text-xl text-[#a77b3d]">
                              {formatINR(
                                previewBudget
                              )}
                            </p>
                          </div>

                          <div className="rounded-xl bg-[#f7f3ed] p-4">
                            <p className="text-[11px] uppercase tracking-wider text-[#91878d]">
                              Reduction
                            </p>

                            <p className="mt-2 font-serif text-xl text-[#9b5e54]">
                              −
                              {formatINR(
                                currentBudget -
                                  previewBudget
                              )}
                            </p>
                          </div>
                        </div>
                      )}
                  </div>
                )}
              </div>
            </section>

            {/* Action */}

            <section className="rounded-2xl bg-[#2b2030] p-6 text-white shadow-lg md:p-7">
              <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[#d3b272]">
                    <Sparkles className="h-3.5 w-3.5" />
                    Agentic recovery
                  </div>

                  <h2 className="mt-2 font-serif text-2xl">
                    Let Eventura adapt the plan.
                  </h2>

                  <p className="mt-2 max-w-lg text-sm leading-6 text-white/55">
                    The system will identify what is affected,
                    preserve unaffected decisions and replan
                    only where necessary.
                  </p>
                </div>

                <Button
                  onClick={handleDisrupt}
                  disabled={
                    disruptMutation.isPending
                  }
                  className="h-12 shrink-0 rounded-full bg-[#d0ad6e] px-6 text-[#241b2b] hover:bg-[#dfc084]"
                >
                  {disruptMutation.isPending ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                      Adapting…
                    </>
                  ) : (
                    <>
                      <Zap className="mr-2 h-4 w-4" />
                      Trigger Disruption
                    </>
                  )}
                </Button>
              </div>
            </section>
          </div>

          {/* Right explanation panel */}

          <aside className="lg:pt-4">
            <div className="sticky top-8 overflow-hidden rounded-3xl bg-[#2b2030] text-white shadow-xl">

              <div className="relative h-52 overflow-hidden">
                <img
                  src="https://images.unsplash.com/photo-1507504031003-b417219a0fde?auto=format&fit=crop&w=900&q=80"
                  alt="Event planning table"
                  className="h-full w-full object-cover opacity-45"
                />

                <div className="absolute inset-0 bg-gradient-to-t from-[#2b2030] via-[#2b2030]/30 to-transparent" />

                <div className="absolute bottom-6 left-6">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#d3b272]">
                    Resilience
                  </p>

                  <h2 className="mt-1 font-serif text-2xl">
                    Plans can change.
                  </h2>
                </div>
              </div>

              <div className="p-6">
                <p className="text-sm leading-6 text-white/60">
                  Eventura is designed to respond to changing
                  constraints instead of starting the planning
                  process from scratch.
                </p>

                <div className="my-6 space-y-5 border-y border-white/10 py-6">

                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-[#d3b272]">
                      <CircleAlert className="h-4 w-4" />
                    </div>

                    <div>
                      <p className="text-sm font-medium">
                        Detect
                      </p>

                      <p className="mt-1 text-xs leading-5 text-white/45">
                        Identify the changed constraint.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-[#d3b272]">
                      <WalletCards className="h-4 w-4" />
                    </div>

                    <div>
                      <p className="text-sm font-medium">
                        Assess
                      </p>

                      <p className="mt-1 text-xs leading-5 text-white/45">
                        Determine which decisions are affected.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-[#d3b272]">
                      <RefreshCw className="h-4 w-4" />
                    </div>

                    <div>
                      <p className="text-sm font-medium">
                        Replan
                      </p>

                      <p className="mt-1 text-xs leading-5 text-white/45">
                        Change only what needs to change.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-[#d3b272]">
                      <ShieldCheck className="h-4 w-4" />
                    </div>

                    <div>
                      <p className="text-sm font-medium">
                        Protect
                      </p>

                      <p className="mt-1 text-xs leading-5 text-white/45">
                        Preserve unaffected planning decisions.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-white/40">
                  <Sparkles className="h-3.5 w-3.5 text-[#d3b272]" />
                  Agentic selective replanning
                </div>
              </div>
            </div>
          </aside>

        </div>
      </div>
    </div>
  );
}