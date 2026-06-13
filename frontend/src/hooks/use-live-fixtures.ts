"use client";

import { useEffect, useState } from "react";
import type { Fixture } from "@/types";
import { getFixtures } from "@/lib/api";

/** Client poll interval for live matches (CLAUDE.md §7.3). */
export const LIVE_POLL_INTERVAL_MS = 30_000;

// Polls the backend only while at least one fixture is live. The interval is
// always cleared in the effect cleanup (CLAUDE.md §7.3).
export function useLiveFixtures(initial: Fixture[]): Fixture[] {
  const [fixtures, setFixtures] = useState<Fixture[]>(initial);

  // Keep in sync if the server provides fresh initial data (e.g. navigation).
  useEffect(() => {
    setFixtures(initial);
  }, [initial]);

  const hasLive = fixtures.some((f) => f.status === "live");

  useEffect(() => {
    if (!hasLive) return;

    const id = setInterval(async () => {
      try {
        const res = await getFixtures();
        setFixtures(res.fixtures);
      } catch {
        // Network blip: keep the last good data, try again next tick.
      }
    }, LIVE_POLL_INTERVAL_MS);

    return () => clearInterval(id);
  }, [hasLive]);

  return fixtures;
}
