import { describe, it, expect } from "vitest";
import type { Standing } from "@/types";
import { sortByFifaTiebreaker } from "@/lib/standings";

function standing(
  name: string,
  points: number,
  goalDiff: number,
  goalsFor: number,
): Standing {
  return {
    team: {
      id: name.length,
      name,
      code: name.slice(0, 3).toUpperCase(),
      group_label: "A",
      flag_url: null,
    },
    group_label: "A",
    played: 3,
    won: 0,
    drawn: 0,
    lost: 0,
    goals_for: goalsFor,
    goals_against: goalsFor - goalDiff,
    goal_diff: goalDiff,
    points,
    form: [],
  };
}

describe("FIFA 2026 tiebreaker ordering", () => {
  it("orders by points, then goal difference, then goals for", () => {
    const rows = [
      standing("Brazil", 6, 3, 5),
      standing("Argentina", 6, 3, 7),
      standing("Croatia", 6, 5, 6),
      standing("Denmark", 4, 0, 3),
    ];

    const ordered = sortByFifaTiebreaker(rows).map((r) => r.team.name);

    // Croatia leads on GD; Brazil/Argentina tie on points+GD so GF breaks it
    // (Argentina 7 > Brazil 5); Denmark trails on points.
    expect(ordered).toEqual(["Croatia", "Argentina", "Brazil", "Denmark"]);
  });

  it("breaks an otherwise-identical tie alphabetically by team name", () => {
    const rows = [standing("Zambia", 3, 1, 2), standing("Angola", 3, 1, 2)];
    expect(sortByFifaTiebreaker(rows).map((r) => r.team.name)).toEqual([
      "Angola",
      "Zambia",
    ]);
  });
});
