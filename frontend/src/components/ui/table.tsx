import * as React from "react";
import { cn } from "@/lib/utils";

// Real <table> semantics with <th scope> for tabular data (dashboard.md §10).
// Wrapper scrolls horizontally on mobile — columns keep their width, never
// merge or wrap (dashboard.md §4.3, §9).
export function Table({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto">
      <table
        className={cn("w-full border-collapse text-[0.875rem]", className)}
        {...props}
      />
    </div>
  );
}

export function TableHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn(className)} {...props} />;
}

export function TableBody({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn(className)} {...props} />;
}

export function TableRow({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "border-b border-line transition-colors last:border-0 hover:bg-surface/70",
        className,
      )}
      {...props}
    />
  );
}

export function TableHead({
  className,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn(
        "px-2 py-2 text-left text-[0.75rem] font-medium uppercase tracking-[0.02em] text-muted sm:px-3",
        className,
      )}
      {...props}
    />
  );
}

export function TableCell({
  className,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn("px-2 py-2.5 align-middle sm:px-3", className)}
      {...props}
    />
  );
}
