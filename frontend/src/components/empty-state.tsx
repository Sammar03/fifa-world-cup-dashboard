// Graceful emptiness: a centered muted caption + one line of guidance — never a
// blank screen (dashboard.md §1, §7).
export function EmptyState({
  title,
  hint,
}: {
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-line-strong bg-card/50 px-6 py-16 text-center">
      <p className="text-[0.9375rem] font-medium text-muted">{title}</p>
      {hint && <p className="text-[0.8125rem] text-muted">{hint}</p>}
    </div>
  );
}
