// Single typed API client. Every frontend data call goes through here — no
// ad-hoc fetch() scattered across components (CLAUDE.md §7.2).
//
// The client reads only from the dashboard's own FastAPI backend. Set
// NEXT_PUBLIC_API_BASE_URL to point at it (defaults to localhost:8000).

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

export async function getFixtures(
  params?: {
    date?: string;
    status?: FixtureStatus;
  },
  opts?: { revalidate?: number },
): Promise<FixturesResponse> {
  const qs = new URLSearchParams();
  if (params?.date) qs.set("date", params.date);
  if (params?.status) qs.set("status", params.status);
  const q = qs.toString();
  // Fixtures change live; always fetch fresh (no ISR) so the list can't drift
  // out of sync with the match detail page's own fresh fetch.
  return getJSON<FixturesResponse>(`/fixtures${q ? `?${q}` : ""}`, {
    revalidate: opts?.revalidate ?? 0,
  });
}

/** A fixture id that does not exist resolves to null so pages can call notFound(). */
export async function getFixture(
  id: number,
  opts?: { revalidate?: number },
): Promise<FixtureDetailResponse | null> {
  try {
    // Same reasoning as getFixtures: always fresh, no ISR, so this page never
    // lags or leads the home board's view of the same fixture.
    return await getJSON<FixtureDetailResponse>(`/fixtures/${id}`, {
      revalidate: opts?.revalidate ?? 0,
    });
  } catch (err) {
    if (err instanceof APIError && err.status === 404) return null;
    throw err;
  }
}

export async function getGroups(): Promise<string[]> {
  // The backend exposes groups implicitly; standings drive the tab list.
  return ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"];
}

export async function getStandings(group?: string): Promise<StandingsResponse> {
  const qs = group ? `?group=${encodeURIComponent(group)}` : "";
  return getJSON<StandingsResponse>(`/standings${qs}`, { revalidate: 60 });
}

export async function getScorers(
  sort: "goals" | "assists" | "clean_sheets" = "goals",
  limit = 50,
): Promise<ScorersResponse> {
  return getJSON<ScorersResponse>(`/scorers?sort=${sort}&limit=${limit}`, {
    revalidate: 60,
  });
}

export async function getTeam(id: number): Promise<TeamResponse | null> {
  try {
    return await getJSON<TeamResponse>(`/teams/${id}`, { revalidate: 60 });
  } catch (err) {
    if (err instanceof APIError && err.status === 404) return null;
    throw err;
  }
}

export async function postQuery(question: string): Promise<QueryResponse> {
  return getJSON<QueryResponse>(`/query`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export async function getHealth(): Promise<HealthResponse> {
  return getJSON<HealthResponse>(`/health`);
}
