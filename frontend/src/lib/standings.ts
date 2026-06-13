import type { Standing } from "@/types";

// Official FIFA 2026 group tiebreaker (CLAUDE.md §4.2, ADR-003):
//   1. points DESC
//   2. goal difference DESC
//   3. goals for DESC
//   4. team name ASC (alphabetical)
export function sortByFifaTiebreaker(rows: Standing[]): Standing[] {
  return [...rows].sort(
    (a, b) =>
      b.points - a.points ||
      b.goal_diff - a.goal_diff ||
      b.goals_for - a.goals_for ||
      a.team.name.localeCompare(b.team.name),
  );
}
