# ADR-003: Self-computed standings, not provider standings

**Status:** Accepted
**Date:** 2026-06-12
**References:** `docs/api-research.md` §6.3; `CLAUDE.md` §4.2, §5.2; `master-project-prompt.md` §8.3

---

## Context

Standings are the table fans trust most, so they must be correct and internally
consistent with the fixture results the app already shows. Provider standings
can lag, disagree with each other, or disagree with the raw results we display —
and serving a provider's table directly would hide any such inconsistency rather
than surface it. The 2026 group stage also has a specific official tiebreaker
order that must be applied deterministically.

## Decision

**Never serve standings from a provider directly.** Recompute them from raw
finished-fixture data on every ingestion run (the `aggregate()` step):

1. For each `finished` fixture, award points from the score:
   home win → home +3; draw → both +1; away win → away +3.
2. Increment `played`, `won`, `drawn`, `lost`, `goals_for`, `goals_against`.
   `goal_diff` is a stored generated column (`goals_for - goals_against`).
3. Sort each group by the **official FIFA 2026 tiebreaker**:
   1. points DESC
   2. goal difference DESC
   3. goals for DESC
   4. team name ASC (alphabetical)

After computing, diff the result against the football-data.org standings
endpoint. If any team's points differ by more than 0, emit a **CRITICAL** log —
it indicates either an aggregator bug or a source data error.

Derived tables (`standings`, `scorer_stats`) are recomputed each run from the
raw tables — never hand-entered, never edited in place by humans.

## Consequences

**Positive**
- One source of truth (raw fixtures) for everything derived from it; eliminates
  an entire class of "the table disagrees with the scores" bugs.
- The recomputation is the visible "data processing" competency for reviewers.
- The cross-check turns a silent disagreement into a loud, actionable alert.

**Negative / mitigations**
- A bug in the aggregator would surface directly in the standings. Mitigated by
  the football-data.org diff above and by required unit tests
  `test_standings_computed_correctly` and `test_fifa_tiebreaker_ordering`
  (CLAUDE.md §13).
- Tiebreakers beyond the four listed (e.g. head-to-head, fair-play points) are
  out of MVP scope; the alphabetical final tiebreaker is deterministic and
  sufficient for the demo.
