import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// Pills (999px), label type, uppercase, +0.02em (dashboard.md §6.8, §3.2).
// Color must carry meaning: positive=win, negative=loss/live, muted=draw/neutral.
const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.75rem] font-medium uppercase tracking-[0.02em]",
  {
    variants: {
      variant: {
        live: "bg-negative text-paper",
        positive: "bg-positive-wash text-positive",
        negative: "bg-negative-wash text-negative",
        draw: "bg-surface text-muted",
        brand: "bg-brand-wash text-paper",
        neutral: "border border-line bg-surface/50 text-muted",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
