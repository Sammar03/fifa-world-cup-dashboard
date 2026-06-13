"use client";

import { type ReactNode, useMemo, useState } from "react";
import { X } from "lucide-react";
import type { Fixture, TeamRef } from "@/types";
import { groupFixturesByDay } from "@/lib/fixtures";
import { useLiveFixtures } from "@/hooks/use-live-fixtures";
import { formatDayHeading } from "@/lib/format";
import { cn } from "@/lib/utils";
import { FixtureCard } from "@/components/fixture-card";
import { TeamFlag } from "@/components/team-flag";
import { EmptyState } from "@/components/empty-state";

type Tab = "upcoming" | "finished";

const byKickoff = (a: Fixture, b: Fixture) =>
  a.kickoff_at.localeCompare(b.kickoff_at);

// Home board. A team search filters to one country's fixtures (live → results →
// upcoming). With no search: live matches pinned on top, then Upcoming / Results
// tabs revealing one matchday at a time via Show more / Show less. All data is
// already client-side; no network on any of these interactions.
export function FixturesBoard({
  initialFixtures,
}: {
  initialFixtures: Fixture[];
}) {
  const fixtures = useLiveFixtures(initialFixtures);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  // Only the 48 real countries are searchable — knockout placeholder "teams"
  // ("Group A Winner") have no group label and are excluded.
  const teams = useMemo(() => {
    const map = new Map<number, TeamRef>();
    for (const f of fixtures) {
      for (const t of [f.home_team, f.away_team]) {
        if (t.group_label && !map.has(t.id)) map.set(t.id, t);
      }
    }
    return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [fixtures]);

  const trimmed = query.trim().toLowerCase();
  const matchingTeams = useMemo(
    () => (trimmed ? teams.filter((t) => t.name.toLowerCase().includes(trimmed)) : []),
    [teams, trimmed],
  );
  // Resolve to a single country: exact name match, else the lone partial match.
  const selectedTeam = useMemo(() => {
    if (!trimmed) return null;
    const exact = teams.find((t) => t.name.toLowerCase() === trimmed);
    return exact ?? (matchingTeams.length === 1 ? matchingTeams[0] : null);
  }, [trimmed, teams, matchingTeams]);

  // Suggestions appear only once the user types — never the full country list.
  const suggestions = trimmed && !selectedTeam ? matchingTeams.slice(0, 8) : [];
  const showInput = open || query.length > 0;

  const searchBar = (
    <div className="flex justify-end">
      {!showInput ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="notch-sm border border-line px-3 py-1.5 text-[0.8125rem] font-medium text-muted transition-colors hover:border-line-strong hover:text-ink"
        >
          Search
        </button>
      ) : (
        <div className="relative w-full max-w-[16rem]">
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Team name…"
            aria-label="Search fixtures by team"
            className="notch-sm w-full border border-line py-2 pl-3 pr-9 text-[0.875rem] text-ink placeholder:text-muted focus:border-brand focus:outline-none"
          />
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setOpen(false);
            }}
            aria-label="Close search"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted transition-colors hover:bg-surface hover:text-ink"
          >
            <X className="size-4" aria-hidden />
          </button>
          {suggestions.length > 0 && (
            <ul className="notch-sm absolute z-20 mt-1 w-full overflow-hidden border border-line bg-card shadow-lg">
              {suggestions.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => setQuery(t.name)}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-[0.875rem] text-ink transition-colors hover:bg-surface"
                  >
                    <TeamFlag src={t.flag_url} name={t.name} width={18} />
                    {t.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );

  if (fixtures.length === 0) {
    return (
      <div className="space-y-6">
        {searchBar}
        <EmptyState
          title="No matches scheduled"
          hint="Check back closer to kickoff for live fixtures."
        />
      </div>
    );
  }

  // --- Team view: one country's fixtures, live → results → upcoming ---------
  if (selectedTeam) {
    const teamFx = fixtures.filter(
      (f) => f.home_team.id === selectedTeam.id || f.away_team.id === selectedTeam.id,
    );
    const groups: { key: string; label: string; fixtures: Fixture[] }[] = [
      { key: "live", label: "Live now", fixtures: teamFx.filter((f) => f.status === "live").sort(byKickoff) },
      { key: "finished", label: "Results", fixtures: teamFx.filter((f) => f.status === "finished").sort(byKickoff) },
      { key: "upcoming", label: "Upcoming", fixtures: teamFx.filter((f) => f.status === "scheduled").sort(byKickoff) },
    ].filter((g) => g.fixtures.length > 0);

    return (
      <div className="space-y-6">
        {searchBar}

        <div className="flex items-center gap-3">
          <TeamFlag src={selectedTeam.flag_url} name={selectedTeam.name} width={28} />
          <h2 className="display text-[1.5rem] text-ink">{selectedTeam.name}</h2>
          <span className="section-tag">{teamFx.length} matches</span>
        </div>

        {groups.length === 0 ? (
          <EmptyState
            title="No fixtures found"
            hint={`No matches are listed for ${selectedTeam.name} yet.`}
          />
        ) : (
          <div className="space-y-8">
            {groups.map((g) => (
              <section key={g.key} aria-labelledby={`team-${g.key}`}>
                <h3 id={`team-${g.key}`} className="mb-4 flex items-center gap-3">
                  <span className="section-tag">
                    {g.key === "live" && (
                      <span className="relative flex size-2" aria-hidden>
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-negative opacity-75" />
                        <span className="relative inline-flex size-2 rounded-full bg-negative" />
                      </span>
                    )}
                    {g.label}
                  </span>
                  <span className="h-px flex-1 bg-line" aria-hidden />
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  {g.fixtures.map((f, i) => (
                    <FixtureCard key={f.id} fixture={f} delayMs={i * 70} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    );
  }

  // No exact/unique team match but a query is present → nothing to show.
  if (trimmed && matchingTeams.length === 0) {
    return (
      <div className="space-y-6">
        {searchBar}
        <EmptyState
          title="No team found"
          hint="Try a country competing at the World Cup, e.g. Brazil or Japan."
        />
      </div>
    );
  }

  // --- Default board: live pinned, then Upcoming / Results tabs --------------
  return (
    <DefaultBoard fixtures={fixtures} searchBar={searchBar} />
  );
}

function DefaultBoard({
  fixtures,
  searchBar,
}: {
  fixtures: Fixture[];
  searchBar: ReactNode;
}) {
  const live = useMemo(() => fixtures.filter((f) => f.status === "live"), [fixtures]);
  const upcomingDays = useMemo(
    () => groupFixturesByDay(fixtures.filter((f) => f.status === "scheduled")),
    [fixtures],
  );
  const finishedDays = useMemo(
    () => groupFixturesByDay(fixtures.filter((f) => f.status === "finished")).reverse(),
    [fixtures],
  );

  const [tab, setTab] = useState<Tab>(
    upcomingDays.length === 0 && finishedDays.length > 0 ? "finished" : "upcoming",
  );
  const [shownUpcoming, setShownUpcoming] = useState(1);
  const [shownFinished, setShownFinished] = useState(1);

  const isUpcoming = tab === "upcoming";
  const days = isUpcoming ? upcomingDays : finishedDays;
  const shown = isUpcoming ? shownUpcoming : shownFinished;
  const setShown = isUpcoming ? setShownUpcoming : setShownFinished;
  const visibleDays = days.slice(0, shown);
  const hasMore = shown < days.length;
  const canShowLess = shown > 1;

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "upcoming", label: "Upcoming", count: upcomingDays.reduce((n, d) => n + d.fixtures.length, 0) },
    { key: "finished", label: "Results", count: finishedDays.reduce((n, d) => n + d.fixtures.length, 0) },
  ];

  return (
    <div className="space-y-6">
      {searchBar}

      {live.length > 0 && (
        <section aria-labelledby="live-heading">
          <h2 id="live-heading" className="mb-4 flex items-center gap-3">
            <span className="section-tag">
              <span className="relative flex size-2" aria-hidden>
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-negative opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-negative" />
              </span>
              Live now · {live.length}
            </span>
            <span className="h-px flex-1 bg-line" aria-hidden />
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {live.map((f, i) => (
              <FixtureCard key={f.id} fixture={f} delayMs={i * 70} />
            ))}
          </div>
        </section>
      )}

      <div role="tablist" aria-label="Fixtures" className="flex flex-wrap gap-1.5">
        {tabs.map((t) => {
          const selected = t.key === tab;
          return (
            <button
              key={t.key}
              role="tab"
              type="button"
              aria-selected={selected}
              onClick={() => setTab(t.key)}
              className={cn(
                "notch-sm border px-3.5 py-1.5 text-[0.875rem] font-medium transition-colors",
                selected
                  ? "border-positive text-positive"
                  : "border-line text-muted hover:border-line-strong hover:text-ink",
              )}
            >
              {t.label}
              <span className={cn("ml-1.5", selected ? "text-paper/70" : "text-muted/70")}>
                {t.count}
              </span>
            </button>
          );
        })}
      </div>

      {days.length === 0 ? (
        <EmptyState
          title={isUpcoming ? "No upcoming matches" : "No results yet"}
          hint={
            isUpcoming
              ? "Every fixture has kicked off — check the Results tab."
              : "Finished matches appear here as the tournament gets underway."
          }
        />
      ) : (
        <div className="space-y-10">
          {visibleDays.map((d) => (
            <section key={d.day} aria-labelledby={`day-${d.day}`}>
              <h2 id={`day-${d.day}`} className="mb-4 flex items-center gap-3">
                <span className="section-tag">{formatDayHeading(d.iso)}</span>
                <span className="h-px flex-1 bg-line" aria-hidden />
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {d.fixtures.map((f, i) => (
                  <FixtureCard key={f.id} fixture={f} delayMs={i * 70} />
                ))}
              </div>
            </section>
          ))}

          {(hasMore || canShowLess) && (
            <div className="flex justify-center gap-2 pt-1">
              {hasMore && (
                <button
                  type="button"
                  onClick={() => setShown((n) => n + 1)}
                  className="notch-sm border border-line-strong px-5 py-2.5 text-[0.875rem] font-medium text-ink transition-colors hover:border-positive hover:text-positive"
                >
                  Show more {isUpcoming ? "matches" : "results"}
                </button>
              )}
              {canShowLess && (
                <button
                  type="button"
                  onClick={() => setShown((n) => Math.max(1, n - 1))}
                  className="notch-sm border border-line-strong px-5 py-2.5 text-[0.875rem] font-medium text-muted transition-colors hover:border-line-strong hover:text-ink"
                >
                  Show less
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
