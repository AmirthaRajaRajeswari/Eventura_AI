import { NavLink, useNavigate } from "react-router-dom";

import { useQuery } from "@tanstack/react-query";

import {
  ArrowUpRight,
  CalendarDays,
  ChevronRight,
  FlaskConical,
  Plus,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { sessionsApi } from "@/api/sessions";

function eventLabel(value?: string) {
  if (!value) return "New Event";

  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getEventInitial(value?: string) {
  if (!value) return "E";
  return eventLabel(value).charAt(0).toUpperCase();
}

export default function Sidebar() {
  const navigate = useNavigate();

  const { data: sessionsData } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => sessionsApi.list(),
    refetchInterval: 5000,
  });

  const sessions = sessionsData?.sessions?.slice(0, 8) ?? [];

  return (
    <aside className="flex h-screen w-[240px] shrink-0 flex-col border-r border-[#ded6cc] bg-[#f3efe8] text-[#2b2030]">

      {/* BRAND */}

      <div className="px-6 pb-6 pt-7">

        <div className="flex items-center gap-3">

          <div className="relative flex h-10 w-10 items-center justify-center rounded-full bg-[#2b2030]">
            <Sparkles className="h-4 w-4 text-[#d0ad6e]" />

            <span className="absolute inset-0 rounded-full border border-[#d0ad6e]/20" />
          </div>

          <div>
            <p className="font-serif text-xl leading-none tracking-[-0.02em] text-[#2b2030]">
              Eventura
            </p>

            <p className="mt-1 text-[9px] font-medium uppercase tracking-[0.17em] text-[#938981]">
              AI Event Planning
            </p>
          </div>

        </div>

      </div>

      {/* NEW EVENT */}

      <div className="px-4 pb-7">

        <Button
          onClick={() => navigate("/events/new")}
          className="h-11 w-full justify-between rounded-xl bg-[#2b2030] px-4 text-xs font-medium text-white shadow-none hover:bg-[#3a2a40]"
        >
          <span className="flex items-center gap-2.5">
            <Plus className="h-4 w-4 text-[#d0ad6e]" />
            New Event
          </span>

          <ArrowUpRight className="h-3.5 w-3.5 text-white/40" />
        </Button>

      </div>

      {/* EVENTS */}

      <nav className="min-h-0 flex-1 overflow-y-auto px-4">

        <div className="mb-3 px-2">
          <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-[#9b9189]">
            Your events
          </p>
        </div>

        {sessions.length === 0 ? (

          <div className="px-4 py-8 text-center">

            <CalendarDays className="mx-auto h-5 w-5 text-[#b3a99f]" />

            <p className="mt-2 text-[10px] leading-4 text-[#91877f]">
              Your planned events
              <br />
              will appear here.
            </p>

          </div>

        ) : (

          <div className="space-y-1">

            {sessions.map((session) => (

              <NavLink
                key={session.id}
                to={`/events/${session.id}`}
                className={({ isActive }) =>
                  cn(
                    "group relative flex items-center gap-3 rounded-xl px-3 py-3 transition-all duration-200",
                    isActive
                      ? "bg-white shadow-[0_5px_18px_rgba(64,48,40,0.06)]"
                      : "hover:bg-white/60"
                  )
                }
              >

                {({ isActive }) => (
                  <>

                    {/* ACTIVE INDICATOR */}

                    {isActive && (
                      <span className="absolute bottom-2 left-0 top-2 w-0.5 rounded-r-full bg-[#a77b3d]" />
                    )}

                    {/* EVENT INITIAL */}

                    <div
                      className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold",
                        isActive
                          ? "bg-[#2b2030] text-[#d0ad6e]"
                          : "bg-[#e8e1d8] text-[#81766e]"
                      )}
                    >
                      {getEventInitial(session.event_type)}
                    </div>

                    {/* EVENT NAME */}

                    <div className="min-w-0 flex-1">

                      <span
                        className={cn(
                          "block truncate text-xs",
                          isActive
                            ? "font-medium text-[#332a30]"
                            : "text-[#675e58]"
                        )}
                      >
                        {eventLabel(session.event_type)}
                      </span>

                    </div>

                    {/* ARROW */}

                    <ChevronRight
                      className={cn(
                        "h-3.5 w-3.5 shrink-0 transition-all",
                        isActive
                          ? "translate-x-0 text-[#a77b3d]"
                          : "-translate-x-1 text-transparent group-hover:translate-x-0 group-hover:text-[#b0a69d]"
                      )}
                    />

                  </>
                )}

              </NavLink>

            ))}

          </div>

        )}

      </nav>

      {/* EVALUATION */}

      <div className="px-4 pb-5 pt-4">

        <div className="mb-2 h-px bg-[#ded6cc]" />

        <NavLink
          to="/eval"
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-xl px-3 py-3 transition-colors",
              isActive
                ? "bg-white text-[#332a30] shadow-[0_5px_18px_rgba(64,48,40,0.05)]"
                : "text-[#776e68] hover:bg-white/60"
            )
          }
        >

          {({ isActive }) => (
            <>

              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full",
                  isActive
                    ? "bg-[#eee7dd]"
                    : "bg-[#e8e1d8]"
                )}
              >
                <FlaskConical
                  className={cn(
                    "h-3.5 w-3.5",
                    isActive
                      ? "text-[#8b6b45]"
                      : "text-[#817870]"
                  )}
                />
              </div>

              <div className="flex-1">

                <p className="text-xs font-medium">
                  Evaluation Studio
                </p>

                <p className="mt-0.5 text-[9px] text-[#a09891]">
                  Research & performance
                </p>

              </div>

              <ArrowUpRight
                className={cn(
                  "h-3 w-3 transition-opacity",
                  isActive
                    ? "opacity-100 text-[#a77b3d]"
                    : "opacity-0 group-hover:opacity-60"
                )}
              />

            </>
          )}

        </NavLink>

      </div>

    </aside>
  );
}