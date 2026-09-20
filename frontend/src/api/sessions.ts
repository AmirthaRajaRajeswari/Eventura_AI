/**
 * Typed API client for session management endpoints.
 */

import { api } from "./client";

export interface SessionOut {
  id: string;
  event_type: string | null;
  status: string;
  rag_mode: string;
  llm_provider: string;
  created_at: string;
  updated_at: string;
  requirements?: Record<string, unknown>;
  feasibility?: Record<string, unknown>;
  vendor_selections: VendorSelection[];
  budget_summary?: BudgetSummary;
  negotiation_logs: NegotiationLog[];
  critic_feedback: CriticFeedback[];
  bookings: BookingRecord[];
  run_of_show?: RunOfShowItem[];
  evidence_count: number;
  retrieval_rounds: number;
  critic_iterations: number;
  awaiting_human: boolean;
  hitl_gate: string | null;
  errors: string[];
  synthetic_disclaimer: string;
}

export interface VendorSelection {
  vendor_id: string;
  name: string;
  category: string;
  city: string;
  base_price: number;
  price_per_guest: number | null;
  price_floor: number;
  quoted_price: number;
  final_price: number | null;
  evidence_ids: string[];
  negotiation_savings: number;
  critic_warnings: string[];
  status: string;
}

export interface BudgetSummary {
  total_budget: number;
  spent: number;
  remaining: number;
  pct_used: number;
  over_budget: boolean;
  negotiation_savings: number;
  over_budget_categories: string[];
}

export interface NegotiationLog {
  vendor_id: string;
  category: string;
  initial_price: number;
  final_price: number | null;
  savings: number;
  rounds: NegotiationRound[];
  status: string;
}

export interface NegotiationRound {
  round_number: number;
  our_offer: number;
  vendor_response: string;
  counter_price: number | null;
  final_price: number | null;
  message: string;
  timestamp: string;
}

export interface CriticFeedback {
  passed: boolean;
  issues: CriticIssue[];
  iteration: number;
  resolved: boolean;
}

export interface CriticIssue {
  type: string;
  severity: "high" | "medium" | "low";
  category: string;
  detail: string;
}

export interface BookingRecord {
  vendor_id: string;
  category: string;
  status: string;
  quoted_price: number;
  final_price: number;
  hold_reference: string | null;
  confirmation_reference: string | null;
}

export interface RunOfShowItem {
  activity: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  owner: string;
  description: string;
  day: number;
}

export interface ActivityEvent {
  id: string;
  session_id: string;
  agent: string;
  action: string;
  status: "success" | "error" | "running" | "waiting";
  detail: string | null;
  payload: Record<string, unknown> | null;
  timestamp: string;
}

export interface ApprovalPayload {
  hitl_gate: string;
  session_id: string;
  payload: Record<string, unknown>;
  status: string;
}

// API calls
export const sessionsApi = {
  create: (data: { prompt: string; rag_mode: string; llm_provider: string }) =>
    api.post<SessionOut>("/api/v1/sessions", data),

  get: (id: string) => api.get<SessionOut>(`/api/v1/sessions/${id}`),

  list: () => api.get<{ sessions: SessionOut[]; total: number }>("/api/v1/sessions"),

  sendMessage: (id: string, message: string) =>
    api.post<SessionOut>(`/api/v1/sessions/${id}/message`, { message }),

  getApproval: (id: string) =>
    api.get<ApprovalPayload>(`/api/v1/sessions/${id}/approval`),

  approve: (
    id: string,
    data: {
      action: "approve" | "modify" | "reject_vendor";
      message?: string;
      rejected_vendor_ids?: string[];
      modifications?: Record<string, unknown>;
    }
  ) => api.post<{ session_id: string; action: string; status: string }>(
    `/api/v1/sessions/${id}/approve`,
    data
  ),

  disrupt: (
    id: string,
    data: {
      disruption_type: "vendor_cancelled" | "budget_reduced";
      vendor_id?: string;
      reduction_pct?: number;
      reason?: string;
    }
  ) => api.post<{
    session_id: string;
    disruption_type: string;
    affected_categories: string[];
    before_budget: number | null;
    after_budget: number | null;
    message: string;
  }>(`/api/v1/sessions/${id}/disrupt`, data),
};
