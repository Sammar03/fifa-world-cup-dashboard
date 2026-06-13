"use client";

import { useMemo, useState } from "react";
import type { ScorerStat } from "@/types";
import { cn } from "@/lib/utils";
import { sortScorers, type ScorerSortKey } from "@/lib/scorers";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";

// Player Stats has three separate leaderboards — Goals, Assists, Clean sheets —
// switched by tabs (like the Standings group tabs). Only one table is mounted at
// a time; switching is instant and client-side, no network call. Goals/assists
// list the players who have any; clean sheets is a goalkeeper-only board.
const TABS: { key: ScorerSortKey; label: string }[] = [
  { key: "goals", label: "Goals" },
  { key: "assists", label: "Assists" },
  { key: "clean_sheets", label: "Clean sheets" },
];

const EMPTY: Record<ScorerSortKey, { title: string; hint: string }> = {
  goals: { title: "No goals yet", hint: "The board fills up as the tournament gets underway." },
  assists: { title: "No assists yet", hint: "The board fills up as the tournament gets underway." },
  clean_sheets: { title: "No clean sheets yet", hint: "Goalkeepers earn a clean sheet by conceding no goals in a match." },
};

export function PlayerStatsView({ players }: { players: ScorerStat[] }) {
  const [active, setActive] = useState<ScorerSortKey>("goals");

  const rows = useMemo(() => {
    const list =
      active === "goals"
        ? players.filter((p) => p.goals > 0)
        : active === "assists"
          ? players.filter((p) => p.assists > 0)
          : players.filter((p) => p.position === "GK");
    return sortScorers(list, active);
  }, [players, active]);

  const metricValue = (s: ScorerStat): number | null =>
    active === "goals" ? s.goals : active === "assists" ? s.assists : s.clean_sheets;

  const metricLabel = TABS.find((t) => t.key === active)!.label;

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="Player stat" className="flex flex-wrap gap-1.5">
        {TABS.map((t) => {
          const selected = t.key === active;
          return (
            <button
              key={t.key}
              role="tab"
              type="button"
              aria-selected={selected}
              onClick={() => setActive(t.key)}
              className={cn(
                "notch-sm border px-3.5 py-1.5 text-[0.875rem] font-medium transition-colors",
                selected
                  ? "border-positive text-positive"
                  : "border-line text-muted hover:border-line-strong hover:text-ink",
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {rows.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10 text-center">#</TableHead>
              <TableHead>Player</TableHead>
              <TableHead>Team</TableHead>
              <TableHead className="text-right">MP</TableHead>
              <TableHead className="text-right">{metricLabel}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((s, i) => (
              <TableRow
                key={`${s.player_name}-${s.team_code}`}
                className="odd:bg-card/70"
              >
                <TableCell className="text-center">
                  <span
                    className={cn(
                      "inline-grid size-6 place-items-center rounded-full text-[0.8125rem] font-semibold",
                      i === 0
                        ? "bg-positive text-paper"
                        : i < 3
                          ? "bg-positive-wash text-positive"
                          : "text-muted",
                    )}
                  >
                    {i + 1}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <span className="font-medium text-ink">{s.player_name}</span>
                    <span className="rounded bg-surface px-1 py-0.5 text-[0.625rem] font-semibold uppercase tracking-[0.04em] text-muted">
                      {s.position}
                    </span>
                  </span>
                </TableCell>
                <TableCell>
                  <span className="rounded bg-surface px-1.5 py-0.5 text-[0.75rem] font-semibold uppercase tracking-[0.04em] text-muted">
                    {s.team_code}
                  </span>
                </TableCell>
                <TableCell className="text-right">{s.matches_played}</TableCell>
                <TableCell className="display text-right text-[1.0625rem] text-positive">
                  {metricValue(s) ?? "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <EmptyState title={EMPTY[active].title} hint={EMPTY[active].hint} />
      )}
    </div>
  );
}
