from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
import sqlite3
import json
import os
from pathlib import Path

app = FastAPI(title="FinancialDataHub REST API")

DATABASE_URL = os.environ.get("DATABASE_URL", str(Path(__file__).parent / "financial_data.db"))
# strip sqlite:/// if present for sqlite3
db_path = DATABASE_URL.replace("sqlite:///", "")

def get_db():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_markov_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_date TEXT,
                current_regime INTEGER,
                regime_probability REAL,
                transition_matrix TEXT,
                probability_next_regime TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_monte_carlo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                mean_return REAL,
                var_95 REAL,
                es_95 REAL,
                prob_loss REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_llm_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_date TEXT,
                ticker TEXT,
                score REAL,
                reasoning TEXT
            )
        """)

init_db()

class MarkovPayload(BaseModel):
    execution_date: str
    current_regime: int
    regime_probability: float
    transition_matrix: List[List[float]]
    probability_next_regime: Dict[str, float]

class LLMPayload(BaseModel):
    execution_date: str
    scores: Dict[str, Dict[str, Any]]

@app.get("/api/data/latest")
def get_data_latest(days: int = 30):
    with get_db() as conn:
        # Get the latest `days` distinct dates
        recent_dates_rows = conn.execute("""
            SELECT date_id, date 
            FROM dim_date 
            ORDER BY date DESC 
            LIMIT ?
        """, (days,)).fetchall()
        
        if not recent_dates_rows:
            return []
            
        latest_date_ids = [str(r["date_id"]) for r in recent_dates_rows]
        placeholders = ",".join("?" for _ in latest_date_ids)
        
        rows = conn.execute(f"""
            SELECT 
                d.date,
                c.ticker,
                f.close_price
            FROM fact_stock_price f
            JOIN dim_company c ON c.company_id = f.company_id
            JOIN dim_date d ON d.date_id = f.date_id
            WHERE f.date_id IN ({placeholders})
            ORDER BY d.date DESC, c.ticker ASC
        """, latest_date_ids).fetchall()
        
        # Pivot the data so each date row contains the tickers as columns
        # Output format: [{"date": "2026-04-10", "AAPL": 150.5, "NVDA": 210.2}, ...]
        pivoted_data = {}
        for row in rows:
            date_str = row["date"]
            if date_str not in pivoted_data:
                pivoted_data[date_str] = {"date": date_str}
            pivoted_data[date_str][row["ticker"]] = row["close_price"]
            
        return list(pivoted_data.values())

@app.get("/api/analysis/markov")
def get_markov():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fact_markov_state ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            return {"execution_date": row["execution_date"], "current_regime": row["current_regime"]}
        return {"execution_date": "2026-04-14", "current_regime": 2}

@app.get("/api/analysis/monte_carlo")
def get_monte_carlo():
    with get_db() as conn:
        rows = conn.execute("SELECT ticker, mean_return, var_95, es_95, prob_loss FROM fact_monte_carlo").fetchall()
        return [dict(r) for r in rows]

@app.post("/api/analysis/markov")
def post_markov(payload: MarkovPayload):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO fact_markov_state (execution_date, current_regime, regime_probability, transition_matrix, probability_next_regime)
            VALUES (?, ?, ?, ?, ?)
        """, (payload.execution_date, payload.current_regime, payload.regime_probability, 
              json.dumps(payload.transition_matrix), json.dumps(payload.probability_next_regime)))
    return {"status": "success", "message": "Markov state recorded"}

@app.post("/api/analysis/monte_carlo")
def post_monte_carlo(payload: List[Dict[str, Any]]):
    with get_db() as conn:
        # Clear old for simplicity, or just append
        conn.execute("DELETE FROM fact_monte_carlo")
        for item in payload:
            conn.execute("""
                INSERT INTO fact_monte_carlo (ticker, mean_return, var_95, es_95, prob_loss)
                VALUES (?, ?, ?, ?, ?)
            """, (item.get("ticker"), item.get("mean_return"), item.get("var_95"), item.get("es_95"), item.get("prob_loss")))
    return {"status": "success", "message": f"Recorded risk for {len(payload)} tickers"}

@app.post("/api/analysis/llm")
def post_llm(payload: LLMPayload):
    with get_db() as conn:
        for ticker, data in payload.scores.items():
            conn.execute("""
                INSERT INTO fact_llm_scores (execution_date, ticker, score, reasoning)
                VALUES (?, ?, ?, ?)
            """, (payload.execution_date, ticker, data.get("score"), data.get("reasoning")))
    return {"status": "success", "message": "LLM scorings recorded"}
