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

## 🚀 How to Run & Deploy It

### 1. Local Testing (STDIO)
For local editors (like Cursor or VS Code) that connect to an MCP server via standard input/output:
```bash
export MCP_TRANSPORT="stdio"
python mcp_server.py
```

### 2. Network Deployment (Tailscale / AI PC / Remote) 
To deploy this server across your network so your remote AI PC ML Node (Gemma 4 etc.) can call the tools as REST requests, use `sse` (Server-Sent Events) transport.

This requires `uvicorn` and `fastapi`:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install fastapi uvicorn  # Ensure these are installed for SSE
```

Run the server on all network interfaces via port 8000:
```bash
export MCP_TRANSPORT="sse"
export MCP_PORT="8000"
python mcp_server.py
```

Your remote AI Node can then connect an MCP Client to `http://<TAILSCALE_IP>:8000/sse` to start calling the Webserver's Database Tools autonomously.

   ## ⚙️ Configuration (.env)

   The application reads the `DATABASE_URL` environment variable to locate the relational database used by the MCP tools.
   You can set `DATABASE_URL` in your environment, or create a local `.env` file (use the example `.env.example` included in this folder).

   Examples:

   zsh
   ```bash
   # Absolute path to an sqlite DB file
   export DATABASE_URL="sqlite:////home/archy/Desktop/Server/FinancialData/webserver_api/financial_data.db"

   # Or create a `.env` file with the same content (and optionally install python-dotenv).
   ```

   If `python-dotenv` is installed, the code will automatically attempt to load a `.env` file from this folder.

---

## ⏭️ Next Development Steps
- **Database Connection:** Connect `mcp_server.py` to the actual SQLAlchemy database instead of returning mocked strings.
- **RAG Pipeline:** Implement the Python script that ingests the SEC `.txt` files, embeds them, and saves them into the Vector DB.
- **FastAPI Integration:** Expand this folder to also include the standard REST endpoints (`/api/portfolio/greenfield_models`) that the AI PC will POST the final portfolios to.