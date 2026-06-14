"use client";

import { useState } from "react";
import type { Standing } from "@/types";
import { cn } from "@/lib/utils";
import { StandingsTable } from "@/components/standings-table";
import { EmptyState } from "@/components/empty-state";

// Group selector + table. Switching is instant (all groups' data is provided by
// the server) — no network call (dashboard.md §6.3, CLAUDE.md §4.2).
export function StandingsView({
  groups,
  standingsByGroup,
}: {
  groups: string[];
  standingsByGroup: Record<string, Standing[]>;
}) {
  const [active, setActive] = useState(groups[0] ?? "");
  const rows = standingsByGroup[active] ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-muted">
          Group
        </span>
        {/* Compact single-letter chips: a tidy row on desktop, wrapping to a
            couple of rows on mobile instead of a tall cluster of "Group X"
            buttons. The aria-label keeps each one fully described. */}
        <div role="tablist" aria-label="Group" className="flex flex-wrap gap-1.5">
          {groups.map((g) => {
            const selected = g === active;
            return (
              <button
                key={g}
                role="tab"
                type="button"
                aria-selected={selected}
                aria-label={`Group ${g}`}
                onClick={() => setActive(g)}
                className={cn(
                  "notch-sm flex size-8 items-center justify-center border text-[0.875rem] font-semibold transition-colors",
                  selected
                    ? "border-positive text-positive"
                    : "border-line text-muted hover:border-line-strong hover:text-ink",
                )}
              >
                {g}
              </button>
            );
          })}
        </div>
      </div>

      {rows.length > 0 ? (
        <StandingsTable standings={rows} />
      ) : (
        <EmptyState
          title={`No results yet for Group ${active}`}
          hint="Standings appear once matches in this group are played."
        />
      )}
    </div>
  );
}
