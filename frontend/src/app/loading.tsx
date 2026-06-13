import { Skeleton } from "@/components/ui/skeleton";

// Skeleton matches the fixtures layout — no spinner for page content (§7).
export default function Loading() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      </div>
    </div>
  );
}
