import type { Metadata } from "next";
import { Anton, DM_Sans } from "next/font/google";
import "./globals.css";
import { AppBar } from "@/components/app-bar";

// DM Sans for body/UI/tables; Anton — a condensed sports-poster display face —
// for headlines, scores, and the big scoreboard numerals.
const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-dm-sans",
});

const anton = Anton({
  subsets: ["latin"],
  weight: "400",
  display: "swap",
  variable: "--font-anton",
});

export const metadata: Metadata = {
  title: "World Cup 2026 — Intelligence Dashboard",
  description:
    "Live FIFA World Cup 2026 fixtures, standings, top scorers, team stats, and AI match insights.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning: browser extensions (e.g. Dark Reader) inject
    // attributes on <html>/<body> before React hydrates; that is harmless and
    // outside our control, so we silence the resulting mismatch warning.
    <html
      lang="en"
      suppressHydrationWarning
      className={`${dmSans.variable} ${anton.variable} h-full`}
    >
      <body
        suppressHydrationWarning
        className="flex min-h-full flex-col bg-pitch text-ink"
      >
        <AppBar />
        <main className="app-container flex-1 py-6 md:py-8">{children}</main>
        <footer className="mt-10 border-t border-line">
          <div className="app-container flex flex-col gap-5 py-6 text-[0.75rem] text-muted md:flex-row md:items-start md:justify-between">
            <div className="max-w-2xl">
              <p>
                This dashboard is a personal skill-building project and has{" "}
                <span className="text-ink">no affiliation or association with
                FIFA</span>. The data shown may be incomplete or incorrect and
                any decision you make based on it is your own responsibility.
              </p>
            </div>
            <div className="flex flex-col items-start gap-3 md:items-end">
              <div className="flex items-center gap-4">
                <a
                  href="https://www.linkedin.com/in/syed-sammar-ali-shah/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium text-muted transition-colors hover:text-ink"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    aria-hidden
                    className="size-4"
                  >
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                  LinkedIn
                </a>
                <a
                  href="https://github.com/Sammar03"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium text-muted transition-colors hover:text-ink"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    aria-hidden
                    className="size-4"
                  >
                    <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                  </svg>
                  GitHub
                </a>
              </div>
              <span className="tri-stripe h-1 w-14 rounded-full" aria-hidden />
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
