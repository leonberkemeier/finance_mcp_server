import os
from pathlib import Path
from typing import Optional, Dict, Any

# Optionally load .env if python-dotenv is installed. This keeps behaviour predictable
# for developers who prefer a local .env file. If python-dotenv is not installed we
# silently continue and rely on environment variables.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

try:
    from sqlalchemy import create_engine, Column, Integer, String, Float
    from sqlalchemy.orm import sessionmaker, declarative_base
except Exception:  # pragma: no cover - allow the module to be imported without sqlalchemy installed
    create_engine = None  # type: ignore


# Database configuration
# Default DB path lives next to this module; override with the DATABASE_URL env var.
DEFAULT_DB_PATH = Path(__file__).parent / "financial_data.db"
# Respect DATABASE_URL from environment (including values loaded from .env above).
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

    class Company(Base):
        __tablename__ = "dim_company"
        company_id = Column(Integer, primary_key=True)
        ticker = Column(String, index=True)

    class StockPrice(Base):
        __tablename__ = "fact_stock_price"
        price_id = Column(Integer, primary_key=True)
        company_id = Column(Integer)
        close_price = Column(Float)
        price_change_percent = Column(Float)
        volume = Column(Integer)
        
    class CompanyMetric(Base):
        __tablename__ = "fact_company_metrics"
        metric_id = Column(Integer, primary_key=True)
        company_id = Column(Integer)
        beta = Column(Float)
        pe_ratio = Column(Float)

    class QuantitativeRisk(Base):
        """Table to store Phase 1 & Phase 2 ML calculated metrics."""
        __tablename__ = "fact_quantitative_risk"
        risk_id = Column(Integer, primary_key=True, autoincrement=True)
        company_id = Column(Integer, index=True)
        date_id = Column(Integer)  # To link to dim_date
        var_95 = Column(Float)
        expected_return = Column(Float)
        regime = Column(String)
        created_at = Column(String)

    return engine, SessionLocal, Base, Company, StockPrice, CompanyMetric, QuantitativeRisk


_components = _create_sqlalchemy_components()


def get_risk_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Query the real historical database to synthesize quantitative data for `ticker`.
    Since there is no `risk_metrics` table, we fetch the most recent close price
    and price change, returning a synthetic response shape expected by the agent.

    Returns a dict like:
      {"ticker": "AAPL", "var_95": -0.04, "expected_return": 0.08, "regime": "Bull Market", "last_close": 150.0}

    Returns None if SQLAlchemy isn't installed, the DB cannot be reached, or no row exists.
    """
    if _components is None:
        return None

    engine, SessionLocal, Base, Company, StockPrice, CompanyMetric, QuantitativeRisk = _components
    try:
        with SessionLocal() as session:
            # 1. Find the company
            company = session.query(Company).filter(Company.ticker == ticker.upper()).first()
            if not company:
                return None

            # 2. Get the latest price and fundamental metrics
            latest_price = (
                session.query(StockPrice)
                .filter(StockPrice.company_id == company.company_id)
                .order_by(StockPrice.price_id.desc())
                .first()
            )
            latest_metric = (
                session.query(CompanyMetric)
                .filter(CompanyMetric.company_id == company.company_id)
                .order_by(CompanyMetric.metric_id.desc())
                .first()
            )
            
            # 3. Get the latest risk metrics stored by the ML nodes
            latest_risk = (
                session.query(QuantitativeRisk)
                .filter(QuantitativeRisk.company_id == company.company_id)
                .order_by(QuantitativeRisk.risk_id.desc())
                .first()
            )
            
            if not latest_price:
                return None
                
            # Populate from the actual ML output table. If no entries exist yet (empty table), they remain None.
            exp_return = latest_risk.expected_return if latest_risk else None
            var95 = latest_risk.var_95 if latest_risk else None
            regime = latest_risk.regime if latest_risk else "Pending Processing"

            close_px = latest_price.close_price if latest_price else None
            beta = latest_metric.beta if latest_metric else None
            pe_ratio = latest_metric.pe_ratio if latest_metric else None

            data_status = (
                "Complete" if latest_risk 
                else "Prices and fundamentals available; Advanced risk metrics pending ML node calculation."
            )

            return {
                "ticker": company.ticker,
                "var_95": var95,
                "expected_return": exp_return,
                "regime": regime,
                "beta": beta,
                "pe_ratio": pe_ratio,
                "last_close": close_px,
                "data_status": data_status
            }
    except Exception as e:
        # Any DB error should be treated as no data available
        import logging
        logging.error(f"DB Error fetching risk for {ticker}: {e}")
        return None


def create_tables_if_missing() -> None:
    """Helper to create tables if desired during development. No-op if SQLAlchemy missing."""
    if _components is None:
        return
    engine, SessionLocal, Base, Company, StockPrice, CompanyMetric, QuantitativeRisk = _components
    
    # This will create the fact_quantitative_risk table so the ML node can write to it
    QuantitativeRisk.__table__.create(engine, checkfirst=True)
