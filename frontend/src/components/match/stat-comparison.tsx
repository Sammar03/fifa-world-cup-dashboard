import { cn } from "@/lib/utils";

export interface StatRow {
  label: string;
  home: number | null;
  away: number | null;
  percent?: boolean;
}

function fmt(value: number | null, percent?: boolean): string {
  if (value === null) return "—";
  return percent ? `${value}%` : `${value}`;
}

// Three fixed columns: home value | label + bar | away value. The numbers stay
// in their own columns; the bars grow out from the center on load — home in
// green, away in red, with the leading side's number lit to match.
export function StatComparison({ rows }: { rows: StatRow[] }) {
  const usable = rows.filter((r) => r.home !== null || r.away !== null);
  if (usable.length === 0) return null;

  return (
    <div className="space-y-4">
      {usable.map((r, i) => {
        const home = r.home ?? 0;
        const away = r.away ?? 0;
        const total = home + away || 1;
        const homePct = r.percent ? home : Math.round((home / total) * 100);
        const delay = `${i * 60}ms`;
        return (
          <div
            key={r.label}
            className="grid grid-cols-[3rem_1fr_3rem] items-center gap-3"
          >
            <span
              className={cn(
                "tabular text-left text-[0.9375rem] font-semibold",
                home > away ? "text-positive" : "text-ink",
              )}
            >
              {fmt(r.home, r.percent)}
            </span>
            <div>
              <div className="mb-1.5 text-center text-[0.75rem] uppercase tracking-[0.04em] text-muted">
                {r.label}
              </div>
              <div className="flex h-2 gap-0.5 overflow-hidden rounded-full bg-surface">
                <div
                  className="bar-home rounded-l-full bg-positive"
                  style={{ width: `${homePct}%`, animationDelay: delay }}
                />
                <div
                  className="bar-away rounded-r-full bg-negative"
                  style={{ width: `${100 - homePct}%`, animationDelay: delay }}
                />
              </div>
            </div>
            <span
              className={cn(
                "tabular text-right text-[0.9375rem] font-semibold",
                away > home ? "text-negative" : "text-ink",
              )}
            >
              {fmt(r.away, r.percent)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
