// Date/number formatting helpers.
//
// Kickoff times are shown in the user's LOCAL timezone via Intl.DateTimeFormat
// (CLAUDE.md §4.1). Because the server's timezone can differ from the visitor's,
// local times are rendered in a small client component (<LocalTime>) to avoid
// hydration mismatches. Day grouping/headings use the UTC calendar date so the
// grouping is stable across server and client.

/** UTC calendar-day key (YYYY-MM-DD) used to group fixtures by day. */
export function dayKey(iso: string): string {
  return iso.slice(0, 10);
}

/** Heading for a day group, e.g. "Thursday, 11 June" (UTC date — stable). */
export function formatDayHeading(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(iso));
}

/** Kickoff time in the user's local timezone, e.g. "18:00". */
export function formatLocalTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** Kickoff date+time in the user's local timezone, e.g. "Thu 11 Jun, 18:00". */
export function formatLocalDateTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** Signed goal difference, e.g. "+5", "0", "-2". */
export function formatGoalDiff(gd: number): string {
  return gd > 0 ? `+${gd}` : `${gd}`;
}

/** A possession/percentage value, or the graceful em-dash fallback. */
export function formatStat(value: number | null | undefined, suffix = ""): string {
  if (value === null || value === undefined) return "—";
  return `${value}${suffix}`;
}
