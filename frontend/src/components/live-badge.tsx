import { Badge } from "@/components/ui/badge";

// LIVE = solid negative pill + pulsing paper dot + minute (dashboard.md §6.2, §6.8).
export function LiveBadge({ minute }: { minute: number | null }) {
  return (
    <Badge variant="live">
      <span className="live-dot" aria-hidden />
      <span>Live</span>
      {minute != null && <span className="tabular font-semibold">{minute}&apos;</span>}
    </Badge>
  );
}
