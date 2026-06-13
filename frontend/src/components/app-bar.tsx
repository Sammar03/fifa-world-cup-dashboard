"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Fixtures" },
  { href: "/standings", label: "Standings" },
  { href: "/scorers", label: "Player Stats" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/match");
  return pathname.startsWith(href);
}

// Transparent bar capped by the tri-color host-nation stripe — the page artwork
// shows through it, just like the fixture cards. A backdrop blur keeps nav text
// legible when content scrolls underneath. Active nav item is a solid brand
// pill; the rest brighten on hover.
export function AppBar() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-50 border-b border-line text-ink backdrop-blur-md">
      <div className="tri-stripe h-[3px]" aria-hidden />
      <div className="app-container flex h-14 items-center justify-between md:h-16">
        <Link
          href="/"
          className="group flex items-center gap-2.5"
          aria-label="FIFA World Cup 26 — home"
        >
          <Image
            src="/fifa-wc26-logo.png"
            alt="FIFA World Cup 26"
            width={36}
            height={36}
            priority
            // Dark Reader rewrites the inline style next/image sets on the <img>;
            // suppress the resulting (harmless) hydration warning.
            suppressHydrationWarning
            className="notch-sm size-9 bg-black object-contain p-0.5"
          />
          {/* On phones the wordmark hides (the logo mark still links home) so
              the longer nav labels — e.g. "Player Stats" — never overflow the
              bar; it returns from the sm breakpoint up. */}
          <span className="display hidden text-[1.125rem] leading-none tracking-[0.04em] sm:inline">
            FIFA World Cup
            <span className="ml-1.5 text-positive">26</span>
          </span>
        </Link>
        <nav aria-label="Primary" className="flex items-center gap-1">
          {NAV.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-full px-3 py-1.5 text-[0.875rem] font-medium transition-colors",
                  active
                    ? "bg-surface text-ink"
                    : "text-muted hover:bg-surface/50 hover:text-ink",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
