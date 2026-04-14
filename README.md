# 🌐 Webserver API & MCP Hub

## 📖 The Vision
This folder acts as the **Central Data Hub** for the Distributed Financial Portfolio System (Robo-Advisor). 

While the `deploy_on_ai-pc` node handles heavy ML and LLM inference, it needs data to make decisions. The `webserver_api` provides that data, but *not* as basic rigid REST endpoints. Instead, it acts as an **MCP (Model Context Protocol) Server**.

By running an MCP Server here, we expose our SQL databases and Vector Databases directly to the remote LLM as **"Tools"**. Gemma 4 (or any LLM on the AI PC) can dynamically call these tools across the Tailscale network to pull exactly the numbers and paragraphs it needs to evaluate an asset.

---

## 🛠️ The Architecture

### 1. Data Storage (To Be Implemented)
This Webserver holds the historical truth:
- **Relational DB (PostgreSQL/SQLite):** Stores daily OHLCV prices, historical Markov regimes, Monte Carlo calculations (VaR, Expected Returns), and the active portfolios.
- **Vector DB (pgvector / ChromaDB):** Stores text embeddings for SEC 10-K/10-Q filings and Earnings Call transcripts.

### 2. The MCP Server (`mcp_server.py`)
Built using the official `mcp` Python SDK (via `FastMCP`), this script translates the databases into natural-language tools that the AI PC can execute.

Current Available Tools for the LLM:
1. `get_quantitative_risk(ticker)`: Provides the mathematical risk limits (VaR) and the macro regime. (Structured Data)
2. `search_filings_and_earnings(ticker, query)`: Performs semantic RAG (Retrieval-Augmented Generation) search over filings to gauge CEO sentiment or forward guidance. (Unstructured Data)
3. `get_macro_economic_indicators()`: Fetches US FRED data (Interest Rates, CPI, GDP).

---

## 🚀 How to Run It

1. **Install Dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the MCP Server:**
   For local testing, the `fastmcp` application can be tested via STDIO or SSE. During production, we will host this over HTTP Server-Sent Events (SSE) so the remote Tailscale AI PC can reach it.
   
   To run manually for testing:
   ```bash
   python mcp_server.py
   ```

---

## ⏭️ Next Development Steps
- **Database Connection:** Connect `mcp_server.py` to the actual SQLAlchemy database instead of returning mocked strings.
- **RAG Pipeline:** Implement the Python script that ingests the SEC `.txt` files, embeds them, and saves them into the Vector DB.
- **FastAPI Integration:** Expand this folder to also include the standard REST endpoints (`/api/portfolio/greenfield_models`) that the AI PC will POST the final portfolios to.