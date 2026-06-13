import type { ScorerStat } from "@/types";

export type ScorerSortKey = "goals" | "assists" | "clean_sheets";

// The fields the sort needs — keeps the comparator usable before `rank` is
// assigned (e.g. while deriving the leaderboard).
type ScorerSortable = Pick<
  ScorerStat,
  "goals" | "assists" | "clean_sheets" | "matches_played" | "player_name"
>;

// Default sort: goals DESC, ties broken by fewer matches played, then assists
// (CLAUDE.md §4.3). The assists and clean-sheets views mirror it with their own
// metric primary. Clean sheets are null for outfield players, so they sort last.
export function sortScorers<T extends ScorerSortable>(
  scorers: T[],
  key: ScorerSortKey,
): T[] {
  const copy = [...scorers];
  if (key === "assists") {
    copy.sort(
      (a, b) =>
        b.assists - a.assists ||
        a.matches_played - b.matches_played ||
        b.goals - a.goals ||
        a.player_name.localeCompare(b.player_name),
    );
  } else if (key === "clean_sheets") {
    copy.sort(
      (a, b) =>
        (b.clean_sheets ?? -1) - (a.clean_sheets ?? -1) ||
        a.matches_played - b.matches_played ||
        b.goals - a.goals ||
        a.player_name.localeCompare(b.player_name),
    );
  } else {
    copy.sort(
      (a, b) =>
        b.goals - a.goals ||
        a.matches_played - b.matches_played ||
        b.assists - a.assists ||
        a.player_name.localeCompare(b.player_name),
    );
  }
  return copy;
}
