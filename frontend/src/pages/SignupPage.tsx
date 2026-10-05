import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Eye,
  EyeOff,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/hooks/use-toast";

export default function SignupPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  function handleSignup(e: React.FormEvent) {
    e.preventDefault();

    if (!name || !email || !password) {
      toast({
        variant: "destructive",
        title: "Complete your details",
        description: "Please fill in all the fields.",
      });
      return;
    }

    if (password.length < 6) {
      toast({
        variant: "destructive",
        title: "Password is too short",
        description: "Use at least 6 characters.",
      });
      return;
    }

    localStorage.setItem(
      "eventura_user",
      JSON.stringify({
        name,
        email,
      })
    );

    toast({
      title: "Welcome to Eventura",
      description: "Your planning workspace is ready.",
    });

    navigate("/events/new");
  }

  return (
    <div className="min-h-screen bg-[#f8f5ef] lg:grid lg:grid-cols-2">

      <div className="relative hidden min-h-screen overflow-hidden bg-[#2b2030] lg:block">
        <img
          src="https://images.unsplash.com/photo-1591604466107-ec97de577aff?auto=format&fit=crop&w=1400&q=85"
          alt="Elegant celebration"
          className="absolute inset-0 h-full w-full object-cover opacity-55"
        />

        <div className="absolute inset-0 bg-[#211823]/60" />

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
            <p className="mb-5 text-[10px] uppercase tracking-[0.25em] text-[#d0ad6e]">
              Begin with an idea
            </p>

            <h1 className="font-serif text-6xl leading-[0.94] tracking-[-0.035em]">
              Your next
              <br />
              unforgettable
              <br />
              <span className="italic text-[#d0ad6e]">
                story starts here.
              </span>
            </h1>

            <p className="mt-7 max-w-md text-sm leading-7 text-white/70">
              Create your Eventura workspace and let your AI
              planning team take care of the complexity.
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

      <div className="flex min-h-screen items-center justify-center px-6 py-12">
        <div className="w-full max-w-[490px]">

          <div className="mb-10">
            <p className="mb-5 text-[10px] font-semibold uppercase tracking-[0.25em] text-[#a77b3d]">
              Create your workspace
            </p>

            <h2 className="font-serif text-[48px] leading-[1.02] tracking-[-0.03em] text-[#241b2b]">
              Let's make
              <br />
              something
              <br />
              <span className="italic">unforgettable.</span>
            </h2>

            <p className="mt-5 text-sm leading-6 text-[#776d74]">
              Create an account and start planning with Eventura.
            </p>
          </div>

          <form onSubmit={handleSignup} className="space-y-6">

            <div>
              <label
                htmlFor="name"
                className="mb-2 block text-[10px] font-medium uppercase tracking-[0.16em] text-[#544a52]"
              >
                Your name
              </label>

              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Amir"
                className="h-11 rounded-none border-0 border-b border-[#d9d1c8] bg-transparent px-0 shadow-none focus-visible:border-[#a77b3d] focus-visible:ring-0"
              />
            </div>

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
                className="h-11 rounded-none border-0 border-b border-[#d9d1c8] bg-transparent px-0 shadow-none focus-visible:border-[#a77b3d] focus-visible:ring-0"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-[10px] font-medium uppercase tracking-[0.16em] text-[#544a52]"
              >
                Password
              </label>

              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  className="h-11 rounded-none border-0 border-b border-[#d9d1c8] bg-transparent px-0 pr-10 shadow-none focus-visible:border-[#a77b3d] focus-visible:ring-0"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-0 top-1/2 -translate-y-1/2 text-[#9a9096]"
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
              Create my Eventura account
              <ArrowRight className="ml-2 h-4 w-4 text-[#d0ad6e]" />
            </Button>
          </form>

          <p className="mt-8 text-center text-xs text-[#91878d]">
            Already have an account?{" "}
            <Link
              to="/login"
              className="font-medium text-[#a77b3d] hover:underline"
            >
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}