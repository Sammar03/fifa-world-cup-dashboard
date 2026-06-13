"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import type { QueryResponse } from "@/types";
import { cn } from "@/lib/utils";
import { postQuery } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// "Ask the data" box. The constrained NL query ships as a stub this phase
// (CLAUDE.md §4.7 / BACKLOG-001): the endpoint returns an honest refusal, shown
// in muted text — a refusal is not an error (dashboard.md §6.9).
export function NLQueryBox() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    try {
      setResult(await postQuery(q));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="notch border-l-2 border-line-strong p-4 md:p-6">
      <div className="mb-1 flex items-center gap-2">
        <Badge variant="brand">Ask the data</Badge>
        <span className="text-[0.75rem] text-muted">Coming soon</span>
      </div>
      <p className="mb-3 text-[0.875rem] text-muted">
        Ask about goals, standings, scorers, or cards.
      </p>
      <form onSubmit={onSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            aria-hidden
          />
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Who is the top scorer?"
            maxLength={500}
            aria-label="Ask a question about the data"
            className="pl-9"
          />
        </div>
        <Button type="submit" disabled={loading || !question.trim()}>
          Ask
        </Button>
      </form>

      {result && (
        <div className="mt-3 rounded-lg border border-line bg-surface p-3">
          <p
            className={cn(
              "text-[0.9375rem]",
              result.supported ? "text-ink" : "text-muted",
            )}
          >
            {result.answer}
          </p>
          {result.evidence && (
            <p className="mt-1 text-[0.875rem] text-muted">
              {result.evidence.metric}:{" "}
              <span className="font-bold text-positive">
                {result.evidence.value}
              </span>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
