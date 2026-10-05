import { useState } from "react";

import { useQuery, useMutation } from "@tanstack/react-query";

import {
  FlaskConical,
  Play,
  RefreshCw,
  AlertTriangle,
  Sparkles,
  Activity,
  Database,
  BrainCircuit,
  ShieldCheck,
  Clock3,
  ChevronRight,
} from "lucide-react";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

import {
  Card,
  CardContent,
} from "@/components/ui/card";

import { Button } from "@/components/ui/button";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

import { api } from "@/api/client";

import { toast } from "@/hooks/use-toast";

const METRIC_LABELS: Record<string, string> = {
  constraint_satisfaction: "Constraint Satisfaction",
  budget_adherence: "Budget Adherence",
  evidence_grounding: "Evidence Grounding",
  task_completion: "Task Completion",
};

export default function EvalConsolePage() {
  const [isRunning, setIsRunning] = useState(false);

  const {
    data: results,
    refetch,
    isLoading,
  } = useQuery({
    queryKey: ["eval-results"],
    queryFn: () =>
      api.get<{
        runs: Record<string, unknown>[];
        summary: Record<string, unknown>;
        generated_at: string;
      }>("/api/v1/eval/results"),
  });

  const runMutation = useMutation({
    mutationFn: () =>
      api.post("/api/v1/eval/run", {
        rag_modes: ["none", "basic", "agentic"],
        llm_providers: ["gemini"],
        critic_enabled_values: [true, false],
        runs_per_scenario: 1,
      }),

    onSuccess: () => {
      setIsRunning(true);

      toast({
        title: "Evaluation started",
        description:
          "Results will appear as runs complete.",
      });
    },

    onError: () =>
      toast({
        variant: "destructive",
        title: "Failed to start evaluation",
      }),
  });

  const summary =
    results?.summary as
      | Record<string, unknown>
      | undefined;

  const byRag =
    summary?.by_rag_mode as
      | Record<string, Record<string, number>>
      | undefined;

  const runs = results?.runs ?? [];

  const ragCompareData = byRag
    ? Object.entries(byRag).map(([mode, metrics]) => ({
        name:
          mode === "none"
            ? "No RAG"
            : mode === "basic"
            ? "Basic RAG"
            : "Agentic RAG",

        "Constraint Sat.": (
          (metrics.constraint_satisfaction ?? 0) * 100
        ).toFixed(1),

        "Budget Adherence": (
          (metrics.budget_adherence ?? 0) * 100
        ).toFixed(1),

        "Evidence Ground.": (
          (metrics.evidence_grounding ?? 0) * 100
        ).toFixed(1),

        "Task Completion": (
          (metrics.task_completion ?? 0) * 100
        ).toFixed(1),
      }))
    : [];

  return (
    <div className="min-h-full bg-[#f8f5ef]">
      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10 lg:py-12">

        {/* Header */}

        <div className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">

          <div>
            <div className="mb-4 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.25em] text-[#a77b3d]">
              <FlaskConical className="h-4 w-4" />
              Eventura Research Studio
            </div>

            <h1 className="font-serif text-5xl leading-tight tracking-tight text-[#241b2b]">
              Evaluation
              <span className="italic text-[#a77b3d]">
                {" "}studio.
              </span>
            </h1>

            <p className="mt-4 max-w-2xl text-base leading-7 text-[#756d74]">
              Measure how Eventura's planning architecture performs
              across retrieval strategies, models and reasoning
              configurations.
            </p>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => refetch()}
              className="border-[#dcd4c9] bg-white text-[#302732] hover:bg-[#f3eee6]"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>

            <Button
              onClick={() => runMutation.mutate()}
              disabled={
                runMutation.isPending || isRunning
              }
              className="bg-[#2b2030] text-white hover:bg-[#3a2b40]"
            >
              <Play className="mr-2 h-4 w-4" />

              {runMutation.isPending
                ? "Starting…"
                : "Run Evaluation"}
            </Button>
          </div>
        </div>

        {/* Research notice */}

        <div className="mb-8 flex items-start gap-4 rounded-2xl border border-[#dfcfae] bg-[#fbf5e8] px-5 py-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#ead9b5] text-[#8f6935]">
            <ShieldCheck className="h-4 w-4" />
          </div>

          <div>
            <p className="text-sm font-medium text-[#4d3b25]">
              Measurement integrity
            </p>

            <p className="mt-1 text-xs leading-5 text-[#806f58]">
              Evaluation metrics are computed from actual agent
              runs. No results are fabricated. Run the evaluation
              to generate measured results.
            </p>
          </div>
        </div>

        {/* Empty state */}

        {runs.length === 0 ? (
          <Card className="overflow-hidden rounded-3xl border-[#ded7cd] bg-white shadow-sm">
            <CardContent className="relative flex min-h-[460px] flex-col items-center justify-center px-6 text-center">

              <div className="absolute right-10 top-10 h-32 w-32 rounded-full bg-[#f5eee3] blur-2xl" />

              <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-[#2b2030] text-[#d5b477]">
                <FlaskConical className="h-8 w-8" />
              </div>

              <h2 className="relative mt-7 font-serif text-3xl text-[#241b2b]">
                The research bench is ready.
              </h2>

              <p className="relative mt-3 max-w-md text-sm leading-6 text-[#81777e]">
                Run an evaluation to compare RAG strategies,
                reasoning configurations and agent performance
                across your scenarios.
              </p>

              <Button
                onClick={() => runMutation.mutate()}
                disabled={
                  runMutation.isPending || isRunning
                }
                className="relative mt-7 rounded-full bg-[#2b2030] px-7 text-white hover:bg-[#3a2b40]"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Begin Evaluation
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="comparison">

            <div className="mb-6 flex items-center justify-between">
              <TabsList className="h-11 rounded-full bg-[#eee8df] p-1">
                <TabsTrigger
                  value="comparison"
                  className="rounded-full px-5 data-[state=active]:bg-white data-[state=active]:text-[#2b2030]"
                >
                  RAG Comparison
                </TabsTrigger>

                <TabsTrigger
                  value="runs"
                  className="rounded-full px-5 data-[state=active]:bg-white data-[state=active]:text-[#2b2030]"
                >
                  All Runs
                </TabsTrigger>
              </TabsList>

              {results?.generated_at && (
                <p className="hidden text-xs text-[#958b91] md:block">
                  Generated{" "}
                  {new Date(
                    results.generated_at
                  ).toLocaleString()}
                </p>
              )}
            </div>

            {/* Comparison */}

            <TabsContent
              value="comparison"
              className="space-y-7"
            >

              {/* Research dimensions */}

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

                {[
                  {
                    icon: Database,
                    label: "Retrieval",
                    value: "3 modes",
                  },
                  {
                    icon: BrainCircuit,
                    label: "Reasoning",
                    value: "Agentic",
                  },
                  {
                    icon: ShieldCheck,
                    label: "Validation",
                    value: "Critic",
                  },
                  {
                    icon: Activity,
                    label: "Scenarios",
                    value: "15",
                  },
                ].map((item) => {
                  const Icon = item.icon;

                  return (
                    <div
                      key={item.label}
                      className="rounded-2xl border border-[#ded7cd] bg-white p-5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#f4efe7] text-[#a77b3d]">
                          <Icon className="h-4 w-4" />
                        </div>

                        <ChevronRight className="h-4 w-4 text-[#c4bbb1]" />
                      </div>

                      <p className="mt-5 text-xs uppercase tracking-wider text-[#91878d]">
                        {item.label}
                      </p>

                      <p className="mt-1 font-serif text-2xl text-[#2b2030]">
                        {item.value}
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* Chart */}

              {ragCompareData.length > 0 && (
                <Card className="rounded-3xl border-[#ded7cd] bg-white shadow-sm">
                  <div className="border-b border-[#eee9e2] px-6 py-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[#a77b3d]">
                          Performance
                        </p>

                        <h2 className="mt-1 font-serif text-2xl text-[#241b2b]">
                          Retrieval strategy comparison
                        </h2>

                        <p className="mt-1 text-sm text-[#847b82]">
                          Average measurements across evaluated
                          scenarios.
                        </p>
                      </div>

                      <div className="hidden h-10 w-10 items-center justify-center rounded-full bg-[#f4efe7] text-[#a77b3d] sm:flex">
                        <Activity className="h-5 w-5" />
                      </div>
                    </div>
                  </div>

                  <CardContent className="pt-7">
                    <ResponsiveContainer
                      width="100%"
                      height={360}
                    >
                      <BarChart
                        data={ragCompareData}
                        barCategoryGap="28%"
                      >
                        <XAxis
                          dataKey="name"
                          axisLine={false}
                          tickLine={false}
                          tick={{
                            fill: "#756d74",
                            fontSize: 12,
                          }}
                        />

                        <YAxis
                          domain={[0, 100]}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={(v) =>
                            `${v}%`
                          }
                          tick={{
                            fill: "#91878d",
                            fontSize: 11,
                          }}
                        />

                        <Tooltip
                          cursor={{
                            fill: "#f8f5ef",
                          }}
                          formatter={(v) =>
                            `${v}%`
                          }
                        />

                        <Legend />

                        <Bar
                          dataKey="Constraint Sat."
                          fill="#2b2030"
                          radius={[6, 6, 0, 0]}
                        />

                        <Bar
                          dataKey="Budget Adherence"
                          fill="#a77b3d"
                          radius={[6, 6, 0, 0]}
                        />

                        <Bar
                          dataKey="Evidence Ground."
                          fill="#8b7891"
                          radius={[6, 6, 0, 0]}
                        />

                        <Bar
                          dataKey="Task Completion"
                          fill="#c9b8a0"
                          radius={[6, 6, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}

              {/* Summary cards */}

              {byRag && (
                <div>
                  <div className="mb-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-[#a77b3d]">
                      Results
                    </p>

                    <h2 className="mt-1 font-serif text-2xl text-[#241b2b]">
                      Measurement summary
                    </h2>
                  </div>

                  <div className="grid gap-5 lg:grid-cols-3">
                    {Object.entries(byRag).map(
                      ([mode, metrics]) => (
                        <Card
                          key={mode}
                          className={`rounded-2xl border-[#ded7cd] bg-white ${
                            mode === "agentic"
                              ? "ring-1 ring-[#c7a66d]"
                              : ""
                          }`}
                        >
                          <div className="p-6">

                            <div className="flex items-start justify-between">
                              <div>
                                <p className="text-xs uppercase tracking-[0.16em] text-[#9a8f95]">
                                  Retrieval mode
                                </p>

                                <h3 className="mt-1 font-serif text-2xl capitalize text-[#2b2030]">
                                  {mode.replace(
                                    "_",
                                    " "
                                  )}
                                </h3>
                              </div>

                              <span className="rounded-full bg-[#f4efe7] px-3 py-1 text-[11px] text-[#756d74]">
                                {(metrics.count ??
                                  0)}{" "}
                                runs
                              </span>
                            </div>

                            <div className="mt-7 space-y-4">
                              {Object.entries(
                                METRIC_LABELS
                              ).map(
                                ([key, label]) => {
                                  const val =
                                    metrics[
                                      key
                                    ];

                                  if (
                                    val == null
                                  ) {
                                    return null;
                                  }

                                  return (
                                    <div
                                      key={key}
                                    >
                                      <div className="mb-1.5 flex justify-between text-xs">
                                        <span className="text-[#756d74]">
                                          {label}
                                        </span>

                                        <span className="font-medium text-[#2b2030]">
                                          {(
                                            val *
                                            100
                                          ).toFixed(
                                            1
                                          )}
                                          %
                                        </span>
                                      </div>

                                      <div className="h-1.5 overflow-hidden rounded-full bg-[#eee9e2]">
                                        <div
                                          className="h-full rounded-full bg-[#a77b3d]"
                                          style={{
                                            width: `${Math.min(
                                              100,
                                              Math.max(
                                                0,
                                                val *
                                                  100
                                              )
                                            )}%`,
                                          }}
                                        />
                                      </div>
                                    </div>
                                  );
                                }
                              )}
                            </div>

                            <div className="mt-6 flex items-center justify-between border-t border-[#eee9e2] pt-4">
                              <div className="flex items-center gap-2 text-xs text-[#847b82]">
                                <Clock3 className="h-3.5 w-3.5" />
                                Avg latency
                              </div>

                              <span className="text-sm font-medium text-[#2b2030]">
                                {metrics.avg_latency_ms
                                  ? `${(
                                      metrics.avg_latency_ms /
                                      1000
                                    ).toFixed(1)}s`
                                  : "—"}
                              </span>
                            </div>
                          </div>
                        </Card>
                      )
                    )}
                  </div>
                </div>
              )}
            </TabsContent>

            {/* All Runs */}

            <TabsContent value="runs">
              <Card className="overflow-hidden rounded-3xl border-[#ded7cd] bg-white shadow-sm">
                <div className="border-b border-[#eee9e2] px-6 py-5">
                  <p className="text-xs uppercase tracking-[0.18em] text-[#a77b3d]">
                    Experiment log
                  </p>

                  <h2 className="mt-1 font-serif text-2xl text-[#241b2b]">
                    All evaluation runs
                  </h2>

                  <p className="mt-1 text-sm text-[#847b82]">
                    Raw measurements from the evaluation
                    harness.
                  </p>
                </div>

                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b bg-[#faf8f4]">
                          {[
                            "Scenario",
                            "RAG",
                            "LLM",
                            "Critic",
                            "Run",
                            "Constraint",
                            "Budget",
                            "Evidence",
                            "Latency",
                            "Error",
                          ].map((h) => (
                            <th
                              key={h}
                              className="whitespace-nowrap px-4 py-3 text-left font-medium text-[#756d74]"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>

                      <tbody>
                        {(
                          runs as Record<
                            string,
                            unknown
                          >[]
                        )
                          .slice(0, 50)
                          .map((r, i) => (
                            <tr
                              key={i}
                              className="border-b border-[#eee9e2] transition-colors hover:bg-[#faf8f4]"
                            >
                              <td className="px-4 py-3 font-mono text-[#4d424b]">
                                {String(
                                  r.scenario_id
                                )}
                              </td>

                              <td className="px-4 py-3">
                                {String(
                                  r.rag_mode
                                )}
                              </td>

                              <td className="px-4 py-3">
                                {String(
                                  r.llm_provider
                                )}
                              </td>

                              <td className="px-4 py-3">
                                {r.critic_enabled
                                  ? "✓"
                                  : "✗"}
                              </td>

                              <td className="px-4 py-3">
                                {String(
                                  r.run_index
                                )}
                              </td>

                              <td className="px-4 py-3">
                                {r.constraint_satisfaction !=
                                null
                                  ? `${(
                                      Number(
                                        r.constraint_satisfaction
                                      ) * 100
                                    ).toFixed(0)}%`
                                  : "—"}
                              </td>

                              <td className="px-4 py-3">
                                {r.budget_adherence !=
                                null
                                  ? `${(
                                      Number(
                                        r.budget_adherence
                                      ) * 100
                                    ).toFixed(0)}%`
                                  : "—"}
                              </td>

                              <td className="px-4 py-3">
                                {r.evidence_grounding !=
                                null
                                  ? `${(
                                      Number(
                                        r.evidence_grounding
                                      ) * 100
                                    ).toFixed(0)}%`
                                  : "—"}
                              </td>

                              <td className="px-4 py-3">
                                {r.latency_ms !=
                                null
                                  ? `${(
                                      Number(
                                        r.latency_ms
                                      ) / 1000
                                    ).toFixed(1)}s`
                                  : "—"}
                              </td>

                              <td className="px-4 py-3 text-red-600">
                                {r.error
                                  ? "⚠"
                                  : ""}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

          </Tabs>
        )}

      </div>
    </div>
  );
}