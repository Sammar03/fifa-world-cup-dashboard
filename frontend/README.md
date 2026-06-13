# World Cup 2026 — Dashboard (Frontend)

The Next.js 15 frontend for the FIFA World Cup Intelligence Dashboard: live
fixtures, group standings, top scorers, team stats, match detail, and AI match
insights. Built per `../docs/dashboard.md` (four colors, DM Sans, strict column
tracks) and the architecture in `../CLAUDE.md`.

## Stack

- **Next.js 15** (App Router) · **React 19** · **TypeScript** (strict)
- **Tailwind CSS v4** · shadcn-style primitives · **lucide-react** icons
- **Vitest** + Testing Library

## Architecture note

The frontend reads **only** from the dashboard's own API — never a third-party
API or LLM on the request path (CLAUDE.md §5.1). All data access goes through the
single typed client in `src/lib/api.ts`.

During this phase there is no backend, so the client serves a built-in mock
dataset. The standings, form, and scorer totals in the mock are **derived** from
the fixtures/goals using the real FIFA tiebreaker, so the tables are internally
consistent. Flip to the real backend with two env vars — no component changes.

## Getting started

```bash
npm install
cp .env.example .env.local   # defaults serve mock data
npm run dev                  # http://localhost:3000
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_USE_MOCKS` | `true` | Serve the mock dataset. Set `false` to call the backend. |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | FastAPI backend base URL (used when mocks are off). |

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
