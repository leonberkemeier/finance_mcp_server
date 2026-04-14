from fastapi import FastAPI
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI(title="FinancialDataHub REST API")

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
def get_data_latest():
    return [
      {"date": "2026-04-10", "AAPL": 150.5, "NVDA": 210.2},
      {"date": "2026-04-11", "AAPL": 152.0, "NVDA": 208.5}
    ]

@app.get("/api/analysis/markov")
def get_markov():
    return {"execution_date": "2026-04-14", "current_regime": 2}

@app.get("/api/analysis/monte_carlo")
def get_monte_carlo():
    return [{"ticker": "AAPL", "mean_return": 0.05, "var_95": -0.02, "es_95": -0.03, "prob_loss": 0.3}]

@app.post("/api/analysis/markov")
def post_markov(payload: MarkovPayload):
    return {"status": "success", "message": "Markov state recorded"}

@app.post("/api/analysis/monte_carlo")
def post_monte_carlo(payload: List[Dict[str, Any]]):
    return {"status": "success", "message": f"Recorded risk for {len(payload)} tickers"}

@app.post("/api/analysis/llm")
def post_llm(payload: LLMPayload):
    return {"status": "success", "message": "LLM scorings recorded"}
