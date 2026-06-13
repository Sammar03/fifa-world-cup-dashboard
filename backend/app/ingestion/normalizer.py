"""Maps ESPN shapes to the internal schema (CLAUDE.md §5.3 step 3).

Pure functions only — no I/O, no DB. Every field access is guarded; a missing
field degrades to None, never an exception (api-research.md §2 gotchas).

Status mapping: live verification (2026-06-12) showed finished matches report
status.type.id "28" / STATUS_FULL_TIME, NOT the documented "3" / STATUS_FINAL.
The robust signal is status.type.state ("pre" | "in" | "post"), used first;
the documented ids remain as a fallback. Unknown statuses log a WARNING and
default to "scheduled" — never crash (api-research.md §2).
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.ingestion.schemas.espn import EspnEvent, EspnStatus, EspnSummary

# "Assisted by <Name>" in ESPN keyEvent prose. The name runs until a clause
# break ("with a cross", "following a corner") or sentence punctuation.
_ASSIST_RE = re.compile(r"Assisted by ([^.,;]+?)(?:\s+with\b|\s+following\b|[.,;]|$)")

logger = logging.getLogger(__name__)

_STATUS_BY_STATE = {"pre": "scheduled", "in": "live", "post": "finished"}
_STATUS_BY_ID = {"1": "scheduled", "2": "live", "3": "finished"}

# ESPN boxscore statistic name → match_stats column (names verified live).
_STAT_NAME_MAP = {
    "possessionPct": "possession",
    "totalShots": "shots",
    "shotsOnTarget": "shots_on_target",
    "wonCorners": "corners",
    "foulsCommitted": "fouls",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
}


@dataclass
class NormalizedTeam:
    external_id: str
    name: str
    code: str | None
    flag_url: str | None
    score: int | None


@dataclass
class NormalizedGoal:
    team_external_id: str | None
    player_external_id: str | None
    player_name: str | None
    minute: int | None
    type: str  # regular | own_goal | penalty


@dataclass
class NormalizedFixture:
    external_id: str
    kickoff_at: datetime | None
    venue: str | None
    status: str
    minute: int | None
    home: NormalizedTeam | None
    away: NormalizedTeam | None
    goals: list[NormalizedGoal] = field(default_factory=list)


@dataclass
class NormalizedLineupPlayer:
    player_external_id: str | None
    player_name: str
    number: int | None
    position: str | None  # GK | DF | MF | FW
    is_starter: bool


@dataclass
class NormalizedLineup:
    team_external_id: str
    formation: str | None
    players: list[NormalizedLineupPlayer] = field(default_factory=list)


@dataclass
class NormalizedAssist:
    minute: int | None
    assister_name: str


@dataclass
class NormalizedSummary:
    # team_external_id → {column: value}
    stats: dict[str, dict[str, float | int | None]] = field(default_factory=dict)
    lineups: list[NormalizedLineup] = field(default_factory=list)
    # Assist credits parsed from goal keyEvents, keyed back to goals by minute.
    assists: list[NormalizedAssist] = field(default_factory=list)


def map_status(status: EspnStatus | None) -> str:
    if status is not None and status.type is not None:
        state = status.type.state
        if state in _STATUS_BY_STATE:
            return _STATUS_BY_STATE[state]
        type_id = status.type.id
        if type_id in _STATUS_BY_ID:
            return _STATUS_BY_ID[type_id]
        if status.type.completed is True:
            return "finished"
        logger.warning(
            "unknown_espn_status id=%s name=%s state=%s — defaulting to scheduled",
            status.type.id,
            status.type.name,
            status.type.state,
        )
    return "scheduled"


def parse_score(score: str | None) -> int | None:
    """ESPN scores are strings ("2"). Empty/missing → None (api-research §2)."""
    if score is None or score == "":
        return None
    try:
        return int(score)
    except ValueError:
        logger.warning("unparseable_espn_score value=%r", score)
        return None


def parse_minute(display_clock: str | None) -> int | None:
    """"45'" → 45, "90'+8'" → 90. None/garbage → None."""
    if not display_clock:
        return None
    digits = ""
    for char in display_clock:
        if char.isdigit():
            digits += char
        else:
            break
    return int(digits) if digits else None


def parse_kickoff(date: str | None) -> datetime | None:
    """ESPN dates look like "2026-06-11T19:00Z" — normalise to aware UTC."""
    if not date:
        return None
    try:
        return datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        logger.warning("unparseable_espn_date value=%r", date)
        return None


def normalize_position(raw: str | None) -> str | None:
    """ESPN roster abbreviations ("G", "CD-L", "CM-R", "ST"…) → GK|DF|MF|FW."""
    if not raw:
        return None
    head = raw.split("-")[0].upper()
    if head.startswith("G"):
        return "GK"
    if head[0] in ("D",) or head in ("LB", "RB", "CB", "WB", "CD", "SW"):
        return "DF"
    if "M" in head:  # CM, DM, AM, LM, RM, M
        return "MF"
    if head[0] in ("F", "S", "W") or head in ("CF", "ST", "LW", "RW"):
        return "FW"
    return None


def _goal_type(penalty: bool | None, own_goal: bool | None) -> str:
    if own_goal:
        return "own_goal"
    if penalty:
        return "penalty"
    return "regular"


def normalize_event(event: EspnEvent) -> NormalizedFixture:
    """Scoreboard event → internal fixture + goal timeline."""
    competition = event.competitions[0] if event.competitions else None

    home: NormalizedTeam | None = None
    away: NormalizedTeam | None = None
    venue: str | None = None
    goals: list[NormalizedGoal] = []

    if competition is not None:
        if competition.venue is not None:
            venue = competition.venue.fullName
        for competitor in competition.competitors:
            if competitor.id is None or competitor.team is None:
                continue
            team = NormalizedTeam(
                external_id=competitor.id,
                name=competitor.team.displayName or competitor.id,
                code=competitor.team.abbreviation,
                flag_url=competitor.team.logo,
                score=parse_score(competitor.score),
            )
            if competitor.homeAway == "home":
                home = team
            elif competitor.homeAway == "away":
                away = team

        for detail in competition.details:
            if not detail.scoringPlay or detail.shootout:
                continue
            athlete = detail.athletesInvolved[0] if detail.athletesInvolved else None
            goals.append(
                NormalizedGoal(
                    team_external_id=detail.team.id if detail.team else None,
                    player_external_id=athlete.id if athlete else None,
                    player_name=athlete.displayName if athlete else None,
                    minute=parse_minute(detail.clock.displayValue if detail.clock else None),
                    type=_goal_type(detail.penaltyKick, detail.ownGoal),
                )
            )

    status = map_status(event.status)
    # ESPN reports "0" for matches that haven't kicked off; the contract
    # (frontend Fixture.home_score) is null until the match starts.
    if status == "scheduled":
        if home is not None:
            home.score = None
        if away is not None:
            away.score = None
    return NormalizedFixture(
        external_id=event.id,
        kickoff_at=parse_kickoff(event.date),
        venue=venue,
        status=status,
        minute=parse_minute(event.status.displayClock if event.status else None)
        if status == "live"
        else None,
        home=home,
        away=away,
        goals=goals,
    )


def _parse_stat_value(name: str, display_value: str | None) -> float | int | None:
    if display_value is None or display_value == "":
        return None
    try:
        if name == "possession":
            return float(display_value)
        return int(float(display_value))
    except ValueError:
        return None


def normalize_summary(summary: EspnSummary) -> NormalizedSummary:
    """Summary → per-team stats + lineups. All sections may be absent pre-match."""
    result = NormalizedSummary()

    if summary.boxscore is not None:
        for boxscore_team in summary.boxscore.teams:
            if boxscore_team.team is None or boxscore_team.team.id is None:
                continue
            stats: dict[str, float | int | None] = {}
            for statistic in boxscore_team.statistics:
                column = _STAT_NAME_MAP.get(statistic.name or "")
                if column:
                    stats[column] = _parse_stat_value(column, statistic.displayValue)
            if stats:
                result.stats[boxscore_team.team.id] = stats

    for roster in summary.rosters:
        if roster.team is None or roster.team.id is None:
            continue
        players = []
        for entry in roster.roster:
            if entry.athlete is None or not entry.athlete.displayName:
                continue
            number: int | None = None
            if entry.jersey:
                try:
                    number = int(entry.jersey)
                except ValueError:
                    number = None
            players.append(
                NormalizedLineupPlayer(
                    player_external_id=entry.athlete.id,
                    player_name=entry.athlete.displayName,
                    number=number,
                    position=normalize_position(
                        entry.position.abbreviation if entry.position else None
                    ),
                    is_starter=bool(entry.starter),
                )
            )
        if players:
            result.lineups.append(
                NormalizedLineup(
                    team_external_id=roster.team.id,
                    formation=roster.formation,
                    players=players,
                )
            )

    for event in summary.keyEvents:
        if not event.scoringPlay or not event.text:
            continue
        assister = parse_assister(event.text)
        if assister:
            result.assists.append(
                NormalizedAssist(
                    minute=parse_minute(event.clock.displayValue if event.clock else None),
                    assister_name=assister,
                )
            )

    return result


def parse_assister(text: str | None) -> str | None:
    """Extract the assist provider from an ESPN goal keyEvent text.
    "…Assisted by Roberto Alvarado with a cross." → "Roberto Alvarado"."""
    if not text:
        return None
    match = _ASSIST_RE.search(text)
    return match.group(1).strip() if match else None
