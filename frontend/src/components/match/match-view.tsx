"use client";

import Link from "next/link";
import type { FixtureDetailResponse } from "@/types";
import type { StatRow } from "@/components/match/stat-comparison";
import { useLiveFixture } from "@/hooks/use-live-fixture";
import { Badge } from "@/components/ui/badge";
import { LiveBadge } from "@/components/live-badge";
import { LocalTime } from "@/components/local-time";
import { TeamFlag } from "@/components/team-flag";
import { AIInsightBlock } from "@/components/ai-insight";
import { GoalTimeline } from "@/components/match/goal-timeline";
import { StatComparison } from "@/components/match/stat-comparison";

// Renders the match detail and polls for live updates so the page stays in sync
// with the home board (the score, minute, goals and stats all change live).
export function MatchView({ initial }: { initial: FixtureDetailResponse }) {
  const data = useLiveFixture(initial.fixture.id, initial);
  const { fixture, stats, goals, insight } = data;
  const { home_team, away_team, status, home_score, away_score, minute, venue } =
    fixture;
  const scheduled = status === "scheduled";

  const homeStats = stats.find((s) => s.team_id === home_team.id);
  const awayStats = stats.find((s) => s.team_id === away_team.id);
  const statRows: StatRow[] = [
    { label: "Possession", home: homeStats?.possession ?? null, away: awayStats?.possession ?? null, percent: true },
    { label: "Shots", home: homeStats?.shots ?? null, away: awayStats?.shots ?? null },
    { label: "On target", home: homeStats?.shots_on_target ?? null, away: awayStats?.shots_on_target ?? null },
    { label: "Corners", home: homeStats?.corners ?? null, away: awayStats?.corners ?? null },
    { label: "Fouls", home: homeStats?.fouls ?? null, away: awayStats?.fouls ?? null },
    { label: "Yellow cards", home: homeStats?.yellow_cards ?? null, away: awayStats?.yellow_cards ?? null },
    { label: "Red cards", home: homeStats?.red_cards ?? null, away: awayStats?.red_cards ?? null },
  ];
  const hasStats = statRows.some((r) => r.home !== null || r.away !== null);

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <Link
          href="/"
          className="text-[0.875rem] font-medium text-muted transition-colors hover:text-positive"
        >
          ← All fixtures
        </Link>
      </div>

      <header className="rise-in notch relative overflow-hidden bg-card p-6 md:p-8">
        <div className="tri-stripe absolute inset-x-0 top-0 h-[3px]" aria-hidden />
        <div className="mb-4 flex items-center justify-between">
          {status === "live" ? (
            <LiveBadge minute={minute} />
          ) : status === "finished" ? (
            <Badge variant="neutral">Full time</Badge>
          ) : (
            <Badge variant="neutral">Upcoming</Badge>
          )}
          {fixture.group_label && (
            <span className="text-[0.75rem] text-muted">
              Group {fixture.group_label}
            </span>
          )}
        </div>

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <div className="flex min-w-0 flex-col items-center gap-2 text-center">
            <TeamFlag src={home_team.flag_url} name={home_team.name} width={48} />
            <Link
              href={`/team/${home_team.id}`}
              className="display text-[1.125rem] transition-colors hover:text-positive md:text-[1.375rem]"
            >
              {home_team.name}
            </Link>
          </div>

          <div className="text-center">
            {scheduled ? (
              <div className="text-[0.875rem] font-medium text-muted">
                <LocalTime iso={fixture.kickoff_at} withDate />
              </div>
            ) : (
              <div className="display text-[3.5rem] text-ink md:text-[4.5rem]">
                {home_score ?? 0}
                <span className="px-2 text-muted">–</span>
                {away_score ?? 0}
              </div>
            )}
          </div>

          <div className="flex min-w-0 flex-col items-center gap-2 text-center">
            <TeamFlag src={away_team.flag_url} name={away_team.name} width={48} />
            <Link
              href={`/team/${away_team.id}`}
              className="display text-[1.125rem] transition-colors hover:text-positive md:text-[1.375rem]"
            >
              {away_team.name}
            </Link>
          </div>
        </div>

        {venue && (
          <p className="mt-4 text-center text-[0.75rem] text-muted">{venue}</p>
        )}
      </header>

      <AIInsightBlock insight={insight} />

      {goals.length > 0 && (
        <section
          className="rise-in notch border-l-2 border-line-strong bg-card p-6"
          style={{ animationDelay: "120ms" }}
        >
          <GoalTimeline goals={goals} homeTeam={home_team} awayTeam={away_team} />
        </section>
      )}

      {hasStats && (
        <section
          className="rise-in notch border-l-2 border-line-strong bg-card p-6"
          style={{ animationDelay: "200ms" }}
        >
          <h2 className="display mb-5 text-[1.375rem]">Match stats</h2>
          <StatComparison rows={statRows} />
        </section>
      )}

      {scheduled && goals.length === 0 && !hasStats && (
        <p className="text-center text-[0.875rem] text-muted">
          Stats and the goal timeline appear once the match kicks off.
        </p>
      )}
    </div>
  );
}
