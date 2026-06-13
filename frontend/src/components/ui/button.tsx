import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// Variants follow dashboard.md §6.7. 40px height, 16px horizontal padding,
// 8px radius, weight 500. Focus ring is provided globally + reinforced here.
export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-[0.875rem] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-positive disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-positive text-paper hover:brightness-110",
        secondary:
          "border border-line-strong bg-card text-ink hover:border-positive hover:text-positive",
        ghost: "bg-transparent text-ink hover:bg-surface",
        danger: "bg-negative text-paper hover:brightness-110",
      },
      size: {
        default: "h-10 px-4",
        sm: "h-8 px-3 text-[0.8125rem]",
        icon: "size-10",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";
