import type { Fixture } from "@/types";
import { dayKey } from "@/lib/format";

export interface FixtureDay {
  /** UTC day key (YYYY-MM-DD). */
  day: string;
  /** A representative ISO timestamp from the day, for heading formatting. */
  iso: string;
  fixtures: Fixture[];
}

const byKickoff = (a: Fixture, b: Fixture) =>
  a.kickoff_at.localeCompare(b.kickoff_at);

/** Group fixtures into day buckets, ascending by day then kickoff. */
export function groupFixturesByDay(fixtures: Fixture[]): FixtureDay[] {
  const map = new Map<string, Fixture[]>();
  for (const f of fixtures) {
    const key = dayKey(f.kickoff_at);
    const bucket = map.get(key);
    if (bucket) bucket.push(f);
    else map.set(key, [f]);
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, fx]) => ({
      day,
      iso: fx[0].kickoff_at,
      fixtures: [...fx].sort(byKickoff),
    }));
}
