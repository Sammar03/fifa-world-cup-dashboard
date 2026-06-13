import type { Metadata } from "next";
import { getScorers } from "@/lib/api";
import { PlayerStatsView } from "@/components/player-stats-view";
import { EmptyState } from "@/components/empty-state";

export const metadata: Metadata = {
  title: "Player Stats — World Cup 2026",
};

// Player Stats. Three separate leaderboards — Goals, Assists, Clean sheets —
// each opened by its own tab; the full roster is fetched server-side and the
// active board is rendered client-side, so switching is instant (CLAUDE.md §4.3).
export default async function ScorersPage() {
  const { scorers } = await getScorers("goals", 50);

  return (
    <div className="space-y-6">
      <header className="rise-in py-2">
        <h1 className="display text-[3rem] md:text-[4rem]">Player Stats</h1>
        <span className="title-accent" aria-hidden />
      </header>

      {scorers.length > 0 ? (
        <PlayerStatsView players={scorers} />
      ) : (
        <EmptyState
          title="No player stats yet"
          hint="The boards fill up as the tournament gets underway."
        />
      )}
    </div>
  );
}
