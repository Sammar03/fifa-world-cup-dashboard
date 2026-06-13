// Single typed API client. Every frontend data call goes through here — no
// ad-hoc fetch() scattered across components (CLAUDE.md §7.2).
//
// During the dashboard phase there is no backend, so the client serves the mock
// dataset (NEXT_PUBLIC_USE_MOCKS, default "true"). Set NEXT_PUBLIC_USE_MOCKS=false
// and NEXT_PUBLIC_API_BASE_URL to point at the FastAPI backend — no component
// changes required.

import type {
  FixtureStatus,
  FixturesResponse,
  FixtureDetailResponse,
  HealthResponse,
  QueryResponse,
  ScorersResponse,
  StandingsResponse,
  TeamResponse,
} from "@/types";
import * as mock from "@/lib/mock-data";

const USE_MOCKS = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") !== "false";
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Thrown when the backend returns a non-2xx response. */
export class APIError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    // Read endpoints serve fast-changing data; never cache at the fetch layer.
    cache: "no-store",
  });
  if (!res.ok) {
    throw new APIError(res.status, `Request to ${path} failed (${res.status})`);
  }
  return (await res.json()) as T;
}

/** A fixture id that does not exist resolves to null so pages can call notFound(). */
export async function getFixtures(params?: {
  date?: string;
  status?: FixtureStatus;
}): Promise<FixturesResponse> {
  if (USE_MOCKS) return mock.getFixtures(params);
  const qs = new URLSearchParams();
  if (params?.date) qs.set("date", params.date);
  if (params?.status) qs.set("status", params.status);
  const q = qs.toString();
  return getJSON<FixturesResponse>(`/fixtures${q ? `?${q}` : ""}`);
}

export async function getFixture(
  id: number,
): Promise<FixtureDetailResponse | null> {
  if (USE_MOCKS) return mock.getFixture(id);
  try {
    return await getJSON<FixtureDetailResponse>(`/fixtures/${id}`);
  } catch (err) {
    if (err instanceof APIError && err.status === 404) return null;
    throw err;
  }
}

export async function getGroups(): Promise<string[]> {
  if (USE_MOCKS) return mock.getGroups();
  // The backend exposes groups implicitly; standings drive the tab list.
  return ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"];
}

export async function getStandings(group?: string): Promise<StandingsResponse> {
  if (USE_MOCKS) return mock.getStandings(group);
  const qs = group ? `?group=${encodeURIComponent(group)}` : "";
  return getJSON<StandingsResponse>(`/standings${qs}`);
}

export async function getScorers(
  sort: "goals" | "assists" = "goals",
  limit = 50,
): Promise<ScorersResponse> {
  if (USE_MOCKS) return mock.getScorers(sort, limit);
  return getJSON<ScorersResponse>(`/scorers?sort=${sort}&limit=${limit}`);
}

export async function getTeam(id: number): Promise<TeamResponse | null> {
  if (USE_MOCKS) return mock.getTeam(id);
  try {
    return await getJSON<TeamResponse>(`/teams/${id}`);
  } catch (err) {
    if (err instanceof APIError && err.status === 404) return null;
    throw err;
  }
}

export async function postQuery(question: string): Promise<QueryResponse> {
  if (USE_MOCKS) {
    // NL query ships as a "coming soon" stub this phase (CLAUDE.md §4.7 / BACKLOG-001).
    return {
      answer:
        "I can't answer that yet — I only know about goals, standings, scorers, and cards.",
      evidence: null,
      supported: false,
    };
  }
  return getJSON<QueryResponse>(`/query`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export async function getHealth(): Promise<HealthResponse> {
  if (USE_MOCKS) return { status: "ok", db: "ok", version: "mock" };
  return getJSON<HealthResponse>(`/health`);
}
