import type { FormResult, TeamAggregate, TeamRef } from "@/types";
import { formatGoalDiff, formatStat } from "@/lib/format";
import { TeamFlag } from "@/components/team-flag";
import { FormChips } from "@/components/form-chips";

// Header band (brand) + uniform stat-grid where each stat is one equal-width
// cell {label, value}. Missing values render "—", never blank (dashboard.md §6.5).
interface StatCell {
  label: string;
  value: string;
}

export function TeamStats({
  team,
  stats,
  form,
}: {
  team: TeamRef;
  stats: TeamAggregate;
  form: FormResult[];
}) {
  const cells: StatCell[] = [
    { label: "Played", value: `${stats.matches_played}` },
    { label: "Goals for", value: `${stats.goals_for}` },
    { label: "Goals against", value: `${stats.goals_against}` },
    { label: "Goal difference", value: formatGoalDiff(stats.goal_diff) },
    { label: "Clean sheets", value: `${stats.clean_sheets}` },
    { label: "Possession avg", value: formatStat(stats.possession_avg, "%") },
    { label: "Shots", value: formatStat(stats.shots) },
    { label: "Shots on target", value: formatStat(stats.shots_on_target) },
    { label: "Corners", value: formatStat(stats.corners) },
    { label: "Yellow cards", value: formatStat(stats.yellow_cards) },
    { label: "Red cards", value: formatStat(stats.red_cards) },
  ];

  return (
    <div className="space-y-6">
      <div className="rise-in notch relative overflow-hidden bg-gradient-to-br from-brand to-brand-wash p-4 text-paper md:p-6">
        <div className="tri-stripe absolute inset-x-0 bottom-0 h-[3px]" aria-hidden />
        <div className="flex items-center gap-4">
          <TeamFlag src={team.flag_url} name={team.name} width={48} />
          <div>
            <h1 className="display text-[2.25rem] md:text-[2.75rem]">
              {team.name}
            </h1>
            <p className="text-[0.875rem] text-paper/80">Group {team.group_label}</p>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="text-[0.75rem] uppercase tracking-[0.04em] text-paper/80">
            Recent form
          </span>
          <FormChips form={form} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {cells.map((c, i) => (
          <div
            key={c.label}
            className="card-interactive rise-in notch-sm border-l-2 border-line-strong bg-card p-4"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <p className="text-[0.75rem] uppercase tracking-[0.04em] text-muted">
              {c.label}
            </p>
            <p className="display mt-1 text-[1.75rem] text-ink">{c.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
