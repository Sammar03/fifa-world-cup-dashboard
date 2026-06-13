import { cn } from "@/lib/utils";

// Loading skeletons are raised blocks with a sweeping shimmer, matching the
// final layout — no spinners for page content (dashboard.md §7).
export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("skeleton-shimmer rounded-lg", className)}
      {...props}
    />
  );
}
