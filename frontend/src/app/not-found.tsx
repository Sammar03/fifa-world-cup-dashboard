import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <p className="display text-[4rem] text-muted/40">404</p>
      <h1 className="display text-[1.75rem]">Page not found</h1>
      <p className="max-w-sm text-[0.9375rem] text-muted">
        That match or team doesn&apos;t exist — it may have been removed or the
        link is incorrect.
      </p>
      <Link href="/" className={buttonVariants({ variant: "secondary" })}>
        Back to fixtures
      </Link>
    </div>
  );
}
