import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Loader2, Info } from "lucide-react";
import { toast } from "@/hooks/use-toast";

const schema = z.object({
  prompt: z.string().min(10, "Please describe your event in at least 10 characters"),
  rag_mode: z.enum(["none", "basic", "agentic"]),
  llm_provider: z.enum(["gemini", "groq", "ollama"]),
});

type FormValues = z.infer<typeof schema>;

const demoPrompts = [
  "I want to organise a Tamil wedding in Chennai for 500 guests with a budget of ₹15 lakh on December 20 for two days.",
  "Plan a birthday party for my daughter turning 10 in Bangalore, 50 guests, budget ₹80,000 on January 15.",
  "Organise a college cultural fest in Mumbai for 2000 students with a budget of ₹8 lakh over 3 days in February.",
  "Wedding in Chennai for 800 guests with budget ₹5 lakh — premium venue required. (infeasibility demo)",
];

export default function NewEventPage() {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      rag_mode: "agentic",
      llm_provider: "gemini",
    },
  });

  const ragMode = watch("rag_mode");
  const llmProvider = watch("llm_provider");

  async function onSubmit(data: FormValues) {
    try {
      const resp = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: data.prompt,
          rag_mode: data.rag_mode,
          llm_provider: data.llm_provider,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${resp.status}`);
      }

      const session = await resp.json();
      toast({ title: "Event session created", description: `Session ${session.id.slice(0, 8)}…` });
      navigate(`/events/${session.id}`);
    } catch (e: unknown) {
      toast({
        variant: "destructive",
        title: "Could not create session",
        description: e instanceof Error ? e.message : "Unknown error",
      });
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">New Event</h2>
        <p className="text-muted-foreground">
          Describe your event in natural language and let the AI agents plan it
          for you.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Demo vendor and pricing data are synthetic and used for demonstration
          purposes only.
        </span>
      </div>

      {/* Demo prompts */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Demo Scenarios</CardTitle>
          <CardDescription>Click a scenario to populate the prompt</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {demoPrompts.map((prompt, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setValue("prompt", prompt)}
              className="w-full rounded-md border border-dashed px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
            >
              {prompt}
            </button>
          ))}
        </CardContent>
      </Card>

      {/* Main form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Event Description</CardTitle>
            <CardDescription>
              Describe your event including type, city, guest count, budget,
              date, and any preferences.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="prompt">Event prompt</Label>
              <Textarea
                id="prompt"
                rows={4}
                placeholder="I want to organise a Tamil wedding in Chennai for 500 guests..."
                {...register("prompt")}
              />
              {errors.prompt && (
                <p className="text-xs text-destructive">{errors.prompt.message}</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Agent Configuration</CardTitle>
            <CardDescription>
              Configure how the agents retrieve information and which LLM to use.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            {/* RAG mode */}
            <div className="space-y-2">
              <Label>RAG Mode</Label>
              <Select
                value={ragMode}
                onValueChange={(v) => setValue("rag_mode", v as FormValues["rag_mode"])}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (no retrieval)</SelectItem>
                  <SelectItem value="basic">Basic RAG</SelectItem>
                  <SelectItem value="agentic">Agentic RAG ✦</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {ragMode === "none" && "LLM answers from its own knowledge — baseline."}
                {ragMode === "basic" && "Fixed top-k retrieval without query refinement."}
                {ragMode === "agentic" && "Dynamic retrieval with source routing and sufficiency checking."}
              </p>
            </div>

            {/* LLM provider */}
            <div className="space-y-2">
              <Label>LLM Provider</Label>
              <Select
                value={llmProvider}
                onValueChange={(v) => setValue("llm_provider", v as FormValues["llm_provider"])}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gemini">Gemini (Primary)</SelectItem>
                  <SelectItem value="groq">Groq / Llama (Secondary)</SelectItem>
                  <SelectItem value="ollama">Ollama (Local)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" className="w-full gap-2" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creating session…
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Start Planning with AI Agents
            </>
          )}
        </Button>
      </form>
    </div>
  );
}
