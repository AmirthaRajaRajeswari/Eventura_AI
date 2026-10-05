import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";

import {
  Sparkles,
  Loader2,
  Heart,
  Cake,
  GraduationCap,
  ArrowRight,
  SlidersHorizontal,
  Check,
  Search,
  WalletCards,
} from "lucide-react";

import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { toast } from "@/hooks/use-toast";

const schema = z.object({
  prompt: z
    .string()
    .min(10, "Please describe your event in at least 10 characters"),
  rag_mode: z.enum(["none", "basic", "agentic"]),
  llm_provider: z.enum(["gemini", "groq", "ollama"]),
});

type FormValues = z.infer<typeof schema>;

const inspirationIdeas = [
  {
    id: "wedding",
    title: "Tamil Wedding",
    description: "A traditional celebration with a touch of elegance.",
    prompt:
      "I want to organise a Tamil wedding in Chennai for 500 guests with a budget of ₹15 lakh on December 20 for two days.",
    icon: Heart,
  },
  {
    id: "birthday",
    title: "Birthday Celebration",
    description: "A memorable birthday experience for someone special.",
    prompt:
      "Plan a birthday party for my daughter turning 10 in Bangalore, 50 guests, budget ₹80,000 on January 15.",
    icon: Cake,
  },
  {
    id: "college",
    title: "College Fest",
    description: "A high-energy celebration for the campus community.",
    prompt:
      "Organise a college cultural fest in Mumbai for 2000 students with a budget of ₹8 lakh over 3 days in February.",
    icon: GraduationCap,
  },
  {
    id: "budget",
    title: "Budget Challenge",
    description: "See how Eventura handles an impossible constraint.",
    prompt:
      "Wedding in Chennai for 800 guests with budget ₹5 lakh — premium venue required. (infeasibility demo)",
    icon: WalletCards,
  },
];

export default function NewEventPage() {
  const navigate = useNavigate();

  const [selectedIdea, setSelectedIdea] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

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
  const prompt = watch("prompt");

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

      toast({
        title: "Event session created",
        description: `Session ${session.id.slice(0, 8)}…`,
      });

      navigate(`/events/${session.id}`);
    } catch (e: unknown) {
      toast({
        variant: "destructive",
        title: "Could not create session",
        description:
          e instanceof Error ? e.message : "Unknown error",
      });
    }
  }

  function chooseIdea(id: string, ideaPrompt: string) {
    setSelectedIdea(id);

    setValue("prompt", ideaPrompt, {
      shouldValidate: true,
    });
  }

  return (
    <div className="min-h-full bg-[#f8f5ef] text-[#241b2b]">

      <div className="mx-auto w-full max-w-[1450px] px-6 py-10 lg:px-10 lg:py-12">

        <form onSubmit={handleSubmit(onSubmit)}>

          <div className="grid items-stretch gap-10 lg:grid-cols-[minmax(0,1fr)_390px]">

            {/* =====================================================
                MAIN CONTENT
            ====================================================== */}

            <main className="flex min-w-0 flex-col">

              {/* HERO */}

              <section className="mb-12 max-w-3xl">

                <h1 className="font-serif text-5xl leading-[1.02] tracking-tight md:text-7xl">
                  Plan something
                  <span className="block italic text-[#a77b3d]">
                    unforgettable.
                  </span>
                </h1>

                <p className="mt-7 max-w-2xl text-base leading-7 text-[#756d74] md:text-lg">
                  Tell us what you're imagining. Eventura's planning team
                  will understand your priorities, research the possibilities,
                  and shape everything into one thoughtful event plan.
                </p>

              </section>

              {/* VISION */}

              <section className="mb-12">

                <div className="mb-5">

                  <h2 className="font-serif text-3xl text-[#241b2b]">
                    Tell us your vision
                  </h2>

                  <p className="mt-2 text-sm text-[#847b82]">
                    Start with whatever you already know. Eventura will work
                    with the details you provide.
                  </p>

                </div>

                <div className="relative overflow-hidden rounded-2xl border border-[#ded7cd] bg-white shadow-sm">

                  <Textarea
                    id="prompt"
                    rows={9}
                    maxLength={1000}
                    placeholder="For example: I want to organise a Tamil wedding in Chennai for 500 guests with a budget of ₹15 lakh..."
                    className="min-h-[240px] resize-none border-0 bg-transparent px-6 py-6 pb-12 text-base leading-7 text-[#302732] placeholder:text-[#aaa1a6] focus-visible:ring-0"
                    {...register("prompt")}
                  />

                  <div className="pointer-events-none absolute bottom-3 right-5">
                    <span className="text-xs text-[#aaa1a6]">
                      {prompt?.length || 0} / 1000
                    </span>
                  </div>

                </div>

                {errors.prompt && (
                  <p className="mt-2 text-xs text-red-600">
                    {errors.prompt.message}
                  </p>
                )}

              </section>

              {/* INSPIRATION */}

              <section className="mb-12">

                <div className="mb-6 flex items-end justify-between">

                  <div>
                    <h2 className="font-serif text-3xl text-[#241b2b]">
                      Need some inspiration?
                    </h2>

                    <p className="mt-2 text-sm text-[#847b82]">
                      Choose an idea to give Eventura a starting point.
                    </p>
                  </div>

                </div>

                <div className="grid gap-4 md:grid-cols-2">

                  {inspirationIdeas.map((idea) => {
                    const Icon = idea.icon;
                    const isSelected = selectedIdea === idea.id;

                    return (
                      <button
                        key={idea.id}
                        type="button"
                        onClick={() =>
                          chooseIdea(idea.id, idea.prompt)
                        }
                        className={`group relative min-h-[155px] rounded-2xl border p-6 text-left transition-all duration-300 ${
                          isSelected
                            ? "border-[#a77b3d] bg-[#2b2030] text-white shadow-lg"
                            : "border-[#ded7cd] bg-white text-[#241b2b] hover:-translate-y-1 hover:border-[#b99a6b] hover:shadow-md"
                        }`}
                      >

                        {isSelected && (
                          <div className="absolute right-5 top-5 flex h-7 w-7 items-center justify-center rounded-full bg-[#d0ad6e]">
                            <Check className="h-4 w-4 text-[#241b2b]" />
                          </div>
                        )}

                        <div
                          className={`mb-7 flex h-10 w-10 items-center justify-center rounded-full ${
                            isSelected
                              ? "bg-white/10 text-[#d7b77c]"
                              : "bg-[#f4efe7] text-[#a77b3d]"
                          }`}
                        >
                          <Icon className="h-5 w-5" />
                        </div>

                        <div className="flex items-end justify-between gap-4">

                          <div>

                            <h3 className="font-serif text-xl">
                              {idea.title}
                            </h3>

                            <p
                              className={`mt-1 max-w-sm text-xs leading-5 ${
                                isSelected
                                  ? "text-white/65"
                                  : "text-[#847b82]"
                              }`}
                            >
                              {idea.description}
                            </p>

                          </div>

                          <ArrowRight
                            className={`mb-1 h-4 w-4 shrink-0 transition-transform group-hover:translate-x-1 ${
                              isSelected
                                ? "text-[#d4b47a]"
                                : "text-[#b38a4e]"
                            }`}
                          />

                        </div>

                      </button>
                    );
                  })}

                </div>

              </section>

              {/* ADVANCED SETTINGS */}

              <section className="mt-auto">

                <button
                  type="button"
                  onClick={() =>
                    setShowAdvanced(!showAdvanced)
                  }
                  className="flex w-full items-center justify-between rounded-xl border border-[#ded7cd] bg-white px-5 py-4 text-left transition-colors hover:border-[#b99a6b]"
                >

                  <div className="flex items-center gap-3">

                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#f4efe7] text-[#a77b3d]">
                      <SlidersHorizontal className="h-4 w-4" />
                    </div>

                    <div>
                      <p className="text-sm font-medium text-[#302732]">
                        Planning preferences
                      </p>

                      <p className="text-xs text-[#91878d]">
                        Advanced AI configuration
                      </p>
                    </div>

                  </div>

                  <span className="text-xs text-[#a77b3d]">
                    {showAdvanced ? "Hide" : "Customize"}
                  </span>

                </button>

                {showAdvanced && (
                  <div className="mt-3 grid gap-4 rounded-xl border border-[#ded7cd] bg-white p-5 sm:grid-cols-2">

                    <div className="space-y-2">

                      <Label className="text-xs uppercase tracking-wider text-[#756d74]">
                        Retrieval strategy
                      </Label>

                      <Select
                        value={ragMode}
                        onValueChange={(v) =>
                          setValue(
                            "rag_mode",
                            v as FormValues["rag_mode"]
                          )
                        }
                      >
                        <SelectTrigger className="h-11 border-[#ded7cd] bg-[#faf8f4]">
                          <SelectValue />
                        </SelectTrigger>

                        <SelectContent>

                          <SelectItem value="none">
                            None — LLM only
                          </SelectItem>

                          <SelectItem value="basic">
                            Basic RAG
                          </SelectItem>

                          <SelectItem value="agentic">
                            Agentic RAG ✦
                          </SelectItem>

                        </SelectContent>

                      </Select>

                      <p className="text-xs leading-5 text-[#91878d]">
                        {ragMode === "none" &&
                          "LLM answers from its own knowledge — baseline."}

                        {ragMode === "basic" &&
                          "Fixed retrieval without adaptive query refinement."}

                        {ragMode === "agentic" &&
                          "Dynamic retrieval with routing and sufficiency checking."}
                      </p>

                    </div>

                    <div className="space-y-2">

                      <Label className="text-xs uppercase tracking-wider text-[#756d74]">
                        AI model
                      </Label>

                      <Select
                        value={llmProvider}
                        onValueChange={(v) =>
                          setValue(
                            "llm_provider",
                            v as FormValues["llm_provider"]
                          )
                        }
                      >
                        <SelectTrigger className="h-11 border-[#ded7cd] bg-[#faf8f4]">
                          <SelectValue />
                        </SelectTrigger>

                        <SelectContent>

                          <SelectItem value="gemini">
                            Gemini — Primary
                          </SelectItem>

                          <SelectItem value="groq">
                            Groq / Llama — Secondary
                          </SelectItem>

                          <SelectItem value="ollama">
                            Ollama — Local
                          </SelectItem>

                        </SelectContent>
                      </Select>

                    </div>

                  </div>
                )}

              </section>

            </main>

            {/* =====================================================
                RIGHT VISUAL PANEL
            ====================================================== */}

            <aside className="hidden h-full lg:block">

              <div className="sticky top-8 flex min-h-[720px] h-full flex-col overflow-hidden rounded-3xl bg-[#2b2030] text-white shadow-xl">

                {/* IMAGE */}

                <div className="relative min-h-[330px] flex-1 overflow-hidden">

                  <img
                    src="https://images.unsplash.com/photo-1519225421980-715cb0215aed?auto=format&fit=crop&w=1200&q=85"
                    alt="Elegant event table setting"
                    className="absolute inset-0 h-full w-full object-cover"
                  />

                  <div className="absolute inset-0 bg-gradient-to-b from-[#2b2030]/10 via-[#2b2030]/25 to-[#2b2030]" />

                  <div className="absolute bottom-7 left-7 right-7">

                    <p className="text-xs uppercase tracking-[0.22em] text-[#d4b47a]">
                      Eventura
                    </p>

                    <h2 className="mt-2 max-w-xs font-serif text-3xl leading-tight">
                      Begins with an idea.
                    </h2>

                  </div>

                </div>

                {/* PANEL CONTENT */}

                <div className="shrink-0 p-7">

                  <p className="max-w-sm text-sm leading-6 text-white/65">
                    Your idea becomes the starting point. Eventura researches,
                    reasons through constraints and refines the details into
                    a coordinated plan.
                  </p>

                  <div className="mt-7 space-y-4">

                    <div className="flex items-center gap-3">
                      <Sparkles className="h-4 w-4 text-[#d4b47a]" />
                      <span className="text-sm text-white/80">
                        Understand your brief
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <Search className="h-4 w-4 text-[#d4b47a]" />
                      <span className="text-sm text-white/80">
                        Research suitable options
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <WalletCards className="h-4 w-4 text-[#d4b47a]" />
                      <span className="text-sm text-white/80">
                        Check budget & feasibility
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <Check className="h-4 w-4 text-[#d4b47a]" />
                      <span className="text-sm text-white/80">
                        Refine the final plan
                      </span>
                    </div>

                  </div>

                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="mt-8 h-12 w-full rounded-full bg-[#d0ad6e] text-[#241b2b] hover:bg-[#dfc084]"
                  >

                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating your event…
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Let Eventura Plan It
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}

                  </Button>

                </div>

              </div>

            </aside>

          </div>

        </form>

      </div>

    </div>
  );
}