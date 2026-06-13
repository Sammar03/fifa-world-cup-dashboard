import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Fixture } from "@/types";
import { FixtureCard } from "@/components/fixture-card";

function fixture(overrides: Partial<Fixture>): Fixture {
  return {
    id: 1,
    home_team: { id: 1, name: "Brazil", code: "BRA", group_label: "A", flag_url: null },
    away_team: { id: 2, name: "Mexico", code: "MEX", group_label: "A", flag_url: null },
    kickoff_at: "2026-06-12T16:00:00Z",
    venue: null,
    status: "scheduled",
    home_score: null,
    away_score: null,
    group_label: "A",
    round: "Group Stage",
    minute: null,
    verified: false,
    ...overrides,
  };
}

describe("FixtureCard", () => {
  it("renders a LIVE badge with the minute when the match is live", () => {
    render(
      <FixtureCard
        fixture={fixture({ status: "live", home_score: 1, away_score: 0, minute: 67 })}
      />,
    );
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByText("67'")).toBeInTheDocument();
  });

  it("shows Full time and no LIVE badge when the match is finished", () => {
    render(
      <FixtureCard
        fixture={fixture({ status: "finished", home_score: 2, away_score: 1 })}
      />,
    );
    expect(screen.queryByText("Live")).not.toBeInTheDocument();
    expect(screen.getByText("Full time")).toBeInTheDocument();
  });
});
