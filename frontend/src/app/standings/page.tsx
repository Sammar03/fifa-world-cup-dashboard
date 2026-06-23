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
  // allSettled so one group's fetch failing (or a transient backend blip at
  // build/render time) degrades that group to empty instead of failing the
  // whole prerender (CLAUDE.md §12); ISR refills on the next revalidate.
  const results = await Promise.allSettled(groups.map((g) => getStandings(g)));
  const standingsByGroup: Record<string, Standing[]> = {};
  results.forEach((result, i) => {
    standingsByGroup[groups[i]] =
      result.status === "fulfilled" ? result.value.standings : [];
  });

  return (
    <div className="space-y-6">
      <header className="rise-in py-2">
        <h1 className="display text-[2.5rem] sm:text-[3rem] md:text-[4rem]">Standings</h1>
        <span className="title-accent" aria-hidden />
      </header>

      <StandingsView groups={groups} standingsByGroup={standingsByGroup} />
    </div>
  );
}
