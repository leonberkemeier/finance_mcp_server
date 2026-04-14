"""Small verification script to show the configured DATABASE_URL and a sample query.

Run from the `webserver_api` folder:
    python3 scripts/verify_db.py

This script will attempt to use the SQLAlchemy-backed helper in `db.py`. If SQLAlchemy
is not installed or the DB cannot be reached, it will report that and show the mocked
fallback behavior.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

try:
    import db
except Exception as exc:
    print("Failed to import db helper:", exc)
    raise

print("Configured DATABASE_URL:", db.DATABASE_URL)

# Show whether SQLAlchemy components are available
has_components = getattr(db, "_components", None) is not None
print("SQLAlchemy available:", has_components)

# Try to fetch a sample ticker row using the helper
sample_ticker = "AAPL"
result = db.get_risk_by_ticker(sample_ticker)
if result:
    print(f"DB row for {sample_ticker}:", json.dumps(result, indent=2))
else:
    print(f"No DB row found for {sample_ticker} or DB unavailable. Falling back to mocked output.")
    # Demonstrate the MCP tool fallback
    try:
        from mcp_server import get_quantitative_risk
        print("Mocked tool output:", get_quantitative_risk(sample_ticker))
    except Exception as exc:
        print("Also failed to call mcp_server.get_quantitative_risk():", exc)
