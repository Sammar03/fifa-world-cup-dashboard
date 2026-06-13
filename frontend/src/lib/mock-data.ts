// =============================================================================
// Mock dataset for the dashboard phase.
//
// The frontend talks only to the typed client in `api.ts`. While the FastAPI
// backend does not yet exist, that client serves this mock data (toggled by
// NEXT_PUBLIC_USE_MOCKS). When the backend lands, flip the env var — no
// component changes required.
//
// Standings, form, and scorer goal-counts are DERIVED here from the fixtures and
// goals below (the same logic the backend's aggregator will own), so every
// table stays internally consistent. Player assists / matches-played and the
// per-match advanced stats are authored, since they cannot be derived from
// scores alone.
// =============================================================================

import type {
  AIInsight,
  Fixture,
  FixturesResponse,
  FixtureDetailResponse,
  FormResult,
  Goal,
  MatchStats,
  ScorerStat,
  ScorersResponse,
  Standing,
  StandingsResponse,
  TeamAggregate,
  TeamRef,
  TeamResponse,
} from "@/types";
import { dayKey } from "@/lib/format";
import { sortByFifaTiebreaker } from "@/lib/standings";
import { sortScorers } from "@/lib/scorers";

const flag = (iso: string) => `https://flagcdn.com/w80/${iso}.png`;

// --- Teams (12 across groups A, B, C) ---------------------------------------

const TEAMS: TeamRef[] = [
  { id: 1, name: "Brazil", code: "BRA", group_label: "A", flag_url: flag("br") },
  { id: 2, name: "Croatia", code: "CRO", group_label: "A", flag_url: flag("hr") },
  { id: 3, name: "Mexico", code: "MEX", group_label: "A", flag_url: flag("mx") },
  { id: 4, name: "Japan", code: "JPN", group_label: "A", flag_url: flag("jp") },
  { id: 5, name: "Argentina", code: "ARG", group_label: "B", flag_url: flag("ar") },
  { id: 6, name: "France", code: "FRA", group_label: "B", flag_url: flag("fr") },
  { id: 7, name: "Morocco", code: "MAR", group_label: "B", flag_url: flag("ma") },
  { id: 8, name: "South Korea", code: "KOR", group_label: "B", flag_url: flag("kr") },
  { id: 9, name: "England", code: "ENG", group_label: "C", flag_url: flag("gb-eng") },
  { id: 10, name: "Spain", code: "ESP", group_label: "C", flag_url: flag("es") },
  { id: 11, name: "United States", code: "USA", group_label: "C", flag_url: flag("us") },
  { id: 12, name: "Senegal", code: "SEN", group_label: "C", flag_url: flag("sn") },
];

const team = (code: string): TeamRef => {
  const t = TEAMS.find((x) => x.code === code);
  if (!t) throw new Error(`Unknown team code: ${code}`);
  return t;
};

// --- Fixtures ----------------------------------------------------------------

interface FixtureSeed {
  id: number;
  home: string;
  away: string;
  kickoff_at: string;
  venue: string;
  status: Fixture["status"];
  home_score: number | null;
  away_score: number | null;
  minute: number | null;
  round: string;
  verified: boolean;
}

const FIXTURE_SEEDS: FixtureSeed[] = [
  // Group A — matchday 1 (finished)
  { id: 1, home: "BRA", away: "CRO", kickoff_at: "2026-06-11T16:00:00Z", venue: "MetLife Stadium, East Rutherford", status: "finished", home_score: 2, away_score: 1, minute: null, round: "Group Stage", verified: true },
  { id: 2, home: "MEX", away: "JPN", kickoff_at: "2026-06-11T19:00:00Z", venue: "Estadio Azteca, Mexico City", status: "finished", home_score: 0, away_score: 0, minute: null, round: "Group Stage", verified: true },
  // Group A — matchday 2 (live + scheduled today)
  { id: 3, home: "BRA", away: "MEX", kickoff_at: "2026-06-12T16:00:00Z", venue: "SoFi Stadium, Los Angeles", status: "live", home_score: 1, away_score: 0, minute: 67, round: "Group Stage", verified: false },
  { id: 4, home: "CRO", away: "JPN", kickoff_at: "2026-06-12T19:00:00Z", venue: "AT&T Stadium, Arlington", status: "scheduled", home_score: null, away_score: null, minute: null, round: "Group Stage", verified: false },
  // Group A — matchday 3 (scheduled)
  { id: 5, home: "BRA", away: "JPN", kickoff_at: "2026-06-13T16:00:00Z", venue: "Mercedes-Benz Stadium, Atlanta", status: "scheduled", home_score: null, away_score: null, minute: null, round: "Group Stage", verified: false },
  { id: 6, home: "CRO", away: "MEX", kickoff_at: "2026-06-13T19:00:00Z", venue: "Lincoln Financial Field, Philadelphia", status: "scheduled", home_score: null, away_score: null, minute: null, round: "Group Stage", verified: false },

  // Group B — matchday 1 (finished)
  { id: 7, home: "ARG", away: "KOR", kickoff_at: "2026-06-11T22:00:00Z", venue: "Hard Rock Stadium, Miami", status: "finished", home_score: 3, away_score: 1, minute: null, round: "Group Stage", verified: true },
  { id: 8, home: "FRA", away: "MAR", kickoff_at: "2026-06-11T18:00:00Z", venue: "Levi's Stadium, Santa Clara", status: "finished", home_score: 2, away_score: 0, minute: null, round: "Group Stage", verified: true },
  // Group B — matchday 2 (live + scheduled today)
  { id: 9, home: "ARG", away: "FRA", kickoff_at: "2026-06-12T16:00:00Z", venue: "NRG Stadium, Houston", status: "live", home_score: 1, away_score: 1, minute: 52, round: "Group Stage", verified: false },
  { id: 10, home: "MAR", away: "KOR", kickoff_at: "2026-06-12T19:00:00Z", venue: "Arrowhead Stadium, Kansas City", status: "scheduled", home_score: null, away_score: null, minute: null, round: "Group Stage", verified: false },

  // Group C — matchday 1 (finished)
  { id: 11, home: "ENG", away: "ESP", kickoff_at: "2026-06-11T20:00:00Z", venue: "Gillette Stadium, Foxborough", status: "finished", home_score: 1, away_score: 1, minute: null, round: "Group Stage", verified: true },
  { id: 12, home: "USA", away: "SEN", kickoff_at: "2026-06-11T23:00:00Z", venue: "BMO Stadium, Los Angeles", status: "finished", home_score: 2, away_score: 1, minute: null, round: "Group Stage", verified: false },
  // Group C — matchday 2 (scheduled today + tomorrow)
  { id: 13, home: "ENG", away: "USA", kickoff_at: "2026-06-12T19:00:00Z", venue: "Lumen Field, Seattle", status: "scheduled", home_score: null, away_score: null, minute: null, round: "Group Stage", verified: false },
  { id: 14, home: "ESP", away: "SEN", kickoff_at: "2026-06-13T22:00:00Z", venue: "BC Place, Vancouver", status: "scheduled", home_score: null, away_score: null, minute: null, round: "Group Stage", verified: false },
];

const FIXTURES: Fixture[] = FIXTURE_SEEDS.map((s) => ({
  id: s.id,
  home_team: team(s.home),
  away_team: team(s.away),
  kickoff_at: s.kickoff_at,
  venue: s.venue,
  status: s.status,
  home_score: s.home_score,
  away_score: s.away_score,
  group_label: team(s.home).group_label,
  round: s.round,
  minute: s.minute,
  verified: s.verified,
}));

const fixtureById = (id: number) => FIXTURES.find((f) => f.id === id);

// --- Goals (feed the match timeline + scorer goal-counts) -------------------

interface GoalSeed {
  fixture_id: number;
  team: string;
  player_name: string;
  minute: number;
  type: Goal["type"];
}

const GOAL_SEEDS: GoalSeed[] = [
  // f1 BRA 2-1 CRO
  { fixture_id: 1, team: "BRA", player_name: "Vinícius Júnior", minute: 23, type: "regular" },
  { fixture_id: 1, team: "BRA", player_name: "Rodrygo", minute: 71, type: "regular" },
  { fixture_id: 1, team: "CRO", player_name: "Andrej Kramarić", minute: 80, type: "regular" },
  // f3 (live) BRA 1-0 MEX
  { fixture_id: 3, team: "BRA", player_name: "Raphinha", minute: 34, type: "regular" },
  // f7 ARG 3-1 KOR
  { fixture_id: 7, team: "ARG", player_name: "Lionel Messi", minute: 12, type: "penalty" },
  { fixture_id: 7, team: "ARG", player_name: "Julián Álvarez", minute: 40, type: "regular" },
  { fixture_id: 7, team: "ARG", player_name: "Lautaro Martínez", minute: 78, type: "regular" },
  { fixture_id: 7, team: "KOR", player_name: "Son Heung-min", minute: 55, type: "regular" },
  // f8 FRA 2-0 MAR
  { fixture_id: 8, team: "FRA", player_name: "Kylian Mbappé", minute: 22, type: "regular" },
  { fixture_id: 8, team: "FRA", player_name: "Olivier Giroud", minute: 60, type: "regular" },
  // f9 (live) ARG 1-1 FRA
  { fixture_id: 9, team: "ARG", player_name: "Julián Álvarez", minute: 30, type: "regular" },
  { fixture_id: 9, team: "FRA", player_name: "Kylian Mbappé", minute: 45, type: "penalty" },
  // f11 ENG 1-1 ESP
  { fixture_id: 11, team: "ENG", player_name: "Harry Kane", minute: 33, type: "regular" },
  { fixture_id: 11, team: "ESP", player_name: "Álvaro Morata", minute: 70, type: "regular" },
  // f12 USA 2-1 SEN
  { fixture_id: 12, team: "USA", player_name: "Christian Pulisic", minute: 25, type: "regular" },
  { fixture_id: 12, team: "USA", player_name: "Timothy Weah", minute: 55, type: "regular" },
  { fixture_id: 12, team: "SEN", player_name: "Sadio Mané", minute: 88, type: "regular" },
];

const GOALS: Goal[] = GOAL_SEEDS.map((g, i) => ({
  id: i + 1,
  fixture_id: g.fixture_id,
  team_id: team(g.team).id,
  player_name: g.player_name,
  minute: g.minute,
  type: g.type,
}));

// --- Per-match advanced stats (authored; ESPN-only in production) -----------

const MATCH_STATS: Record<number, MatchStats[]> = {
  1: [
    { team_id: team("BRA").id, possession: 58, shots: 14, shots_on_target: 6, corners: 7, fouls: 9, yellow_cards: 1, red_cards: 0 },
    { team_id: team("CRO").id, possession: 42, shots: 9, shots_on_target: 3, corners: 4, fouls: 12, yellow_cards: 2, red_cards: 0 },
  ],
  2: [
    { team_id: team("MEX").id, possession: 52, shots: 8, shots_on_target: 2, corners: 5, fouls: 10, yellow_cards: 1, red_cards: 0 },
    { team_id: team("JPN").id, possession: 48, shots: 7, shots_on_target: 3, corners: 4, fouls: 9, yellow_cards: 2, red_cards: 0 },
  ],
  3: [
    { team_id: team("BRA").id, possession: 61, shots: 11, shots_on_target: 4, corners: 5, fouls: 6, yellow_cards: 0, red_cards: 0 },
    { team_id: team("MEX").id, possession: 39, shots: 5, shots_on_target: 1, corners: 2, fouls: 8, yellow_cards: 1, red_cards: 0 },
  ],
  7: [
    { team_id: team("ARG").id, possession: 55, shots: 16, shots_on_target: 8, corners: 6, fouls: 10, yellow_cards: 1, red_cards: 0 },
    { team_id: team("KOR").id, possession: 45, shots: 10, shots_on_target: 4, corners: 3, fouls: 11, yellow_cards: 2, red_cards: 0 },
  ],
  8: [
    { team_id: team("FRA").id, possession: 56, shots: 15, shots_on_target: 7, corners: 8, fouls: 7, yellow_cards: 1, red_cards: 0 },
    { team_id: team("MAR").id, possession: 44, shots: 8, shots_on_target: 2, corners: 3, fouls: 12, yellow_cards: 3, red_cards: 0 },
  ],
  9: [
    { team_id: team("ARG").id, possession: 49, shots: 8, shots_on_target: 3, corners: 4, fouls: 7, yellow_cards: 1, red_cards: 0 },
    { team_id: team("FRA").id, possession: 51, shots: 9, shots_on_target: 4, corners: 5, fouls: 6, yellow_cards: 1, red_cards: 0 },
  ],
  11: [
    { team_id: team("ENG").id, possession: 47, shots: 11, shots_on_target: 4, corners: 5, fouls: 9, yellow_cards: 2, red_cards: 0 },
    { team_id: team("ESP").id, possession: 53, shots: 13, shots_on_target: 5, corners: 7, fouls: 8, yellow_cards: 1, red_cards: 0 },
  ],
  12: [
    { team_id: team("USA").id, possession: 50, shots: 12, shots_on_target: 5, corners: 6, fouls: 10, yellow_cards: 2, red_cards: 0 },
    { team_id: team("SEN").id, possession: 50, shots: 10, shots_on_target: 4, corners: 5, fouls: 11, yellow_cards: 2, red_cards: 1 },
  ],
};

// --- AI insights (cached in production; authored here) ----------------------

const INSIGHTS: Record<number, AIInsight> = {
  1: {
    content:
      "Brazil controlled the tempo and turned 58% possession into the decisive edge, with Rodrygo's 71st-minute strike restoring a two-goal cushion before Kramarić's late reply. Croatia's midfield created chances but couldn't match Brazil's clinical finishing.",
    state: "finished",
    model: "claude-haiku-4-5",
    prompt_version: "match_insight_v1",
  },
  3: {
    content:
      "Brazil enter as group leaders and have started on the front foot, with Raphinha's early goal reflecting their 61% possession. Mexico will need to find a foothold quickly to avoid a second straight game without a goal.",
    state: "scheduled",
    model: "claude-haiku-4-5",
    prompt_version: "match_insight_v1",
  },
  4: {
    content:
      "Croatia look to bounce back from their opening defeat against a Japan side that frustrated Mexico to a goalless draw. Expect a tight, low-block contest where the first goal carries outsized weight.",
    state: "scheduled",
    model: "claude-haiku-4-5",
    prompt_version: "match_insight_v1",
  },
  7: {
    content:
      "Argentina's front line proved too sharp for South Korea, with Messi converting early from the spot and Álvarez and Martínez adding to a comfortable margin. Son's strike was a bright spot in an otherwise one-sided contest.",
    state: "finished",
    model: "claude-haiku-4-5",
    prompt_version: "match_insight_v1",
  },
  9: {
    content:
      "Two opening-day winners meet with first place on the line, and the early exchange of goals from Álvarez and Mbappé reflects how evenly matched these sides are. Possession is split almost down the middle — a single moment of quality may decide it.",
    state: "scheduled",
    model: "claude-haiku-4-5",
    prompt_version: "match_insight_v1",
  },
};

// --- Player roster (scorers + goalkeepers) ----------------------------------
//
// Goals are DERIVED from GOALS below (so they stay consistent with the match
// timelines); position, assists and matches-played are authored since they
// can't be inferred from scores. Goalkeepers are included so the Player Stats
// table shows clean sheets — a stat the outfield scorers don't accrue.

type Position = "GK" | "DF" | "MF" | "FW";

interface PlayerSeed {
  name: string;
  team: string; // team code
  position: Position;
  assists: number;
  matches_played: number;
}

const PLAYER_SEEDS: PlayerSeed[] = [
  // Outfield scorers (goals derived from GOALS)
  { name: "Kylian Mbappé", team: "FRA", position: "FW", assists: 1, matches_played: 2 },
  { name: "Julián Álvarez", team: "ARG", position: "FW", assists: 0, matches_played: 2 },
  { name: "Lionel Messi", team: "ARG", position: "FW", assists: 2, matches_played: 1 },
  { name: "Lautaro Martínez", team: "ARG", position: "FW", assists: 1, matches_played: 1 },
  { name: "Vinícius Júnior", team: "BRA", position: "FW", assists: 1, matches_played: 2 },
  { name: "Rodrygo", team: "BRA", position: "FW", assists: 0, matches_played: 2 },
  { name: "Raphinha", team: "BRA", position: "FW", assists: 1, matches_played: 2 },
  { name: "Olivier Giroud", team: "FRA", position: "FW", assists: 0, matches_played: 1 },
  { name: "Harry Kane", team: "ENG", position: "FW", assists: 0, matches_played: 1 },
  { name: "Álvaro Morata", team: "ESP", position: "FW", assists: 0, matches_played: 1 },
  { name: "Christian Pulisic", team: "USA", position: "MF", assists: 1, matches_played: 1 },
  { name: "Timothy Weah", team: "USA", position: "FW", assists: 0, matches_played: 1 },
  { name: "Sadio Mané", team: "SEN", position: "FW", assists: 0, matches_played: 1 },
  { name: "Son Heung-min", team: "KOR", position: "FW", assists: 0, matches_played: 1 },
  { name: "Andrej Kramarić", team: "CRO", position: "FW", assists: 0, matches_played: 1 },
  // Goalkeepers (clean sheets derived from their team's finished results)
  { name: "Alisson", team: "BRA", position: "GK", assists: 0, matches_played: 2 },
  { name: "Dominik Livaković", team: "CRO", position: "GK", assists: 0, matches_played: 1 },
  { name: "Guillermo Ochoa", team: "MEX", position: "GK", assists: 0, matches_played: 2 },
  { name: "Zion Suzuki", team: "JPN", position: "GK", assists: 0, matches_played: 1 },
  { name: "Emiliano Martínez", team: "ARG", position: "GK", assists: 0, matches_played: 2 },
  { name: "Kim Seung-gyu", team: "KOR", position: "GK", assists: 0, matches_played: 1 },
  { name: "Mike Maignan", team: "FRA", position: "GK", assists: 0, matches_played: 2 },
  { name: "Yassine Bounou", team: "MAR", position: "GK", assists: 0, matches_played: 1 },
  { name: "Jordan Pickford", team: "ENG", position: "GK", assists: 0, matches_played: 1 },
  { name: "Unai Simón", team: "ESP", position: "GK", assists: 0, matches_played: 1 },
  { name: "Matt Turner", team: "USA", position: "GK", assists: 0, matches_played: 1 },
  { name: "Édouard Mendy", team: "SEN", position: "GK", assists: 0, matches_played: 1 },
];

// --- Derivations (the aggregator the backend will own) ----------------------

function emptyStanding(t: TeamRef): Standing {
  return {
    team: t,
    group_label: t.group_label,
    played: 0,
    won: 0,
    drawn: 0,
    lost: 0,
    goals_for: 0,
    goals_against: 0,
    goal_diff: 0,
    points: 0,
    form: [],
  };
}

const byKickoff = (a: Fixture, b: Fixture) =>
  a.kickoff_at.localeCompare(b.kickoff_at);

function computeStandings(): Standing[] {
  const rows = new Map<number, Standing>();
  for (const t of TEAMS) rows.set(t.id, emptyStanding(t));

  for (const f of FIXTURES.filter((x) => x.status === "finished").sort(byKickoff)) {
    const home = rows.get(f.home_team.id)!;
    const away = rows.get(f.away_team.id)!;
    const hs = f.home_score ?? 0;
    const as = f.away_score ?? 0;

    home.played++;
    away.played++;
    home.goals_for += hs;
    home.goals_against += as;
    away.goals_for += as;
    away.goals_against += hs;

    if (hs > as) {
      home.won++;
      home.points += 3;
      home.form.push("W");
      away.lost++;
      away.form.push("L");
    } else if (hs < as) {
      away.won++;
      away.points += 3;
      away.form.push("W");
      home.lost++;
      home.form.push("L");
    } else {
      home.drawn++;
      away.drawn++;
      home.points += 1;
      away.points += 1;
      home.form.push("D");
      away.form.push("D");
    }
  }

  for (const r of rows.values()) {
    r.goal_diff = r.goals_for - r.goals_against;
    r.form = r.form.slice(-5);
  }
  return [...rows.values()];
}

const ALL_STANDINGS = computeStandings();

// Count a team's clean sheets across its finished fixtures (conceded 0).
function teamCleanSheetCount(teamId: number): number {
  let count = 0;
  for (const f of FIXTURES) {
    if (f.status !== "finished") continue;
    const isHome = f.home_team.id === teamId;
    const isAway = f.away_team.id === teamId;
    if (!isHome && !isAway) continue;
    const conceded = (isHome ? f.away_score : f.home_score) ?? 0;
    if (conceded === 0) count++;
  }
  return count;
}

function computePlayers(): ScorerStat[] {
  const goalsByPlayer = new Map<string, number>();
  for (const g of GOALS) {
    if (g.type === "own_goal") continue;
    goalsByPlayer.set(g.player_name, (goalsByPlayer.get(g.player_name) ?? 0) + 1);
  }

  const rows = PLAYER_SEEDS.map((p) => {
    const t = team(p.team);
    const isKeeper = p.position === "GK";
    return {
      player_name: p.name,
      team_name: t.name,
      team_code: t.code,
      position: p.position,
      goals: goalsByPlayer.get(p.name) ?? 0,
      assists: p.assists,
      // Clean sheets are a goalkeeper-only stat; outfield players get null → "—".
      clean_sheets: isKeeper ? teamCleanSheetCount(t.id) : null,
      matches_played: p.matches_played,
    };
  });

  return sortScorers(rows, "goals").map((r, i) => ({ rank: i + 1, ...r }));
}

const ALL_SCORERS = computePlayers();

// Aggregate a team's totals from its finished fixtures. Goals/clean-sheets come
// from the scores; the advanced stats (possession, shots, cards…) are summed
// from that team's per-match `match_stats` rows — never a hand-authored table.
// This mirrors the backend aggregator (CLAUDE.md §5.3 step 5), so once real
// match stats land for every fixture, every team is populated automatically —
// no team is left with blank advanced stats. A field stays null (renders "—")
// only when genuinely no match-stat row exists for that team.
function teamAggregate(t: TeamRef): TeamAggregate {
  const finished = FIXTURES.filter(
    (f) =>
      f.status === "finished" &&
      (f.home_team.id === t.id || f.away_team.id === t.id),
  );

  let gf = 0;
  let ga = 0;
  let cleanSheets = 0;

  let possessionSum = 0;
  let possessionCount = 0;
  let shots = 0;
  let shotsOnTarget = 0;
  let corners = 0;
  let yellowCards = 0;
  let redCards = 0;
  let hasMatchStats = false;

  for (const f of finished) {
    const isHome = f.home_team.id === t.id;
    const scored = (isHome ? f.home_score : f.away_score) ?? 0;
    const conceded = (isHome ? f.away_score : f.home_score) ?? 0;
    gf += scored;
    ga += conceded;
    if (conceded === 0) cleanSheets++;

    const row = (MATCH_STATS[f.id] ?? []).find((s) => s.team_id === t.id);
    if (row) {
      hasMatchStats = true;
      if (row.possession != null) {
        possessionSum += row.possession;
        possessionCount++;
      }
      shots += row.shots ?? 0;
      shotsOnTarget += row.shots_on_target ?? 0;
      corners += row.corners ?? 0;
      yellowCards += row.yellow_cards ?? 0;
      redCards += row.red_cards ?? 0;
    }
  }

  return {
    matches_played: finished.length,
    goals_for: gf,
    goals_against: ga,
    goal_diff: gf - ga,
    clean_sheets: cleanSheets,
    possession_avg: possessionCount
      ? Math.round((possessionSum / possessionCount) * 10) / 10
      : null,
    shots: hasMatchStats ? shots : null,
    shots_on_target: hasMatchStats ? shotsOnTarget : null,
    corners: hasMatchStats ? corners : null,
    yellow_cards: hasMatchStats ? yellowCards : null,
    red_cards: hasMatchStats ? redCards : null,
  };
}

function teamForm(t: TeamRef): FormResult[] {
  return ALL_STANDINGS.find((s) => s.team.id === t.id)?.form ?? [];
}

// --- Public mock API (mirrors api.ts signatures) ----------------------------

const now = () => new Date().toISOString();

export function getFixtures(params?: {
  date?: string;
  status?: Fixture["status"];
}): FixturesResponse {
  let fixtures = [...FIXTURES];
  if (params?.date) fixtures = fixtures.filter((f) => dayKey(f.kickoff_at) === params.date);
  if (params?.status) fixtures = fixtures.filter((f) => f.status === params.status);
  fixtures.sort(byKickoff);
  return { fixtures, generated_at: now() };
}

export function getFixture(id: number): FixtureDetailResponse | null {
  const fixture = fixtureById(id);
  if (!fixture) return null;
  return {
    fixture,
    stats: MATCH_STATS[id] ?? [],
    goals: GOALS.filter((g) => g.fixture_id === id).sort((a, b) => a.minute - b.minute),
    lineups: null, // ESPN lineups deferred (BACKLOG-002)
    insight: INSIGHTS[id] ?? null,
  };
}

export function getGroups(): string[] {
  return [...new Set(TEAMS.map((t) => t.group_label))].sort();
}

export function getStandings(group?: string): StandingsResponse {
  const target = group ?? getGroups()[0];
  const rows = sortByFifaTiebreaker(
    ALL_STANDINGS.filter((s) => s.group_label === target),
  );
  return { standings: rows, group: target, updated_at: now() };
}

export function getScorers(
  sort: "goals" | "assists" = "goals",
  limit = 50,
): ScorersResponse {
  return {
    scorers: sortScorers(ALL_SCORERS, sort).slice(0, limit),
    updated_at: now(),
  };
}

export function getTeam(id: number): TeamResponse | null {
  const t = TEAMS.find((x) => x.id === id);
  if (!t) return null;
  return { team: t, stats: teamAggregate(t), form: teamForm(t) };
}

export { TEAMS, FIXTURES };
