"""Database models and operations for LLM2Deck"""

import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

Base = declarative_base()


class DatabaseManager:
    """
    Manages database connections and session lifecycle.

    Supports both singleton access (for backward compatibility) and
    dependency injection (for testing and multi-database scenarios).
    """

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the database manager.

        Args:
            db_path: Path to SQLite database. If None, must call initialize() later.
        """
        self._engine = None
        self._session_factory = None
        self._db_path: Optional[Path] = None

        if db_path is not None:
            self.initialize(db_path)

    def initialize(self, db_path: Path) -> None:
        """
        Initialize database engine and create tables.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = Path(db_path)
        logger.info(f"Initializing database at {self._db_path}")

        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        Base.metadata.create_all(bind=self._engine)

        self._session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine
        )

        logger.info("Database initialized successfully")

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._session_factory is not None

    @property
    def db_path(self) -> Optional[Path]:
        """Get the database path."""
        return self._db_path

    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory()

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @classmethod
    def get_default(cls) -> "DatabaseManager":
        """Get or create the default singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_default(cls, manager: "DatabaseManager") -> None:
        """
        Set the default singleton instance.

        Useful for testing with in-memory databases or custom configurations.

        Args:
            manager: The DatabaseManager instance to use as default.
        """
        cls._instance = manager

    @classmethod
    def reset_default(cls) -> None:
        """Reset the default singleton (useful for testing cleanup)."""
        cls._instance = None


class Run(Base):
    """Tracks each execution of the card generation system"""

    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user_label = Column(String, nullable=True)
    mode = Column(String, nullable=False)  # "leetcode", "cs_mcq", etc.
    subject = Column(String, nullable=False)  # "leetcode", "cs", "physics"
    card_type = Column(String, nullable=False)  # "standard", "mcq"
    total_problems = Column(Integer, default=0)
    successful_problems = Column(Integer, default=0)
    failed_problems = Column(Integer, default=0)
    status = Column(String, nullable=False)  # "running", "completed", "failed"
    completed_at = Column(DateTime, nullable=True)
    run_metadata = Column(Text, nullable=True)  # JSON blob

    # Relationships
    problems = relationship(
        "Problem", back_populates="run", cascade="all, delete-orphan"
    )
    provider_results = relationship(
        "ProviderResult", back_populates="run", cascade="all, delete-orphan"
    )
    cards = relationship("Card", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_runs_created_at", "created_at"),
        Index("idx_runs_mode", "mode"),
        Index("idx_runs_status", "status"),
    )


class Problem(Base):
    """Tracks each problem/question processed"""

    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    question_name = Column(String, nullable=False)
    sanitized_name = Column(String, nullable=False)
    category_name = Column(String, nullable=True)
    category_index = Column(Integer, nullable=True)
    problem_index = Column(Integer, nullable=True)
    status = Column(String, nullable=False)  # "success", "failed", "partial", "running"
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    processing_time_seconds = Column(Float, nullable=True)
    final_card_count = Column(Integer, nullable=True)
    final_result = Column(Text, nullable=True)  # JSON blob

    # Relationships
    run = relationship("Run", back_populates="problems")
    provider_results = relationship(
        "ProviderResult", back_populates="problem", cascade="all, delete-orphan"
    )
    cards = relationship("Card", back_populates="problem", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_problems_run_id", "run_id"),
        Index("idx_problems_question_name", "question_name"),
        Index("idx_problems_created_at", "created_at"),
        Index("idx_problems_status", "status"),
    )


class ProviderResult(Base):
    """Tracks individual provider outputs before combining"""

    __tablename__ = "provider_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    provider_name = Column(String, nullable=False)  # "llm2deck_cerebras", etc.
    provider_model = Column(String, nullable=False)  # "llama3.1-70b", etc.
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    success = Column(Boolean, nullable=False)
    raw_output = Column(Text, nullable=True)  # Raw JSON string
    card_count = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    problem = relationship("Problem", back_populates="provider_results")
    run = relationship("Run", back_populates="provider_results")

    __table_args__ = (
        Index("idx_provider_results_problem_id", "problem_id"),
        Index("idx_provider_results_run_id", "run_id"),
        Index("idx_provider_results_provider_name", "provider_name"),
        Index("idx_provider_results_success", "success"),
    )


class Card(Base):
    """Individual cards extracted from final results"""

    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    card_index = Column(Integer, nullable=False)  # Position in deck (0-based)
    card_type = Column(String, nullable=True)  # "BruteForceAlgorithm", etc.
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    tags = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    problem = relationship("Problem", back_populates="cards")
    run = relationship("Run", back_populates="cards")

    __table_args__ = (
        Index("idx_cards_problem_id", "problem_id"),
        Index("idx_cards_run_id", "run_id"),
        Index("idx_cards_card_type", "card_type"),
    )


class LLMCache(Base):
    """Cache for LLM API responses."""

    __tablename__ = "llm_cache"

    cache_key = Column(String(64), primary_key=True)  # SHA256 hex
    provider_name = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_preview = Column(String(200), nullable=True)  # First 200 chars for debugging
    response = Column(Text, nullable=False)  # Raw JSON response
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    hit_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_llm_cache_provider", "provider_name"),
        Index("idx_llm_cache_created", "created_at"),
    )


def init_database(db_path: Path) -> None:
    """
    Initialize database engine and create tables.

    .. deprecated::
        Use DatabaseManager.get_default().initialize() instead.
    """
    warnings.warn(
        "init_database() is deprecated. Use DatabaseManager.get_default().initialize() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    DatabaseManager.get_default().initialize(db_path)


def get_session() -> Session:
    """
    Get a new database session.

    .. deprecated::
        Use DatabaseManager.get_default().get_session() instead.
    """
    warnings.warn(
        "get_session() is deprecated. Use DatabaseManager.get_default().get_session() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return DatabaseManager.get_default().get_session()


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.

    .. deprecated::
        Use DatabaseManager.get_default().session_scope() instead.
    """
    warnings.warn(
        "session_scope() is deprecated. Use DatabaseManager.get_default().session_scope() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    with DatabaseManager.get_default().session_scope() as session:
        yield session


# CRUD Operations


def create_run(
    session: Session,
    id: str,
    mode: str,
    subject: str,
    card_type: str,
    status: str = "running",
    user_label: Optional[str] = None,
    run_metadata: Optional[Dict] = None,
) -> Run:
    """Create a new run entry"""
    run = Run(
        id=id,
        user_label=user_label,
        mode=mode,
        subject=subject,
        card_type=card_type,
        status=status,
        run_metadata=json.dumps(run_metadata) if run_metadata else None,
    )
    session.add(run)
    session.commit()
    logger.info(f"Created run: {id} ({mode})")
    return run


def update_run(session: Session, run_id: str, **kwargs) -> Run:
    """Update an existing run"""
    run = session.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise ValueError(f"Run not found: {run_id}")

    # Update completed_at if status is being set to completed
    if kwargs.get("status") == "completed" and "completed_at" not in kwargs:
        kwargs["completed_at"] = datetime.now(timezone.utc)

    for key, value in kwargs.items():
        if hasattr(run, key):
            setattr(run, key, value)

    session.commit()
    return run


def create_problem(
    session: Session,
    run_id: str,
    question_name: str,
    status: str = "running",
    category_name: Optional[str] = None,
    category_index: Optional[int] = None,
    problem_index: Optional[int] = None,
) -> Problem:
    """Create a new problem entry"""
    from src.utils import sanitize_filename

    problem = Problem(
        run_id=run_id,
        question_name=question_name,
        sanitized_name=sanitize_filename(question_name),
        category_name=category_name,
        category_index=category_index,
        problem_index=problem_index,
        status=status,
    )
    session.add(problem)
    session.commit()
    logger.debug(f"Created problem: {question_name} (ID: {problem.id})")
    return problem


def update_problem(session: Session, problem_id: int, **kwargs) -> Problem:
    """Update an existing problem"""
    problem = session.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise ValueError(f"Problem not found: {problem_id}")

    for key, value in kwargs.items():
        if hasattr(problem, key):
            setattr(problem, key, value)

    session.commit()
    return problem


def create_provider_result(
    session: Session,
    problem_id: int,
    run_id: str,
    provider_name: str,
    provider_model: str,
    success: bool,
    raw_output: Optional[str] = None,
    card_count: Optional[int] = None,
    processing_time_seconds: Optional[float] = None,
    error_message: Optional[str] = None,
) -> ProviderResult:
    """Create a new provider result entry"""
    result = ProviderResult(
        problem_id=problem_id,
        run_id=run_id,
        provider_name=provider_name,
        provider_model=provider_model,
        success=success,
        raw_output=raw_output,
        card_count=card_count,
        processing_time_seconds=processing_time_seconds,
        error_message=error_message,
    )
    session.add(result)
    session.commit()
    logger.debug(f"Saved provider result: {provider_name} for problem {problem_id}")
    return result


def create_cards(
    session: Session, problem_id: int, run_id: str, cards_data: List[Dict[str, Any]]
) -> List[Card]:
    """Create multiple card entries from card data"""
    cards = []
    for idx, card_data in enumerate(cards_data):
        card = Card(
            problem_id=problem_id,
            run_id=run_id,
            card_index=idx,
            card_type=card_data.get("card_type"),
            front=card_data.get("front", ""),
            back=card_data.get("back", ""),
            tags=json.dumps(card_data.get("tags", [])),
        )
        cards.append(card)
        session.add(card)

    session.commit()
    logger.debug(f"Saved {len(cards)} cards for problem {problem_id}")
    return cards


def get_run(session: Session, run_id: str) -> Optional[Run]:
    """Get a run by ID"""
    return session.query(Run).filter(Run.id == run_id).first()


def get_problem(session: Session, problem_id: int) -> Optional[Problem]:
    """Get a problem by ID"""
    return session.query(Problem).filter(Problem.id == problem_id).first()
