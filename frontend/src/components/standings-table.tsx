import Link from "next/link";
import type { Standing } from "@/types";
import { cn } from "@/lib/utils";
import { formatGoalDiff } from "@/lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TeamFlag } from "@/components/team-flag";
import { FormChips } from "@/components/form-chips";

// Strict column tracks (dashboard.md §6.3): POS · TEAM · P · W · D · L · GF · GA
// · GD · Pts · Form. Numeric columns right-aligned with tabular figures. The top
// two rows are the qualifying places — marked with a 2px brand cutoff line.
const QUALIFYING_PLACES = 2;

export function StandingsTable({ standings }: { standings: Standing[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-10 text-center">Pos</TableHead>
          <TableHead>Team</TableHead>
          <TableHead className="text-right">P</TableHead>
          <TableHead className="hidden text-right sm:table-cell">W</TableHead>
          <TableHead className="hidden text-right sm:table-cell">D</TableHead>
          <TableHead className="hidden text-right sm:table-cell">L</TableHead>
          <TableHead className="hidden text-right sm:table-cell">GF</TableHead>
          <TableHead className="hidden text-right sm:table-cell">GA</TableHead>
          <TableHead className="text-right">GD</TableHead>
          <TableHead className="text-right">Pts</TableHead>
          <TableHead className="hidden pl-4 sm:table-cell">Form</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {standings.map((row, i) => {
          const pos = i + 1;
          const qualifying = pos <= QUALIFYING_PLACES;
          const cutoff = pos === QUALIFYING_PLACES;
          return (
            <TableRow
              key={row.team.id}
              className={cn(
                "odd:bg-card/70",
                cutoff && "border-b-2 border-b-positive",
              )}
            >
              <TableCell className="text-center">
                <span
                  className={cn(
                    "inline-grid size-6 place-items-center rounded-full text-[0.8125rem] font-semibold",
                    qualifying ? "bg-positive-wash text-positive" : "text-muted",
                  )}
                >
                  {pos}
                </span>
              </TableCell>
              <TableCell>
                <Link
                  href={`/team/${row.team.id}`}
                  className="flex min-w-0 items-center gap-2 font-medium text-ink transition-colors hover:text-positive"
                >
                  <TeamFlag src={row.team.flag_url} name={row.team.name} width={20} />
                  <span className="block max-w-[45vw] truncate sm:max-w-none">
                    {row.team.name}
                  </span>
                </Link>
              </TableCell>
              <TableCell className="text-right">{row.played}</TableCell>
              <TableCell className="hidden text-right sm:table-cell">{row.won}</TableCell>
              <TableCell className="hidden text-right sm:table-cell">{row.drawn}</TableCell>
              <TableCell className="hidden text-right sm:table-cell">{row.lost}</TableCell>
              <TableCell className="hidden text-right sm:table-cell">{row.goals_for}</TableCell>
              <TableCell className="hidden text-right sm:table-cell">{row.goals_against}</TableCell>
              <TableCell
                className={cn(
                  "text-right",
                  row.goal_diff > 0 && "text-positive",
                  row.goal_diff < 0 && "text-negative",
                )}
              >
                {formatGoalDiff(row.goal_diff)}
              </TableCell>
              <TableCell className="display text-right text-[1.0625rem] text-ink">
                {row.points}
              </TableCell>
              <TableCell className="hidden pl-4 sm:table-cell">
                <FormChips form={row.form} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
