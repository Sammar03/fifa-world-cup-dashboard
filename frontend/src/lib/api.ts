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

type GetOpts = { revalidate?: number; method?: string; body?: BodyInit };

async function getJSON<T>(path: string, opts: GetOpts = {}): Promise<T> {
  const { revalidate = 0, method, body } = opts;
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    body,
    headers: { "Content-Type": "application/json" },
    // revalidate > 0 → cache the result in Next's Data Cache and refresh it
    // every N seconds (ISR). Server-rendered pages then serve from cache instead
    // of hitting the backend on every request — the main load-time win, and safe
    // because ingestion updates on a similar cadence. revalidate 0 → always
    // fresh: client-side live polling, /health, and POST /query. The `next`
    // option is ignored for browser fetches, so live polling stays real-time.
    ...(revalidate > 0 ? { next: { revalidate } } : { cache: "no-store" }),
  });
  if (!res.ok) {
    throw new APIError(res.status, `Request to ${path} failed (${res.status})`);
  }
  return (await res.json()) as T;
}

/** A fixture id that does not exist resolves to null so pages can call notFound(). */
export async function getFixtures(
  params?: {
    date?: string;
    status?: FixtureStatus;
  },
  opts?: { revalidate?: number },
): Promise<FixturesResponse> {
  if (USE_MOCKS) return mock.getFixtures(params);
  const qs = new URLSearchParams();
  if (params?.date) qs.set("date", params.date);
  if (params?.status) qs.set("status", params.status);
  const q = qs.toString();
  // Default 30s; the live-polling hook passes 0 to force fresh client fetches.
  return getJSON<FixturesResponse>(`/fixtures${q ? `?${q}` : ""}`, {
    revalidate: opts?.revalidate ?? 30,
  });
}

export async function getFixture(
  id: number,
): Promise<FixtureDetailResponse | null> {
  if (USE_MOCKS) return mock.getFixture(id);
  try {
    return await getJSON<FixtureDetailResponse>(`/fixtures/${id}`, {
      revalidate: 30,
    });
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
  return getJSON<StandingsResponse>(`/standings${qs}`, { revalidate: 60 });
}

export async function getScorers(
  sort: "goals" | "assists" = "goals",
  limit = 50,
): Promise<ScorersResponse> {
  if (USE_MOCKS) return mock.getScorers(sort, limit);
  return getJSON<ScorersResponse>(`/scorers?sort=${sort}&limit=${limit}`, {
    revalidate: 60,
  });
}

export async function getTeam(id: number): Promise<TeamResponse | null> {
  if (USE_MOCKS) return mock.getTeam(id);
  try {
    return await getJSON<TeamResponse>(`/teams/${id}`, { revalidate: 60 });
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
