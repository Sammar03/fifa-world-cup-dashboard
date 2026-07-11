"use client";

import { useEffect, useRef, useState } from "react";
import type { Fixture } from "@/types";
import { getFixtures } from "@/lib/api";

/** Client poll interval for live matches (CLAUDE.md §7.3). */
export const LIVE_POLL_INTERVAL_MS = 30_000;

// Begin polling a little before kickoff and keep going through a match's max
// duration, so the page catches the scheduled→live→finished transitions on its
// own without a manual refresh.
const KICKOFF_LEAD_MS = 15 * 60_000; // 15 min before kickoff
const MATCH_MAX_DURATION_MS = 3.5 * 60 * 60_000; // ~3.5 h after kickoff

// Is any match in its live window — currently live, or scheduled with kickoff
// near/just passed? Used to decide whether a poll tick should hit the network.
function inLiveWindow(fixtures: Fixture[], now: number): boolean {
  return fixtures.some((f) => {
    if (f.status === "live") return true;
    if (f.status !== "scheduled") return false;
    const kickoff = new Date(f.kickoff_at).getTime();
    return kickoff - KICKOFF_LEAD_MS <= now && now <= kickoff + MATCH_MAX_DURATION_MS;
  });
}

// Polls the backend while matches can still change, refreshing live scores and
// catching kickoffs without the user refreshing. The interval is always cleared
// in the effect cleanup (CLAUDE.md §7.3).
export function useLiveFixtures(initial: Fixture[]): Fixture[] {
  const [fixtures, setFixtures] = useState<Fixture[]>(initial);

  // Latest fixtures for the interval closure (the effect intentionally does not
  // re-subscribe on every data change — it re-evaluates the window each tick).
  const latest = useRef(fixtures);
  latest.current = fixtures;

  // Keep in sync if the server provides fresh initial data (e.g. navigation).
  useEffect(() => {
    setFixtures(initial);
  }, [initial]);

  // Nothing to poll for once every match is finished.
  const hasUnfinished = fixtures.some((f) => f.status !== "finished");

  useEffect(() => {
    if (!hasUnfinished) return;

    let cancelled = false;
    const poll = async () => {
      // Cheap no-op outside match windows; the interval stays alive so a kickoff
      // that happens while the page is open is caught without a manual refresh.
      if (!inLiveWindow(latest.current, Date.now())) return;
      try {
        // revalidate: 0 → always fetch fresh while a match is live.
        const res = await getFixtures(undefined, { revalidate: 0 });
        if (!cancelled) setFixtures(res.fixtures);
      } catch {
        // Network blip: keep the last good data, try again next tick.
      }
    };

    // Poll immediately on mount instead of waiting for the first interval tick,
    // so navigating here never shows a stale snapshot for up to 30s.
    poll();
    const id = setInterval(poll, LIVE_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [hasUnfinished]);

  return fixtures;
}
