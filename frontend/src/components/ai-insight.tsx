import { Sparkles } from "lucide-react";
import type { AIInsight } from "@/types";

// Bordered card, brand-wash, small "AI" pill (dashboard.md §6.6). Hidden
// entirely if there is no cached insight — never a spinner on the request path
// (CLAUDE.md §4.6).
export function AIInsightBlock({
  insight,
}: {
  insight: AIInsight | null | undefined;
}) {
  if (!insight) return null;

  return (
    <section
      aria-label="AI match insight"
      className="rise-in notch relative overflow-hidden bg-gradient-to-br from-brand-wash to-card p-4 md:p-6"
      style={{ animationDelay: "60ms" }}
    >
      <div className="tri-stripe absolute inset-x-0 top-0 h-[3px]" aria-hidden />
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-flex items-center gap-1 rounded-full bg-brand px-2 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.02em] text-paper">
          <Sparkles className="size-3" aria-hidden />
          AI
        </span>
        <span className="text-[0.75rem] font-medium uppercase tracking-[0.04em] text-paper/70">
          {insight.state === "scheduled" ? "Match preview" : "Result summary"}
        </span>
      </div>
      <p className="text-[1rem] leading-relaxed text-ink">{insight.content}</p>
    </section>
  );
}
