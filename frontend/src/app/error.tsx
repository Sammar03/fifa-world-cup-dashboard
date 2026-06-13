"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

// Root error boundary — renders a friendly message, never a stack trace
// (CLAUDE.md §12). Covers every page nested under the root layout.
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <h1 className="display text-[1.75rem]">Something went wrong</h1>
      <p className="max-w-sm text-[0.9375rem] text-muted">
        We couldn&apos;t load this page. The data may be temporarily
        unavailable — please try again.
      </p>
      <Button variant="secondary" onClick={reset}>
        Try again
      </Button>
    </div>
  );
}
