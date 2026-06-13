"""Unit tests for the standings computation core (CLAUDE.md §13, ADR-003).
Pure functions — no DB."""

from app.ingestion.aggregator import (
    FixtureResult,
    StandingTotals,
    _lookup_by_name,
    _token_key,
    compute_standings,
    form_from_results,
    sort_group,
)


def test_standings_computed_correctly():
    # Group: 1 beats 2 (3-1), 2 draws 3 (2-2)
    results = [
        FixtureResult(home_team_id=1, away_team_id=2, home_score=3, away_score=1),
        FixtureResult(home_team_id=2, away_team_id=3, home_score=2, away_score=2),
    ]
    groups = {1: "A", 2: "A", 3: "A"}
    rows = {row.team_id: row for row in compute_standings(results, groups)}

    assert rows[1].played == 1 and rows[1].won == 1 and rows[1].points == 3
    assert rows[1].goals_for == 3 and rows[1].goals_against == 1 and rows[1].goal_diff == 2
    assert rows[2].played == 2 and rows[2].won == 0 and rows[2].drawn == 1 and rows[2].lost == 1
    assert rows[2].points == 1
    assert rows[3].played == 1 and rows[3].drawn == 1 and rows[3].points == 1
    assert rows[3].goal_diff == 0


def test_standings_only_count_listed_teams():
    # A fixture against a team outside the group map must not crash or count.
    results = [FixtureResult(home_team_id=1, away_team_id=99, home_score=1, away_score=0)]
    rows = {row.team_id: row for row in compute_standings(results, {1: "A"})}
    assert rows[1].won == 1
    assert 99 not in rows


def test_fifa_tiebreaker_ordering():
    """points DESC → goal_diff DESC → goals_for DESC → name ASC (FIFA 2026)."""

    def totals(team_id, name, points, gf, ga):
        row = StandingTotals(team_id=team_id, group_label="A", team_name=name)
        row.points, row.goals_for, row.goals_against = points, gf, ga
        return row

    rows = [
        totals(1, "Senegal", 6, 4, 2),   # same pts as Japan, lower GD
        totals(2, "Japan", 6, 5, 1),     # GD +4 → first
        totals(3, "Brazil", 4, 6, 3),    # same as Austria on pts/GD/GF → name ASC
        totals(4, "Austria", 4, 6, 3),
        totals(5, "Ghana", 4, 3, 0),     # same pts/GD as 3&4, fewer GF → after them
    ]
    ordered = [row.team_name for row in sort_group(rows)]
    assert ordered == ["Japan", "Senegal", "Austria", "Brazil", "Ghana"]


def test_form_keeps_last_five_oldest_to_newest():
    assert form_from_results(["W", "W", "D", "L", "W", "D", "L"]) == ["D", "L", "W", "D", "L"]
    assert form_from_results(["W"]) == ["W"]
    assert form_from_results([]) == []


def test_name_matching_is_order_independent():
    # football-data "In-beom Hwang" vs ESPN lineup "Hwang In-Beom" must match.
    assert _token_key("In-beom Hwang") == _token_key("Hwang In-Beom")
    positions_exact = {"hwang in-beom": "MF"}
    positions_token = {_token_key("Hwang In-Beom"): "MF"}

    # Exact order still works
    assert _lookup_by_name(positions_exact, positions_token, "Hwang In-Beom") == "MF"
    # Reversed order resolves via the token key
    assert _lookup_by_name(positions_exact, positions_token, "In-beom Hwang") == "MF"
    # Genuinely unknown name returns None
    assert _lookup_by_name(positions_exact, positions_token, "Lionel Messi") is None
