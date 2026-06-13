import Image from "next/image";
import { cn } from "@/lib/utils";

// Flags are the only place color outside the four appears (dashboard.md §8).
// Small, rounded, never letting flag colors leak into surrounding chrome.
export function TeamFlag({
  src,
  name,
  className,
  width = 22,
}: {
  src: string | null;
  name: string;
  className?: string;
  width?: number;
}) {
  const height = Math.round((width * 3) / 4);
  if (!src) {
    return (
      <span
        aria-hidden
        className={cn(
          "inline-block rounded-[2px] bg-surface",
          className,
        )}
        style={{ width, height }}
      />
    );
  }
  return (
    <Image
      src={src}
      alt={`${name} flag`}
      width={width}
      height={height}
      className={cn("rounded-[2px] object-cover", className)}
    />
  );
}
