import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}
