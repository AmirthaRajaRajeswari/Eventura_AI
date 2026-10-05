import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, CheckCircle2, Eye, EyeOff, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";

export default function LoginPage() {
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);
  const [showReset, setShowReset] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetEmail, setResetEmail] = useState("");

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();

    if (!email || !password) {
      toast({
        variant: "destructive",
        title: "Complete your details",
        description: "Please enter your email and password.",
      });
      return;
    }

    toast({
      title: "Welcome back",
      description: "Opening your Eventura workspace.",
    });

    navigate("/events/new");
  }

  function handleDemoLogin() {
    toast({
      title: "Demo workspace opened",
      description: "Welcome to Eventura.",
    });

    navigate("/events/new");
  }

  function handleResetPassword(e: React.FormEvent) {
    e.preventDefault();

    if (!resetEmail) {
      toast({
        variant: "destructive",
        title: "Email required",
        description: "Enter the email associated with your account.",
      });
      return;
    }

    setShowReset(false);

    toast({
      title: "Reset link sent",
      description: `If an account exists for ${resetEmail}, a reset link has been sent.`,
    });

    setResetEmail("");
  }

  return (
    <div className="min-h-screen bg-[#f8f5ef] lg:grid lg:grid-cols-2">

      {/* Left visual */}

      <div className="relative hidden min-h-screen overflow-hidden bg-[#2b2030] lg:block">
        <img
          src="https://images.unsplash.com/photo-1519225421980-715cb0215aed?auto=format&fit=crop&w=1400&q=85"
          alt="Elegant event setting"
          className="absolute inset-0 h-full w-full object-cover opacity-60"
        />

        <div className="absolute inset-0 bg-[#211823]/55" />

        <div className="relative flex min-h-screen flex-col justify-between p-12 text-white">

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[#d0ad6e]/60">
              <Sparkles className="h-5 w-5 text-[#d0ad6e]" />
            </div>

            <div>
              <p className="font-serif text-2xl leading-none">
                Eventura AI
              </p>

              <p className="mt-1 text-[9px] uppercase tracking-[0.2em] text-white/60">
                Agentic Event Planning
              </p>
            </div>
          </div>

          <div className="max-w-xl">
            <p className="mb-5 text-[10px] font-medium uppercase tracking-[0.25em] text-[#d0ad6e]">
              Your vision · Our intelligence
            </p>

            <h1 className="font-serif text-6xl leading-[0.94] tracking-[-0.035em]">
              Every event
              <br />
              deserves a
              <br />
              <span className="italic text-[#d0ad6e]">
                story.
              </span>
            </h1>

            <p className="mt-7 max-w-md text-sm leading-7 text-white/70">
              Let Eventura's AI agents transform your ideas into
              thoughtfully planned, beautifully coordinated
              experiences.
            </p>
          </div>

          <div className="flex gap-8 text-[10px] text-white/55">
            <span>Weddings</span>
            <span>Birthdays</span>
            <span>College Fests</span>
            <span>More</span>
          </div>
        </div>
      </div>

      {/* Right */}

      <div className="flex min-h-screen items-center justify-center px-6 py-12">
        <div className="w-full max-w-[490px]">

          <div className="mb-10">
            <p className="mb-5 text-[10px] font-semibold uppercase tracking-[0.25em] text-[#a77b3d]">
              Welcome back
            </p>

            <h2 className="font-serif text-[48px] leading-[1.02] tracking-[-0.03em] text-[#241b2b]">
              Let's continue
              <br />
              <span className="italic">
                your story.
              </span>
            </h2>

            <p className="mt-5 text-sm leading-6 text-[#776d74]">
              Sign in to continue planning your next
              unforgettable experience.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-7">

            <div>
              <label
                htmlFor="email"
                className="mb-2 block text-[10px] font-medium uppercase tracking-[0.16em] text-[#544a52]"
              >
                Email
              </label>

              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="h-11 rounded-none border-0 border-b border-[#d9d1c8] bg-transparent px-0 text-sm shadow-none focus-visible:border-[#a77b3d] focus-visible:ring-0"
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="text-[10px] font-medium uppercase tracking-[0.16em] text-[#544a52]"
                >
                  Password
                </label>

                <button
                  type="button"
                  onClick={() => setShowReset(true)}
                  className="text-[10px] text-[#a77b3d] transition-colors hover:text-[#76552d]"
                >
                  Forgot password?
                </button>
              </div>

              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="h-11 rounded-none border-0 border-b border-[#d9d1c8] bg-transparent px-0 pr-10 text-sm shadow-none focus-visible:border-[#a77b3d] focus-visible:ring-0"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-0 top-1/2 -translate-y-1/2 text-[#9a9096] hover:text-[#4d424b]"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="h-11 w-full rounded-full bg-[#211823] text-xs font-medium text-white shadow-none hover:bg-[#342638]"
            >
              Enter Eventura
              <ArrowRight className="ml-2 h-4 w-4 text-[#d0ad6e]" />
            </Button>
          </form>

          <div className="my-8 flex items-center gap-4">
            <div className="h-px flex-1 bg-[#ddd5cc]" />
            <span className="text-[9px] uppercase tracking-[0.2em] text-[#aaa0a5]">
              Or
            </span>
            <div className="h-px flex-1 bg-[#ddd5cc]" />
          </div>

          <button
            type="button"
            onClick={handleDemoLogin}
            className="h-11 w-full rounded-full border border-[#d7cec4] bg-transparent text-xs font-medium text-[#302732] transition-colors hover:bg-white"
          >
            Continue as Demo User
          </button>

          <p className="mt-8 text-center text-xs text-[#91878d]">
            New to Eventura?{" "}
            <Link
              to="/signup"
              className="font-medium text-[#a77b3d] hover:underline"
            >
              Sign up
            </Link>
          </p>
        </div>
      </div>

      {/* Forgot password */}

      {showReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#211823]/45 px-5 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#f8f5ef] p-8 shadow-2xl">

            <div className="mb-7">
              <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-full bg-[#eee7dc]">
                <Sparkles className="h-4 w-4 text-[#a77b3d]" />
              </div>

              <h3 className="font-serif text-3xl text-[#241b2b]">
                Reset your password
              </h3>

              <p className="mt-2 text-sm leading-6 text-[#81767d]">
                Enter your email and we'll send instructions
                to reset your password.
              </p>
            </div>

            <form onSubmit={handleResetPassword}>
              <label
                htmlFor="reset-email"
                className="mb-2 block text-[10px] font-medium uppercase tracking-[0.15em] text-[#544a52]"
              >
                Email
              </label>

              <Input
                id="reset-email"
                type="email"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                placeholder="you@example.com"
                autoFocus
                className="h-11 rounded-none border-0 border-b border-[#d9d1c8] bg-transparent px-0 shadow-none focus-visible:border-[#a77b3d] focus-visible:ring-0"
              />

              <div className="mt-7 flex gap-3">
                <Button
                  type="button"
                  onClick={() => setShowReset(false)}
                  variant="ghost"
                  className="flex-1 rounded-full text-xs"
                >
                  Cancel
                </Button>

                <Button
                  type="submit"
                  className="flex-1 rounded-full bg-[#211823] text-xs text-white hover:bg-[#342638]"
                >
                  Send reset link
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}