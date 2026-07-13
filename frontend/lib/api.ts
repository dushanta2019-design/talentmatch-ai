"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Role = "admin" | "recruiter" | "hiring_manager" | "candidate";

export interface Session {
  access_token: string;
  role: Role;
  user_id: string;
  full_name: string;
}

export interface Resume {
  id: string;
  file_name: string | null;
  status: string;
  parsed: Record<string, any> | null;
  error: string | null;
  created_at: string;
}

export interface Job {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  description_raw: string;
  status: string;
  parsed: Record<string, any> | null;
  is_open: boolean;
  created_at: string;
}

export interface Match {
  id: string;
  resume_id: string;
  job_id: string;
  status: string;
  overall_score: number | null;
  confidence: "low" | "medium" | "high" | null;
  semantic_score: number | null;
  skills_score: number | null;
  experience_score: number | null;
  education_score: number | null;
  matched_skills: string[] | null;
  missing_skills: string[] | null;
  gaps: Record<string, string[]> | null;
  explanation: {
    strengths?: string[];
    concerns?: string[];
    experience_gaps?: string[];
    education_certification_gaps?: string[];
    role_fit_summary?: string;
    recommendation_note?: string;
  } | null;
  review_status: string;
  override_score: number | null;
  job_title?: string | null;
  resume_file_name?: string | null;
  created_at: string;
}

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("session");
  return raw ? (JSON.parse(raw) as Session) : null;
}

export function setSession(s: Session | null) {
  if (s) localStorage.setItem("session", JSON.stringify(s));
  else localStorage.removeItem("session");
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const session = getSession();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (session) headers["Authorization"] = `Bearer ${session.access_token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    setSession(null);
    window.location.href = "/login";
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
