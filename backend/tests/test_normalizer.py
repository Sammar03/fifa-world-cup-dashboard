"""Unit tests for ESPN normalization (CLAUDE.md §13). Sample payloads mirror
the live responses captured on 2026-06-12 — including the status id "28" /
STATUS_FULL_TIME deviation from the documented "3" / STATUS_FINAL."""

from app.ingestion.normalizer import (
    map_status,
    normalize_event,
    normalize_position,
    normalize_summary,
    parse_assister,
    parse_minute,
    parse_score,
)
from app.ingestion.schemas.espn import EspnEvent, EspnStatus, EspnSummary


def _sample_event() -> EspnEvent:
    return EspnEvent.model_validate(
        {
            "id": "760415",
            "date": "2026-06-11T19:00Z",
            "name": "South Africa at Mexico",
            "status": {
                "displayClock": "90'+8'",
                "period": 2,
                "type": {"id": "28", "name": "STATUS_FULL_TIME", "state": "post", "completed": True},
            },
            "competitions": [
                {
                    "venue": {"fullName": "Estadio Banorte", "address": {"city": "Mexico City"}},
                    "competitors": [
                        {
                            "id": "203",
                            "homeAway": "home",
                            "score": "2",
                            "team": {
                                "displayName": "Mexico",
                                "abbreviation": "MEX",
                                "logo": "https://a.espncdn.com/i/teamlogos/countries/500/mex.png",
                            },
                        },
                        {
                            "id": "467",
                            "homeAway": "away",
                            "score": "0",
                            "team": {"displayName": "South Africa", "abbreviation": "RSA"},
                        },
                    ],
                    "details": [
                        {
                            "clock": {"displayValue": "9'"},
                            "team": {"id": "203"},
                            "scoringPlay": True,
                            "penaltyKick": False,
                            "ownGoal": False,
                            "shootout": False,
                            "athletesInvolved": [{"id": "233075", "displayName": "Julián Quiñones"}],
                        },
                        {  # a yellow card — must NOT become a goal
                            "clock": {"displayValue": "17'"},
                            "team": {"id": "467"},
                            "scoringPlay": False,
                            "yellowCard": True,
                        },
                    ],
                }
            ],
        }
    )


def test_ingest_normalizes_espn_response():
    fixture = normalize_event(_sample_event())

    assert fixture.external_id == "760415"
    assert fixture.status == "finished"  # via state "post", not the documented id table
    assert fixture.kickoff_at is not None and fixture.kickoff_at.hour == 19
    assert fixture.venue == "Estadio Banorte"
    assert fixture.home is not None and fixture.home.code == "MEX"
    assert fixture.home.score == 2  # "2" string → int
    assert fixture.away is not None and fixture.away.score == 0
    assert fixture.minute is None  # only live fixtures expose the clock
    assert len(fixture.goals) == 1  # the card was filtered out
    goal = fixture.goals[0]
    assert goal.player_name == "Julián Quiñones"
    assert goal.minute == 9
    assert goal.type == "regular"


def test_ingest_handles_missing_fields():
    # Bare-minimum event: only the id. Everything degrades, nothing raises.
    fixture = normalize_event(EspnEvent.model_validate({"id": "x1"}))
    assert fixture.status == "scheduled"
    assert fixture.home is None and fixture.away is None
    assert fixture.goals == []

    # Unknown status id and state → WARNING + scheduled (api-research §2)
    unknown = EspnStatus.model_validate({"type": {"id": "99", "name": "STATUS_MYSTERY"}})
    assert map_status(unknown) == "scheduled"
    assert map_status(None) == "scheduled"

    # Defensive parsers
    assert parse_score(None) is None
    assert parse_score("") is None
    assert parse_score("not-a-number") is None
    assert parse_minute("45'") == 45
    assert parse_minute("90'+8'") == 90
    assert parse_minute("HT") is None
    assert parse_minute(None) is None

    # Empty summary → no stats, no lineups, no exception
    summary = normalize_summary(EspnSummary.model_validate({}))
    assert summary.stats == {} and summary.lineups == []


def test_scheduled_fixture_scores_are_null():
    event = _sample_event()
    event.status.type.state = "pre"
    event.status.type.id = "1"
    fixture = normalize_event(event)
    assert fixture.status == "scheduled"
    # ESPN reports "0"/"2" pre-kickoff; the contract requires null until live.
    assert fixture.home.score is None and fixture.away.score is None


def test_position_normalization():
    assert normalize_position("G") == "GK"
    assert normalize_position("CD-L") == "DF"
    assert normalize_position("CM-R") == "MF"
    assert normalize_position("ST") == "FW"
    assert normalize_position("LM") == "MF"
    assert normalize_position(None) is None


def test_parse_assister_from_keyevent_text():
    # Real ESPN goal texts (captured live 2026-06-13).
    assert (
        parse_assister(
            "Goal! Mexico 1, South Africa 0. Julián Quiñones (Mexico) right footed "
            "shot from the centre of the box. Assisted by Érik Lira."
        )
        == "Érik Lira"
    )
    # Trailing clause ("with a cross") must be trimmed off the name.
    assert (
        parse_assister(
            "Goal! Mexico 2, South Africa 0. Raúl Jiménez (Mexico) header. "
            "Assisted by Roberto Alvarado with a cross."
        )
        == "Roberto Alvarado"
    )
    assert (
        parse_assister("Goal! Korea 2. Oh Hyeon-Gyu. Assisted by Hwang In-Beom.")
        == "Hwang In-Beom"
    )
    # An unassisted goal (penalty / solo) yields no assister.
    assert parse_assister("Goal! Penalty. Player X scores from the spot.") is None
    assert parse_assister(None) is None


def test_normalize_summary_extracts_assists():
    summary = EspnSummary.model_validate(
        {
            "keyEvents": [
                {
                    "scoringPlay": True,
                    "clock": {"displayValue": "9'"},
                    "text": "Goal! Julián Quiñones. Assisted by Érik Lira.",
                },
                {  # a non-scoring play with 'assist' wording must be ignored
                    "scoringPlay": False,
                    "clock": {"displayValue": "17'"},
                    "text": "Attempt saved. Assisted by Someone Else.",
                },
                {  # a goal with no assist
                    "scoringPlay": True,
                    "clock": {"displayValue": "67'"},
                    "text": "Goal! A penalty converted.",
                },
            ]
        }
    )
    result = normalize_summary(summary)
    assert len(result.assists) == 1
    assert result.assists[0].minute == 9
    assert result.assists[0].assister_name == "Érik Lira"


def test_summary_stats_mapping():
    summary = EspnSummary.model_validate(
        {
            "boxscore": {
                "teams": [
                    {
                        "team": {"id": "203"},
                        "statistics": [
                            {"name": "possessionPct", "displayValue": "60.5"},
                            {"name": "totalShots", "displayValue": "16"},
                            {"name": "wonCorners", "displayValue": "3"},
                            {"name": "unknownStat", "displayValue": "7"},
                        ],
                    }
                ]
            },
            "rosters": [
                {
                    "team": {"id": "203"},
                    "formation": "4-1-4-1",
                    "roster": [
                        {
                            "starter": True,
                            "jersey": "1",
                            "position": {"abbreviation": "G"},
                            "athlete": {"id": "9", "displayName": "Raúl Rangel"},
                        }
                    ],
                }
            ],
        }
    )
    normalized = normalize_summary(summary)
    assert normalized.stats["203"]["possession"] == 60.5
    assert normalized.stats["203"]["shots"] == 16
    assert normalized.stats["203"]["corners"] == 3
    assert "unknownStat" not in normalized.stats["203"]
    assert normalized.lineups[0].formation == "4-1-4-1"
    assert normalized.lineups[0].players[0].position == "GK"
    assert normalized.lineups[0].players[0].number == 1
