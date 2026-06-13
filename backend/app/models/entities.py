"""SQLAlchemy ORM models — implements CLAUDE.md §5.2 exactly, plus the
documented extensions from docs/api-research.md and the frontend contract:

- fixtures.verified / verified_at / mismatch_count  (api-research §6.2, §9)
- fixtures.minute                                   (frontend Fixture.minute — live clock)
- scorer_stats.position / clean_sheets              (frontend ScorerStat; owner decision 2026-06-12)
- external_id_map                                   (api-research §5)
- lineups                                           (serves FixtureDetailResponse.lineups;
                                                     source for GK identity / clean sheets)
- ingestion_runs                                    (observability: /health + POST /ingest response)

Any further schema change requires an Alembic migration AND a CLAUDE.md §5.2 update.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str | None] = mapped_column(Text)
    group_label: Mapped[str | None] = mapped_column(Text)
    flag_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    position: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Fixture(Base):
    __tablename__ = "fixtures"
    __table_args__ = (
        Index("idx_fixtures_status", "status"),
        Index("idx_fixtures_kickoff", "kickoff_at"),
        Index("idx_fixtures_home_team", "home_team_id"),
        Index("idx_fixtures_away_team", "away_team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    venue: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)  # scheduled | live | finished
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    group_label: Mapped[str | None] = mapped_column(Text)
    round: Mapped[str | None] = mapped_column(Text)
    # Live display clock in minutes; null when not live (frontend Fixture.minute).
    minute: Mapped[int | None] = mapped_column(Integer)
    # Two-source reconciliation result (api-research §6.2). text("false") renders
    # an unquoted boolean literal on both Postgres and SQLite ('false' would be
    # a truthy string on SQLite).
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Consecutive runs with a score mismatch; CRITICAL log after threshold (api-research §9).
    mismatch_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # When the ESPN /summary (stats, lineups, assists) was last applied. Reset to
    # NULL on any status change so each state gets one fresh summary sync; gates
    # which finished fixtures still need a summary fetch (scheduler cap = 5/run).
    summary_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MatchStat(Base):
    __tablename__ = "match_stats"
    __table_args__ = (
        UniqueConstraint("fixture_id", "team_id"),
        Index("idx_match_stats_fixture", "fixture_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    possession: Mapped[float | None] = mapped_column(Numeric(5, 2))
    shots: Mapped[int | None] = mapped_column(Integer)
    shots_on_target: Mapped[int | None] = mapped_column(Integer)
    corners: Mapped[int | None] = mapped_column(Integer)
    fouls: Mapped[int | None] = mapped_column(Integer)
    yellow_cards: Mapped[int | None] = mapped_column(Integer)
    red_cards: Mapped[int | None] = mapped_column(Integer)


class Goal(Base):
    __tablename__ = "goals"
    # Dedup guard (BACKLOG DEBT-003): one row per scorer-minute-type per fixture.
    __table_args__ = (UniqueConstraint("fixture_id", "player_name", "minute", "type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"))
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"))
    # Denormalized: ESPN's goal timeline gives a display name, not a stable player
    # id we can always resolve. The frontend Goal shape needs player_name directly.
    player_name: Mapped[str | None] = mapped_column(Text)
    # Assist provider, parsed from ESPN keyEvents prose (the only source that
    # exposes assists — football-data free tier returns null for most goals).
    assist_player_name: Mapped[str | None] = mapped_column(Text)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    minute: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[str | None] = mapped_column(Text)  # regular | own_goal | penalty


class LineupEntry(Base):
    __tablename__ = "lineups"
    __table_args__ = (UniqueConstraint("fixture_id", "team_id", "player_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    player_name: Mapped[str] = mapped_column(Text, nullable=False)
    number: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(Text)  # GK | DF | MF | FW (ESPN abbreviation)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    formation: Mapped[str | None] = mapped_column(Text)  # per team; repeated per row for MVP


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (Index("idx_standings_group", "group_label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), unique=True)
    group_label: Mapped[str] = mapped_column(Text, nullable=False)
    played: Mapped[int] = mapped_column(Integer, server_default="0")
    won: Mapped[int] = mapped_column(Integer, server_default="0")
    drawn: Mapped[int] = mapped_column(Integer, server_default="0")
    lost: Mapped[int] = mapped_column(Integer, server_default="0")
    goals_for: Mapped[int] = mapped_column(Integer, server_default="0")
    goals_against: Mapped[int] = mapped_column(Integer, server_default="0")
    goal_diff: Mapped[int] = mapped_column(Integer, Computed("goals_for - goals_against"))
    points: Mapped[int] = mapped_column(Integer, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScorerStat(Base):
    __tablename__ = "scorer_stats"
    __table_args__ = (Index("idx_scorer_stats_goals", text("goals DESC")),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), unique=True)
    goals: Mapped[int] = mapped_column(Integer, server_default="0")
    assists: Mapped[int] = mapped_column(Integer, server_default="0")
    matches_played: Mapped[int] = mapped_column(Integer, server_default="0")
    # Derived from ESPN lineup data when present; null → frontend shows "—"
    # (owner decision 2026-06-12; frontend ScorerStat.position / clean_sheets).
    position: Mapped[str | None] = mapped_column(Text)
    clean_sheets: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIInsight(Base):
    __tablename__ = "ai_insights"
    __table_args__ = (
        UniqueConstraint("fixture_id", "state"),
        Index("idx_ai_insights_fixture", "fixture_id", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"))
    state: Mapped[str] = mapped_column(Text, nullable=False)  # scheduled | finished
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExternalIdMap(Base):
    __tablename__ = "external_id_map"
    __table_args__ = (UniqueConstraint("entity_type", "source", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)  # 'team' | 'fixture'
    source: Mapped[str] = mapped_column(Text, nullable=False)  # 'espn' | 'football_data' | 'openfootball'
    external_id: Mapped[str] = mapped_column(Text, nullable=False)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="running")  # running | ok | error
    fixtures_updated: Mapped[int] = mapped_column(Integer, server_default="0")
    insights_generated: Mapped[int] = mapped_column(Integer, server_default="0")
    reconciliation_flags: Mapped[int] = mapped_column(Integer, server_default="0")
    error: Mapped[str | None] = mapped_column(Text)
