import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ScorerStat } from "@/types";
import { PlayerStatsView } from "@/components/player-stats-view";

const players: ScorerStat[] = [
  {
    rank: 1,
    player_name: "Goal King",
    team_name: "Brazil",
    team_code: "BRA",
    position: "FW",
    goals: 5,
    assists: 1,
    clean_sheets: null,
    matches_played: 3,
  },
  {
    rank: 2,
    player_name: "Assist Ace",
    team_name: "France",
    team_code: "FRA",
    position: "MF",
    goals: 2,
    assists: 6,
    clean_sheets: null,
    matches_played: 3,
  },
  {
    rank: 3,
    player_name: "Safe Hands",
    team_name: "Spain",
    team_code: "ESP",
    position: "GK",
    goals: 0,
    assists: 0,
    clean_sheets: 4,
    matches_played: 3,
  },
];

describe("PlayerStatsView tabs", () => {
  it("defaults to the Goals board with the top scorer first", () => {
    render(<PlayerStatsView players={players} />);

    expect(screen.getByRole("tab", { name: "Goals" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    // Row 0 is the header; the goalkeeper (no goals) is filtered off this board.
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("Goal King");
    expect(screen.queryByText("Safe Hands")).not.toBeInTheDocument();
  });

  it("switches to the Assists board on tab click, replacing the table", async () => {
    const user = userEvent.setup();
    render(<PlayerStatsView players={players} />);

    await user.click(screen.getByRole("tab", { name: "Assists" }));

    expect(screen.getAllByRole("row")[1]).toHaveTextContent("Assist Ace");
  });

  it("shows only goalkeepers, ranked by clean sheets, on the Clean sheets board", async () => {
    const user = userEvent.setup();
    render(<PlayerStatsView players={players} />);

    await user.click(screen.getByRole("tab", { name: "Clean sheets" }));

    expect(screen.getAllByRole("row")[1]).toHaveTextContent("Safe Hands");
    // Outfield players are excluded from the clean-sheets board.
    expect(screen.queryByText("Goal King")).not.toBeInTheDocument();
  });
});
