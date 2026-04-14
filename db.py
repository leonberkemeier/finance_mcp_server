import os
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from sqlalchemy import create_engine, Column, Integer, String, Float
    from sqlalchemy.orm import sessionmaker, declarative_base
except Exception:  # pragma: no cover - allow the module to be imported without sqlalchemy installed
    create_engine = None  # type: ignore


# Database configuration
DEFAULT_DB_PATH = Path(__file__).parent / "financial_data.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


def _create_sqlalchemy_components():
    """Create SQLAlchemy engine, session and Base. Returns None if SQLAlchemy isn't available."""
    if create_engine is None:
        return None

    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base = declarative_base()

    class RiskMetric(Base):
        __tablename__ = "risk_metrics"
        id = Column(Integer, primary_key=True, index=True)
        ticker = Column(String, index=True)
        var_95 = Column(Float)
        expected_return = Column(Float)
        regime = Column(String)

    return engine, SessionLocal, Base, RiskMetric


_components = _create_sqlalchemy_components()


def get_risk_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Query the `risk_metrics` table for the most recent entry for `ticker`.

    Returns a dict like:
      {"ticker": "AAPL", "var_95": -0.04, "expected_return": 0.08, "regime": "Bull Market"}

    Returns None if SQLAlchemy isn't installed, the DB cannot be reached, or no row exists.
    """
    if _components is None:
        return None

    engine, SessionLocal, Base, RiskMetric = _components
    try:
        with SessionLocal() as session:
            row = (
                session.query(RiskMetric)
                .filter(RiskMetric.ticker == ticker.upper())
                .order_by(RiskMetric.id.desc())
                .first()
            )
            if not row:
                return None
            return {
                "ticker": row.ticker,
                "var_95": row.var_95,
                "expected_return": row.expected_return,
                "regime": row.regime,
            }
    except Exception:
        # Any DB error should be treated as no data available for our higher-level caller.
        return None


def create_tables_if_missing() -> None:
    """Helper to create tables if desired during development. No-op if SQLAlchemy missing."""
    if _components is None:
        return
    engine, SessionLocal, Base, RiskMetric = _components
    Base.metadata.create_all(bind=engine)
