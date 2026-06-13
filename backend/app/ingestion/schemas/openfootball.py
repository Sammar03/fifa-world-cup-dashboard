"""Pydantic boundary models for openfootball/worldcup.json (api-research.md §4).

Shape verified live on 2026-06-12 — it differs from older editions:
top level is { name, matches } (no `rounds` array), `team1`/`team2` are plain
name strings (no 3-letter codes — codes come from ESPN instead), knockout
matches use placeholder tokens ("W101", "1A", "3A/B/C/D/F"), and `time` is
local with a UTC offset, e.g. "13:00 UTC-6". Validation failures here must
fail loudly — that is the seed contract.
"""

from pydantic import BaseModel, ConfigDict


class OFScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ft: list[int] | None = None  # [home, away] full time
    ht: list[int] | None = None


class OFGoal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    minute: str | None = None


class OFMatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    round: str  # "Matchday 1" … "Round of 32" … "Final"
    date: str  # "2026-06-11"
    time: str | None = None  # "13:00 UTC-6"
    team1: str  # name or placeholder token ("W101", "1A")
    team2: str
    group: str | None = None  # "Group A" … "Group L"; absent for knockouts
    ground: str | None = None  # city / venue hint
    num: int | None = None
    score: OFScore | None = None
    goals1: list[OFGoal] = []
    goals2: list[OFGoal] = []


class OFWorldCup(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    matches: list[OFMatch]
