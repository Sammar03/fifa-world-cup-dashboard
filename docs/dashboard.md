# FIFA World Cup Intelligence Dashboard — Design System & UI Guide

**Version:** 1.0
**Scope:** Visual language, layout patterns, and component conventions for the Next.js 15 frontend.
**Hard constraints (non-negotiable):**
1. **Exactly four colors** — `#308A2F`, `#222E71`, `#B6141B`, `#313537`. No other hues.
2. **Single typeface** — DM Sans.
3. **Strict columns** — proper spacing, **no interlocked columns, no combined/merged columns.** Every column stands on its own grid track.

This document is the source of truth. If a component contradicts it, the component is wrong.

---

## 1. Design Principles

1. **Read-at-a-glance.** A fan checks scores in 3 seconds. Hierarchy and contrast do the work, not labels.
2. **Calm canvas, loud signals.** Surfaces stay neutral; color is reserved for meaning (live, win, loss, action).
3. **One grid, honored everywhere.** Spacing, alignment, and column tracks are consistent across every page.
4. **Data is the hero.** Chrome recedes. No decorative gradients, shadows-for-show, or ornament.
5. **Graceful emptiness.** Every list, table, and stat has a defined empty and loading state.

---

## 2. Color System

Only these four colors exist in the product. White (`#FFFFFF`) is treated as the absence of color — the paper the UI is printed on — and `#313537` doubles as the near-black text/ink. No greys, blues, greens, or reds outside the four are permitted. Tints are produced **only** by applying opacity of these four over white; never by introducing a new hex.

| Token | Hex | Role |
|---|---|---|
| `--brand` | `#222E71` | Primary brand. App bar, primary buttons, links, active nav, headings, focus rings. |
| `--positive` | `#308A2F` | Success / positive. Wins, "LIVE" online state, gains, confirmation. |
| `--negative` | `#B6141B` | Alert / negative. Losses, errors, the LIVE match badge, destructive emphasis. |
| `--ink` | `#313537` | Text and structure. Body copy, table text, borders, neutral surfaces, icons. |
| `--paper` | `#FFFFFF` | Base canvas / surface (non-color). |

### 2.1 Derived tints (opacity over `--paper` only)

Use these instead of inventing colors. Express as `color-mix` or `rgba` of the four base hexes.

| Purpose | Recipe |
|---|---|
| Page background | `--paper` (`#FFFFFF`) |
| Subtle surface / zebra row | `--ink` @ 4% over paper |
| Hairline border / divider | `--ink` @ 12% |
| Strong border | `--ink` @ 24% |
| Muted / secondary text | `--ink` @ 64% |
| Body text | `--ink` @ 100% |
| Brand wash (hover, selected) | `--brand` @ 8% |
| Positive wash (chip bg) | `--positive` @ 12% |
| Negative wash (chip bg) | `--negative` @ 12% |

### 2.2 Semantic mapping (football context)

| Meaning | Color |
|---|---|
| Win (W) | `--positive` |
| Loss (L) | `--negative` |
| Draw (D) | `--ink` @ 64% |
| LIVE badge | `--negative` (solid, pulsing dot) |
| Scheduled / upcoming | `--ink` @ 64% |
| Finished (final) | `--ink` |
| Primary action / link | `--brand` |
| Selected group / active tab | `--brand` |

> **Rule:** color must carry meaning. Never use `--positive` or `--negative` decoratively — green means good/win, red means bad/loss/live. Mixing them as accents dilutes the signal.

### 2.3 Contrast

All text must meet WCAG AA (4.5:1 body, 3:1 large). `--ink` and `--brand` on `--paper` pass. White text is only allowed on solid `--brand`, `--positive`, `--negative`, or `--ink` fills.

---

## 3. Typography — DM Sans

DM Sans for **everything** (UI, headings, numerals, tables). Load via `next/font/google` with `display: swap`. No secondary font, no system fallback styling beyond the metric-matched fallback.

```ts
import { DM_Sans } from "next/font/google";
export const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-dm-sans",
});
```

### 3.1 Type scale (1.25 ratio, rem)

| Token | Size / Line | Weight | Use |
|---|---|---|---|
| `display` | 2.5rem / 1.1 | 700 | Page hero scoreline, big numbers |
| `h1` | 2rem / 1.2 | 700 | Page titles |
| `h2` | 1.5rem / 1.25 | 600 | Section headers |
| `h3` | 1.25rem / 1.3 | 600 | Card titles |
| `body-lg` | 1.125rem / 1.5 | 400 | Lead text |
| `body` | 1rem / 1.5 | 400 | Default |
| `label` | 0.875rem / 1.4 | 500 | Table headers, form labels, badges |
| `caption` | 0.75rem / 1.4 | 500 | Meta, timestamps, footnotes |

### 3.2 Numeric data

- Use **tabular figures** (`font-variant-numeric: tabular-nums`) for **all** scores, table stats, minutes, and standings so digits align in columns.
- Scorelines and standings points: weight 600–700.
- Never letter-space body text; `+0.02em` is allowed on uppercase `label`/badge text only.

---

## 4. Spacing & Grid

### 4.1 Spacing scale (8px base)

`4, 8, 12, 16, 24, 32, 48, 64` px. Use these tokens (`space-1`=4 … ) and nothing in between. Vertical rhythm between sections: 32–48px. Card inner padding: 16–24px.

### 4.2 Layout grid

- **Container max-width:** 1200px, centered, 24px side gutters (16px on mobile).
- **12-column grid**, 24px gutter on desktop, 16px on tablet, single column on mobile.
- Content blocks snap to grid columns — no arbitrary widths.

### 4.3 Column discipline (the hard rule)

> **No interlocked columns. No combined/merged columns. No `colspan`/`rowspan` in data tables.**

- Every column occupies its **own dedicated track** with a fixed semantic meaning top to bottom.
- Columns never bleed into, overlap, or borrow space from neighbors. Gutters between columns are uniform and always present (min 16px).
- A cell holds **one** datum. Do not pack "team + flag + form" into a single column as a blob — give flag, name, and form their own aligned columns (or render flag as an inline icon *within* the name column only when it's purely decorative, never as shared data).
- Headers align 1:1 with their column below; no header spans two columns.
- Tables scroll horizontally on mobile (each column keeps its width) rather than wrapping or merging.

```
GOOD (independent tracks, uniform gutters)
┌──────┬──────────────┬────┬────┬────┬─────┐
│ POS  │ TEAM         │ P  │ GD │ Pts│ Form│
├──────┼──────────────┼────┼────┼────┼─────┤
│  1   │ Argentina    │ 3  │ +5 │  9 │ WWW │
└──────┴──────────────┴────┴────┴────┴─────┘

BAD (merged "team+stats" blob, interlocked, uneven gaps)
┌─────────────────────────┬──────────┐
│ 1 Argentina  P3 GD+5 9pts│ WWW      │   ✗ do not do this
└─────────────────────────┴──────────┘
```

### 4.4 Alignment

- Text columns: **left-aligned.**
- Numeric columns (P, W, D, L, GF, GA, GD, Pts, goals, assists): **right-aligned** (or centered for single-digit-only columns), with tabular numerals so they line up.
- Column headers share the alignment of their data.

---

## 5. Elevation, Radius, Borders

- **Radius:** `8px` standard (cards, inputs, badges `999px` pill). One radius family — don't mix.
- **Borders over shadows.** Default separation is a `--ink @ 12%` hairline. Use shadow sparingly and only for genuinely floating layers (dropdowns, dialogs): `0 4px 16px rgba(49,53,55,0.12)` — derived from `--ink`, no new color.
- No gradients. No glows. No neumorphism.

---

## 6. Core Components

### 6.1 App bar / Nav
- Solid `--brand` background, `--paper` text and logo. Active item underlined or with a `--paper` pill.
- Sticky on scroll. Height 64px desktop / 56px mobile.

### 6.2 Fixture card
- `--paper` surface, hairline border, 8px radius, 16px padding.
- Layout: **home block | score block | away block** as three independent columns (centered score). Status/badge sits in its own row above, not merged into the score.
- LIVE: `--negative` pill, top-left, with a pulsing dot. Minute in `--negative`.
- Finished: final score in `--ink` 700; result tints the winner's name subtly (`--positive` wash optional, never both teams colored).
- Entire card is a link to `/match/[id]`; hover = `--brand @ 8%` wash.

### 6.3 Standings table
- Strict column tracks per §4.3. Columns: `POS · TEAM · P · W · D · L · GF · GA · GD · Pts · Form`.
- Zebra rows via `--ink @ 4%`. Qualifying line: a 2px `--brand` bottom border under the cutoff row (no fill).
- `Form` column: row of W/D/L chips (`--positive` / `--ink@64%` / `--negative`), each chip a fixed 20px square, evenly spaced — chips do not merge.
- Active group tab: `--brand` underline + `--brand` text; inactive: `--ink @ 64%`.

### 6.4 Scorers leaderboard
- Columns: `RANK · PLAYER · TEAM · MP · A · G`. Goals right-most, bold. Each its own track.
- Sortable headers (goals default, assists) — sort arrow is `--brand`. Client-side, instant.

### 6.5 Team stats page
- Header band: `--brand` with team name in `--paper`, recent-form chips.
- Stats shown as a **uniform stat-grid**: each stat = one cell `{label (caption, --ink@64%), value (h2, --ink)}`. Cells are equal-width grid items with consistent gutters — never two stats crammed in one cell.
- Missing value renders `—` in `--ink @ 64%`. Never blank, never crash.

### 6.6 Match detail
- Score header (display size, tabular), status badge, venue caption.
- Goal timeline: vertical list, minute in its own left column, scorer in the next — two clean tracks.
- Stat comparison rows: `home value | label | away value` as three fixed columns; the bar between them may fill with `--brand` (home) vs `--ink@24%` (away), but the numbers stay in their own columns.
- **AI Insight block:** bordered card, `--brand @ 8%` wash, small "AI" label pill in `--brand`. 2–4 sentences, `body`. Hidden entirely if no cached insight (never a spinner on the request path).

### 6.7 Buttons
| Variant | Fill | Text | Use |
|---|---|---|---|
| Primary | `--brand` | `--paper` | Main action |
| Secondary | `--paper`, `--brand` border | `--brand` | Secondary |
| Ghost | transparent | `--ink` | Low emphasis |
| Danger | `--negative` | `--paper` | Rare; destructive |

Height 40px, 16px horizontal padding, 8px radius, weight 500. Focus: 2px `--brand` ring offset 2px.

### 6.8 Badges / chips
- Pill (`999px`), `label` type, uppercase, `+0.02em`.
- LIVE = solid `--negative` + paper text. W/D/L = washed backgrounds per §2.2.

### 6.9 NL Query box (stretch)
- Single input, `--brand` focus ring, search icon `--ink @ 64%`.
- Answer card: sentence in `body`, the supporting number emphasized in `--brand` 700.
- Refusal state: plain `--ink @ 64%` text, no red (a refusal isn't an error).

---

## 7. States

| State | Treatment |
|---|---|
| Loading | Skeletons in `--ink @ 4%` blocks matching final layout. No spinners for page content. |
| Empty | Centered caption in `--ink @ 64%` + one-line guidance ("No matches today — check back at kickoff"). |
| Error | Inline `--negative` text + retry; never a blank screen. |
| Live | `--negative` LIVE pill, client polls every 30s, subtle row highlight. |
| Selected / active | `--brand` text + `--brand @ 8%` wash. |
| Hover (interactive) | `--brand @ 8%` wash; cursor pointer. |
| Focus (keyboard) | 2px `--brand` ring, offset 2px. Always visible. |

---

## 8. Iconography & Imagery

- One icon set (e.g. Lucide), stroke 1.5–2px, colored `--ink` or `--brand` only.
- Team flags: the **only** place outside the four colors may appear, because flags are data/imagery, not UI chrome. Keep them small, square/rounded, and never let flag colors leak into surrounding UI styling.
- No photographic backgrounds behind text.

---

## 9. Responsive

| Breakpoint | Width | Behavior |
|---|---|---|
| Mobile | < 640px | Single column. Tables scroll horizontally (columns keep width — never merge). Nav collapses. |
| Tablet | 640–1024px | 8-col grid, 16px gutters. Cards 2-up. |
| Desktop | > 1024px | 12-col grid, 24px gutters, 1200px container. |

Touch targets ≥ 44px. Live polling continues on mobile.

---

## 10. Accessibility

- WCAG AA contrast on all text (§2.3).
- Semantic HTML: real `<table>` for tabular data (with `<th scope>`), `<nav>`, `<main>`, headings in order.
- Keyboard navigable end to end; visible focus rings (§7).
- Color is never the **only** signal: W/D/L chips also carry the letter; LIVE has text + dot.
- Respect `prefers-reduced-motion` — disable the LIVE pulse and polling fade.

---

## 11. Do / Don't

**Do**
- Keep every column on its own track with uniform gutters.
- Reserve `--positive`/`--negative` for win/loss/live meaning.
- Use tabular numerals for all stats.
- Define empty + loading for every data view.

**Don't**
- Introduce any fifth color, gradient, or grey outside the four.
- Merge, span, or interlock columns, or pack multiple data points in one cell.
- Use red/green decoratively.
- Block page render on AI or third-party calls.

---

## 12. Token Reference (CSS variables)

```css
:root {
  /* The only four colors */
  --brand: #222E71;
  --positive: #308A2F;
  --negative: #B6141B;
  --ink: #313537;
  --paper: #ffffff;

  /* Derived (opacity of the four only) */
  --surface: color-mix(in srgb, var(--ink) 4%, var(--paper));
  --border: color-mix(in srgb, var(--ink) 12%, var(--paper));
  --border-strong: color-mix(in srgb, var(--ink) 24%, var(--paper));
  --text-muted: color-mix(in srgb, var(--ink) 64%, var(--paper));
  --brand-wash: color-mix(in srgb, var(--brand) 8%, var(--paper));
  --positive-wash: color-mix(in srgb, var(--positive) 12%, var(--paper));
  --negative-wash: color-mix(in srgb, var(--negative) 12%, var(--paper));

  /* Type */
  --font-dm-sans: "DM Sans", sans-serif;

  /* Spacing (8pt) */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-6: 24px; --space-8: 32px; --space-12: 48px; --space-16: 64px;

  /* Radius */
  --radius: 8px;
  --radius-pill: 999px;

  /* Elevation (derived from --ink only) */
  --shadow-pop: 0 4px 16px rgba(49, 53, 55, 0.12);
}
```

---

*This guide pairs with `prd.md`. The PRD defines **what** the dashboard does; this defines **how it looks and holds together.***
