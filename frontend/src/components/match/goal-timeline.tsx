import type { Goal, TeamRef } from "@/types";
import { TeamFlag } from "@/components/team-flag";

// Two clean tracks: minute | scorer (dashboard.md §6.6).
const TYPE_LABEL: Record<Goal["type"], string | null> = {
  regular: null,
  penalty: "pen",
  own_goal: "OG",
};

export function GoalTimeline({
  goals,
  homeTeam,
  awayTeam,
}: {
  goals: Goal[];
  homeTeam: TeamRef;
  awayTeam: TeamRef;
}) {
  if (goals.length === 0) return null;

  const teamFor = (id: number) => (id === homeTeam.id ? homeTeam : awayTeam);

  return (
    <div>
      <h2 className="display mb-3 text-[1.375rem]">Goals</h2>
      <ul className="divide-y divide-line">
        {goals.map((g) => {
          const t = teamFor(g.team_id);
          const tag = TYPE_LABEL[g.type];
          return (
            <li
              key={g.id}
              className="grid grid-cols-[3rem_1fr] items-center gap-3 py-2.5 transition-colors hover:bg-surface/50"
            >
              <span className="tabular inline-grid h-6 place-items-center justify-self-end rounded-full bg-positive-wash px-2 text-[0.8125rem] font-semibold text-positive">
                {g.minute}&apos;
              </span>
              <span className="flex items-center gap-2">
                <TeamFlag src={t.flag_url} name={t.name} width={18} />
                <span className="font-medium text-ink">{g.player_name}</span>
                {tag && (
                  <span className="rounded bg-surface px-1.5 py-0.5 text-[0.6875rem] font-medium uppercase tracking-[0.04em] text-muted">
                    {tag}
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
