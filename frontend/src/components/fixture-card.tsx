import Link from "next/link";
import type { Fixture } from "@/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { LiveBadge } from "@/components/live-badge";
import { LocalTime } from "@/components/local-time";
import { TeamFlag } from "@/components/team-flag";

// Three independent columns: home | score | away. Status sits in its own row
// above — never merged into the score. The card is transparent with only an
// outline, so the page artwork shows through (matching the open table rows);
// notched corner, condensed scoreboard numerals. Winners read in green.
export function FixtureCard({
  fixture,
  delayMs = 0,
}: {
  fixture: Fixture;
  delayMs?: number;
}) {
  const {
    id,
    status,
    home_team,
    away_team,
    home_score,
    away_score,
    minute,
    kickoff_at,
    group_label,
  } = fixture;

  const live = status === "live";
  const finished = status === "finished";
  const scheduled = status === "scheduled";
  const homeWin = finished && (home_score ?? 0) > (away_score ?? 0);
  const awayWin = finished && (away_score ?? 0) > (home_score ?? 0);

  return (
    <Link
      href={`/match/${id}`}
      className="card-interactive rise-in notch group block border border-line-strong p-4"
      style={{ animationDelay: `${delayMs}ms` }}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        {live ? (
          <LiveBadge minute={minute} />
        ) : finished ? (
          <Badge variant="neutral">Full time</Badge>
        ) : (
          <span className="text-[0.75rem] font-medium text-muted">
            <LocalTime iso={kickoff_at} />
          </span>
        )}
        {group_label && (
          <span className="rounded-full bg-surface px-2 py-0.5 text-[0.6875rem] font-medium uppercase tracking-[0.04em] text-muted">
            Group {group_label}
          </span>
        )}
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div className="flex min-w-0 items-center justify-end gap-2 text-right">
          <span
            className={cn(
              "truncate text-[0.9375rem]",
              homeWin ? "font-bold text-positive" : "text-ink",
            )}
          >
            {home_team.name}
          </span>
          <TeamFlag src={home_team.flag_url} name={home_team.name} />
        </div>

        <div className="min-w-[64px] text-center">
          {scheduled ? (
            <span className="display text-[0.875rem] text-muted">vs</span>
          ) : (
            <span className="display text-[1.625rem] text-ink">
              {home_score ?? 0}
              <span className="px-1 text-muted">–</span>
              {away_score ?? 0}
            </span>
          )}
        </div>

        <div className="flex min-w-0 items-center gap-2">
          <TeamFlag src={away_team.flag_url} name={away_team.name} />
          <span
            className={cn(
              "truncate text-[0.9375rem]",
              awayWin ? "font-bold text-positive" : "text-ink",
            )}
          >
            {away_team.name}
          </span>
        </div>
      </div>
    </Link>
  );
}
