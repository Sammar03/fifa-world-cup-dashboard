import type { Metadata } from "next";
import type { ScorerStat } from "@/types";
import { getScorers } from "@/lib/api";
import { PlayerStatsView } from "@/components/player-stats-view";
import { EmptyState } from "@/components/empty-state";

export const metadata: Metadata = {
  title: "Player Stats — World Cup 2026",
};

// Player Stats. Three separate leaderboards — Goals, Assists, Clean sheets —
// each opened by its own tab; the active board is rendered client-side so
// switching is instant (CLAUDE.md §4.3). Each board has its own ordering, and
// assisters / goalkeepers don't appear in the goals top-N (0 goals), so we fetch
// all three boards and merge them — a single goals-sorted fetch would leave the
// Assists and Clean-sheets tabs nearly empty once enough matches are played.
export default async function ScorersPage() {
  const [goals, assists, cleanSheets] = await Promise.all([
    getScorers("goals", 50),
    getScorers("assists", 50),
    getScorers("clean_sheets", 50),
  ]);
  const byPlayer = new Map<string, ScorerStat>();
  for (const s of [...goals.scorers, ...assists.scorers, ...cleanSheets.scorers]) {
    // Same DB row across sorts, so last-write-wins is fine; PlayerStatsView
    // re-ranks each board client-side and ignores the server `rank`.
    byPlayer.set(`${s.player_name}|${s.team_code}`, s);
  }
  const scorers = [...byPlayer.values()];

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
