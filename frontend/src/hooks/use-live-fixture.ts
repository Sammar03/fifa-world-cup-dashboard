"use client";

import { useEffect, useRef, useState } from "react";
import type { FixtureDetailResponse } from "@/types";
import { getFixture } from "@/lib/api";

// Single-match sibling of useLiveFixtures: keeps the match detail page in sync
// with the home board (CLAUDE.md §7.3). The server render is always fresh
// (no ISR), but we still poll on the client while the match can change so the
// page re-renders score/minute/goals/stats without a manual refresh.
export const LIVE_POLL_INTERVAL_MS = 30_000;

const KICKOFF_LEAD_MS = 15 * 60_000; // 15 min before kickoff
const MATCH_MAX_DURATION_MS = 3.5 * 60 * 60_000; // ~3.5 h after kickoff

function inLiveWindow(data: FixtureDetailResponse, now: number): boolean {
  const f = data.fixture;
  if (f.status === "live") return true;
  if (f.status !== "scheduled") return false;
  const kickoff = new Date(f.kickoff_at).getTime();
  return kickoff - KICKOFF_LEAD_MS <= now && now <= kickoff + MATCH_MAX_DURATION_MS;
}

export function useLiveFixture(
  id: number,
  initial: FixtureDetailResponse,
): FixtureDetailResponse {
  const [data, setData] = useState<FixtureDetailResponse>(initial);

  const latest = useRef(data);
  latest.current = data;

  // Adopt fresh server data on navigation between matches.
  useEffect(() => {
    setData(initial);
  }, [initial]);

  // Once finished there is nothing left to poll for.
  const finished = data.fixture.status === "finished";

  useEffect(() => {
    if (finished) return;

    let cancelled = false;
    const poll = async () => {
      if (!inLiveWindow(latest.current, Date.now())) return;
      try {
        // revalidate: 0 → always fetch fresh while a match is live.
        const res = await getFixture(id, { revalidate: 0 });
        if (res && !cancelled) setData(res);
      } catch {
        // Network blip: keep the last good data, try again next tick.
      }
    };

    // Poll immediately on mount instead of waiting for the first interval tick,
    // so navigating here never shows a stale snapshot for up to 30s.
    poll();
    const interval = setInterval(poll, LIVE_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [id, finished]);

  return data;
}
