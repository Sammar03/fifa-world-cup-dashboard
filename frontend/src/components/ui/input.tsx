import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => (
  <input
    ref={ref}
    type={type}
    className={cn(
      "h-10 w-full rounded-lg border border-line bg-surface px-3 text-[1rem] text-ink transition-colors placeholder:text-muted hover:border-line-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-positive disabled:cursor-not-allowed disabled:opacity-50",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";
