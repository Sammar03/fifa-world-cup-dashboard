# ADR-004: Constrained natural-language query — tool-select, no raw SQL generation

**Status:** Accepted
**Date:** 2026-06-12
**References:** `CLAUDE.md` §4.7, §8.3; `docs/prd.md` §5.7; `master-project-prompt.md` §7.4; `BACKLOG.md` BACKLOG-001

---

## Context

The "ask the data" box (PRD §5.7) lets a user type a question and get an answer
with the supporting number. For a feature where correctness is the whole point,
having an LLM generate arbitrary SQL is unsafe (injection surface, malformed
queries) and hallucination-prone (confident but wrong stats). A reviewer should
see a *safe* AI pattern, not a risky one.

## Decision

Use a **constrained / tool-select** design. The LLM does not write SQL or prose
stats — it **selects from a whitelist of ~10 predefined query patterns** and
fills their parameters. Each pattern maps to a known, parameterised query over
the existing aggregate tables (`scorer_stats`, `standings`, `fixtures`,
`match_stats`). The 10 patterns are fixed in CLAUDE.md §8.3 (top scorer, most
goals by a team, best defence, most wins, group leader, clean sheets, most
assists, highest-scoring match, most yellow cards, matches played).

Response contract (`POST /query`):

```
{ answer: string,
  evidence: { metric: string, value: number|string, team?: string, player?: string },
  supported: boolean }
```

For any question outside the whitelist, return an **honest refusal** —
`supported: false`, `evidence: null`, and the message: *"I can't answer that yet
— I only know about goals, standings, scorers, and cards."* — never an invented
stat. The prompt lives in `backend/app/ai/prompts/nl_query_v1.txt` (a versioned
file, not an inline string).

## Consequences

**Positive**
- No raw-SQL surface: the LLM can only trigger pre-vetted, parameterised queries.
- Demo-stable and predictable; numeric evidence always comes from the DB.
- Honest refusals beat confident hallucinations — the safer-AI story.

**Negative / mitigations**
- Coverage is limited to the 10 whitelisted patterns. Accepted for MVP (KL-003);
  broader coverage and chart output are tracked in BACKLOG-001 and BACKLOG-012.
- This is the first feature on the cut list (CLAUDE.md §15). If time runs short
  it ships as a "coming soon" UI stub with `POST /query` returning **501**, but
  this design remains fixed for when it is implemented.
