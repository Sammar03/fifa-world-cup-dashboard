# World Cup 2026 — Dashboard (Frontend)

The Next.js 15 frontend for the FIFA World Cup Intelligence Dashboard: live
fixtures, group standings, top scorers, team stats, match detail, and AI match
insights. Design system (four colors, DM Sans, strict column tracks) and the
full architecture spec live in the project context archive at
`Projects/Reference/fifa-world-cup-dashboard/` (`docs/dashboard.md`).

## Stack

- **Next.js 15** (App Router) · **React 19** · **TypeScript** (strict)
- **Tailwind CSS v4** · shadcn-style primitives · **lucide-react** icons
- **Vitest** + Testing Library

## Architecture note

The frontend reads **only** from the dashboard's own API — never a third-party
API or LLM on the request path (CLAUDE.md §5.1). All data access goes through the
single typed client in `src/lib/api.ts`, which points at the FastAPI backend via
`NEXT_PUBLIC_API_BASE_URL`. The backend must be running for the app to show data.

## Getting started

```bash
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL to your backend
npm run dev                  # http://localhost:3000
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | FastAPI backend base URL. |

## Scripts

```bash
npm run dev      # start the dev server
npm run build    # production build
npm run start    # serve the production build
npm run lint     # ESLint
npm run test     # Vitest (run once)
npm run test:watch
```

## Routes

| Route | Description |
|---|---|
| `/` | Live + upcoming fixtures grouped by day (live matches pinned, 30s polling) |
| `/standings` | Group tables with the FIFA 2026 tiebreaker; instant group switch |
| `/scorers` | Top scorers; client-side goals/assists sort |
| `/match/[id]` | Match detail: score, goal timeline, stats, AI insight |
| `/team/[id]` | Team aggregates + recent form |

## Structure

```
src/
  app/                 # App Router pages + loading/error/not-found
  components/          # UI primitives (ui/) + domain components
  hooks/               # useLiveFixtures (live polling)
  lib/                 # api client, mock data, formatting, sort logic
  types/               # shared domain types (mirror the backend contracts)
```

## Tests

```bash
npm run test
```

Covers the FixtureCard LIVE badge, the FIFA tiebreaker ordering, the client-side
scorer sort, the `useLiveFixtures` interval cleanup, and the API client URL
building (CLAUDE.md §13).
