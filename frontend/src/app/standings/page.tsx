import type { Metadata } from "next";
import type { Standing } from "@/types";
import { getGroups, getStandings } from "@/lib/api";
import { StandingsView } from "@/components/standings-view";

export const metadata: Metadata = {
  title: "Standings — World Cup 2026",
};

// Group standings. All groups are fetched server-side and handed to a client
// view so switching groups is instant with no network call (CLAUDE.md §4.2).
export default async function StandingsPage() {
  const groups = await getGroups();
  const results = await Promise.all(groups.map((g) => getStandings(g)));
  const standingsByGroup: Record<string, Standing[]> = Object.fromEntries(
    results.map((r) => [r.group, r.standings]),
  );

  return (
    <div className="space-y-6">
      <header className="rise-in py-2">
        <h1 className="display text-[3rem] md:text-[4rem]">Standings</h1>
        <span className="title-accent" aria-hidden />
      </header>

      <StandingsView groups={groups} standingsByGroup={standingsByGroup} />
    </div>
  );
}
