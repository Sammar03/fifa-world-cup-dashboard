"use client";

import { useEffect, useRef, useState } from "react";
import type { Fixture } from "@/types";
import { getFixtures } from "@/lib/api";
import { LIVE_POLL_INTERVAL_MS, inLiveWindow as fixtureInLiveWindow } from "@/lib/live-window";

export { LIVE_POLL_INTERVAL_MS };

// Is any match in its live window? Used to decide whether a poll tick should
// hit the network.
function inLiveWindow(fixtures: Fixture[], now: number): boolean {
  return fixtures.some((f) => fixtureInLiveWindow(f.status, f.kickoff_at, now));
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
