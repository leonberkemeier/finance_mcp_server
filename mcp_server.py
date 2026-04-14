import logging
import json
import os
from typing import Dict, Any

# Try to import FastMCP; if it's not installed (dev machine), provide a minimal stub so
# this file can still be imported and the tool functions executed locally.
try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - fallback when `mcp` package is not installed
    class FastMCP:  # minimal stub used for local testing
        def __init__(self, name: str):
            self.name = name

        def tool(self):
            def decorator(fn):
                return fn

            return decorator

        def run(self, *args, **kwargs):
            return None


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize the MCP Server
# We name it "FinancialDataHub" so the LLM Client knows what it provides
mcp = FastMCP("FinancialDataHub")

@mcp.tool()
def get_quantitative_risk(ticker: str) -> str:
    """
    Retrieves the latest Phase 1 & Phase 2 mathematical risk metrics (Markov/Monte Carlo) for a given asset.
    Use this tool FIRST when analyzing an asset to understand its baseline mathematical risk.
    """
    logger.info(f"[TOOL CALLED] get_quantitative_risk for {ticker}")

    # Attempt to load real data from the SQLite DB via our db helper. Import lazily so
    # this module can be imported even when SQLAlchemy isn't installed.
    try:
        from . import db as _db
    except Exception:
        # Try relative import fallback for when running as a script from the same dir
        try:
            import db as _db
        except Exception:
            _db = None

    if _db:
        data = _db.get_risk_by_ticker(ticker)
        if data:
            # Return a stable JSON string so downstream tools/LLMs can parse easily.
            return json.dumps({
                "ticker": data.get("ticker"),
                "var_95": data.get("var_95"),
                "expected_return": data.get("expected_return"),
                "regime": data.get("regime"),
            })

    # Fallback mocked responses if DB not available or no row found
    if ticker.upper() == "AAPL":
        return json.dumps({
            "ticker": ticker.upper(),
            "regime": "Bull Market",
            "var_95": -0.04,
            "expected_return": 0.08,
        })
    elif ticker.upper() == "NVDA":
        return json.dumps({
            "ticker": ticker.upper(),
            "regime": "High Volatility",
            "var_95": -0.09,
            "expected_return": 0.15,
        })
    else:
        return json.dumps({
            "ticker": ticker.upper(),
            "regime": "Sideways",
            "var_95": -0.05,
            "expected_return": 0.06,
        })

@mcp.tool()
def search_filings_and_earnings(ticker: str, query: str) -> str:
    """
    Performs a semantic vector search over the company's recent SEC EDGAR filings, 10-Ks, and earnings calls.
    Use this tool SECOND to retrieve qualitative fundamental sentiment regarding a specific query (e.g. "AI revenue guidance").
    """
    logger.info(f"[TOOL CALLED] search_filings_and_earnings for {ticker} with query: '{query}'")
    
    # TODO: Connect to the actual Vector DB (pgvector / ChromaDB)
    # For now, we return a mocked RAG chunk to simulate finding CEO quotes
    return (
        f"Retrieval Context for {ticker} | Query: '{query}'\n"
        f"Snippet 1 (from Q3 Earnings Call): 'We are extremely optimistic about the fundamental demand in the upcoming year. "
        f"Our forward guidance looks incredibly strong despite macroeconomic headwinds.'"
    )

@mcp.tool()
def get_macro_economic_indicators() -> str:
    """
    Retrieves current FRED macroeconomic data vital for context.
    Use this tool to understand the broader US economy.
    """
    logger.info("[TOOL CALLED] get_macro_economic_indicators")
    
    # TODO: Connect to FRED tables in Database
    return "US Macro Data: Interest Rates=4.5%, Inflation (CPI)=2.8%, GDP Growth=2.1%. The environment favors technology and growth equities."

if __name__ == "__main__":
    # You can run this file directly to test it via 'stdio' 
    # Or, in production via Tailscale, we will run this Server using Server-Sent Events (SSE).
    # To run via SSE: `mcp dev mcp_server.py` or use a wrapper framework.
    logger.info("Starting FinancialDataHub MCP Server...")
    mcp.run(transport="stdio")
