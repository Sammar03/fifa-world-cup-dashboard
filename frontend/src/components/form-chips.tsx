import type { FormResult } from "@/types";
import { cn } from "@/lib/utils";

// W/D/L chips: fixed 20px squares, color-coded, but the letter is always
// present so color is never the only signal (dashboard.md §6.3, §10).
const CHIP: Record<FormResult, string> = {
  W: "bg-positive text-paper",
  D: "bg-surface text-muted",
  L: "bg-negative text-paper",
};

const LABEL: Record<FormResult, string> = {
  W: "Win",
  D: "Draw",
  L: "Loss",
};

export function FormChips({
  form,
  className,
}: {
  form: FormResult[];
  className?: string;
}) {
  if (!form.length) {
    return <span className="text-muted">—</span>;
  }
  return (
    <div className={cn("flex gap-1", className)} role="img" aria-label={`Recent form: ${form.map((r) => LABEL[r]).join(", ")}`}>
      {form.map((r, i) => (
        <span
          key={i}
          aria-hidden
          className={cn(
            "grid size-5 place-items-center rounded-[4px] text-[0.6875rem] font-semibold",
            CHIP[r],
          )}
        >
          {r}
        </span>
      ))}
    </div>
  );
}
