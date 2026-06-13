"use client";

import { useEffect, useState } from "react";
import { formatLocalTime, formatLocalDateTime } from "@/lib/format";

// Renders a kickoff time in the visitor's local timezone. The server can't know
// the visitor's tz, so we render a stable UTC placeholder first, then swap to
// local time after mount — avoiding a hydration mismatch (CLAUDE.md §4.1).
export function LocalTime({
  iso,
  withDate = false,
}: {
  iso: string;
  withDate?: boolean;
}) {
  const format = withDate ? formatLocalDateTime : formatLocalTime;
  const [label, setLabel] = useState(() =>
    withDate
      ? new Intl.DateTimeFormat("en-GB", {
          weekday: "short",
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "UTC",
        }).format(new Date(iso))
      : new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "UTC",
        }).format(new Date(iso)),
  );

  useEffect(() => {
    setLabel(format(iso));
  }, [iso, format]);

  return (
    <time dateTime={iso} suppressHydrationWarning>
      {label}
    </time>
  );
}
