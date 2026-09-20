import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { FlaskConical, Play, RefreshCw, AlertTriangle } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

  const { data: results, refetch, isLoading } = useQuery({
    queryKey: ["eval-results"],
    queryFn: () => api.get<{ runs: Record<string,unknown>[]; summary: Record<string,unknown>; generated_at: string }>("/api/v1/eval/results"),
  });

  const runMutation = useMutation({
    mutationFn: () => api.post("/api/v1/eval/run", {
      rag_modes: ["none", "basic", "agentic"],
      llm_providers: ["gemini"],
      critic_enabled_values: [true, false],
      runs_per_scenario: 1,
    }),
    onSuccess: () => {
      setIsRunning(true);
      toast({ title: "Evaluation started", description: "Results will appear as runs complete." });
    },
    onError: () => toast({ variant: "destructive", title: "Failed to start evaluation" }),
  });

  const summary = results?.summary as Record<string, unknown> | undefined;
  const byRag = summary?.by_rag_mode as Record<string, Record<string, number>> | undefined;
  const runs = results?.runs ?? [];

  // Build chart data from summary
  const ragCompareData = byRag
    ? Object.entries(byRag).map(([mode, metrics]) => ({
        name: mode === "none" ? "No RAG" : mode === "basic" ? "Basic RAG" : "Agentic RAG",
        "Constraint Sat.": ((metrics.constraint_satisfaction ?? 0) * 100).toFixed(1),
        "Budget Adherence": ((metrics.budget_adherence ?? 0) * 100).toFixed(1),
        "Evidence Ground.": ((metrics.evidence_grounding ?? 0) * 100).toFixed(1),
        "Task Completion": ((metrics.task_completion ?? 0) * 100).toFixed(1),
      }))
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Evaluation Console</h2>
          <p className="text-sm text-muted-foreground">
            Compare RAG modes, LLM providers, and Critic ablation across 15 scenarios.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending || isRunning}
            className="gap-2"
          >
            <Play className="h-4 w-4" />
            {runMutation.isPending ? "Starting…" : "Run Evaluation"}
          </Button>
        </div>
      </div>

      <div className="rounded-md border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
        <AlertTriangle className="mr-2 inline-block h-4 w-4" />
        Evaluation metrics are computed from actual agent runs. No results are fabricated.
        Run the evaluation to see real measurements.
      </div>

      {runs.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <FlaskConical className="mx-auto mb-3 h-8 w-8 opacity-30" />
            <p className="text-sm text-muted-foreground">
              No evaluation results yet. Run the evaluation to compare RAG modes and LLMs.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Tabs defaultValue="comparison">
          <TabsList>
            <TabsTrigger value="comparison">RAG Comparison</TabsTrigger>
            <TabsTrigger value="runs">All Runs</TabsTrigger>
          </TabsList>

          <TabsContent value="comparison" className="space-y-4">
            {ragCompareData.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">RAG Mode Comparison</CardTitle>
                  <CardDescription>Average metrics across all scenarios (higher is better, %)</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={ragCompareData} barCategoryGap="30%">
                      <XAxis dataKey="name" />
                      <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                      <Tooltip formatter={(v) => `${v}%`} />
                      <Legend />
                      <Bar dataKey="Constraint Sat." fill="#6366f1" radius={[4,4,0,0]} />
                      <Bar dataKey="Budget Adherence" fill="#10b981" radius={[4,4,0,0]} />
                      <Bar dataKey="Evidence Ground." fill="#f59e0b" radius={[4,4,0,0]} />
                      <Bar dataKey="Task Completion" fill="#3b82f6" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}

            {/* Summary cards */}
            {byRag && (
              <div className="grid gap-4 sm:grid-cols-3">
                {Object.entries(byRag).map(([mode, m]) => (
                  <Card key={mode}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm capitalize">{mode.replace("_"," ")} RAG</CardTitle>
                        <Badge variant={mode === "agentic" ? "default" : "secondary"} className="text-xs">
                          {(m as Record<string,number>).count ?? 0} runs
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-1.5">
                      {Object.entries(METRIC_LABELS).map(([key, label]) => {
                        const val = (m as Record<string,number>)[key];
                        return val != null ? (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-muted-foreground">{label}</span>
                            <span className="font-medium">{(val * 100).toFixed(1)}%</span>
                          </div>
                        ) : null;
                      })}
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Avg Latency</span>
                        <span className="font-medium">
                          {(m as Record<string,number>).avg_latency_ms
                            ? `${((m as Record<string,number>).avg_latency_ms / 1000).toFixed(1)}s`
                            : "—"}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="runs">
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        {["Scenario", "RAG", "LLM", "Critic", "Run", "Constraint", "Budget", "Evidence", "Latency", "Error"].map((h) => (
                          <th key={h} className="px-3 py-2 text-left font-medium text-muted-foreground">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(runs as Record<string,unknown>[]).slice(0, 50).map((r, i) => (
                        <tr key={i} className="border-b hover:bg-muted/30">
                          <td className="px-3 py-2 font-mono">{String(r.scenario_id)}</td>
                          <td className="px-3 py-2">{String(r.rag_mode)}</td>
                          <td className="px-3 py-2">{String(r.llm_provider)}</td>
                          <td className="px-3 py-2">{r.critic_enabled ? "✓" : "✗"}</td>
                          <td className="px-3 py-2">{String(r.run_index)}</td>
                          <td className="px-3 py-2">{r.constraint_satisfaction != null ? `${(Number(r.constraint_satisfaction)*100).toFixed(0)}%` : "—"}</td>
                          <td className="px-3 py-2">{r.budget_adherence != null ? `${(Number(r.budget_adherence)*100).toFixed(0)}%` : "—"}</td>
                          <td className="px-3 py-2">{r.evidence_grounding != null ? `${(Number(r.evidence_grounding)*100).toFixed(0)}%` : "—"}</td>
                          <td className="px-3 py-2">{r.latency_ms != null ? `${(Number(r.latency_ms)/1000).toFixed(1)}s` : "—"}</td>
                          <td className="px-3 py-2 text-destructive">{r.error ? "⚠" : ""}</td>
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
  );
}
