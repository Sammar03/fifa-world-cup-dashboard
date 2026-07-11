import type { FixtureStatus } from "@/types";

/** Client poll interval for live matches (CLAUDE.md §7.3). */
export const LIVE_POLL_INTERVAL_MS = 30_000;

// Begin polling a little before kickoff and keep going through a match's max
// duration, so the page catches the scheduled→live→finished transitions on its
// own without a manual refresh.
const KICKOFF_LEAD_MS = 15 * 60_000; // 15 min before kickoff
const MATCH_MAX_DURATION_MS = 3.5 * 60 * 60_000; // ~3.5 h after kickoff

// Is this match in its live window — currently live, or scheduled with
// kickoff near/just passed? Used to decide whether a poll tick should hit
// the network.
export function inLiveWindow(status: FixtureStatus, kickoffAt: string, now: number): boolean {
  if (status === "live") return true;
  if (status !== "scheduled") return false;
  const kickoff = new Date(kickoffAt).getTime();
  return kickoff - KICKOFF_LEAD_MS <= now && now <= kickoff + MATCH_MAX_DURATION_MS;
}
