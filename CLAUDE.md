# Zeitgeist — AI Trend Prediction Engine

## What is this?

Zeitgeist predicts trending topics **24-72 hours BEFORE they trend**. It monitors early signals from multiple sources (HackerNews, Reddit, GitHub trending, ArXiv, patents, job postings), uses AI to identify patterns, and generates predictions with confidence scores.

> Google Trends tells you NOW. Zeitgeist tells you TOMORROW.

## Project Structure

```
zeitgeist/
├── zeitgeist/
│   ├── models.py        # Pydantic models (Signal, TrendPrediction, TrendReport)
│   ├── sources/         # Signal collectors (HN, Reddit, GitHub, Mock)
│   ├── analyzer.py      # Core analysis engine (collect → analyze → predict → report)
│   ├── ai.py            # LLM abstraction (Anthropic / OpenAI / fallback heuristics)
│   ├── store.py         # SQLite persistence
│   ├── cli.py           # Typer CLI with Rich output
│   ├── api/app.py       # FastAPI REST API
│   └── mcp/server.py    # MCP server (FastMCP)
├── tests/               # Pytest test suite
├── pyproject.toml       # Package config
└── .env.example         # Environment template
```

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
zeitgeist scan --mock      # Quick demo with mock data
zeitgeist scan             # Live scan from HN, Reddit, GitHub
```

## Key Commands

- `zeitgeist scan [--mock]` — Scan sources and generate predictions
- `zeitgeist predict` — Show latest predictions
- `zeitgeist sources` — List signal sources
- `zeitgeist history` — Past predictions + accuracy

## API

```bash
uvicorn zeitgeist.api.app:app --reload
# POST /api/v1/scan — trigger scan
# GET  /api/v1/predictions — latest predictions
# GET  /api/v1/sources — list sources
# GET  /health — health check
```

## MCP Server

Configured in `.mcp.json`. Tools: `scan_trends`, `get_predictions`, `explain_zeitgeist`.

## Testing

```bash
python -m pytest tests/ -v
```

## Architecture Notes

- **No API keys needed** for basic operation — falls back to heuristic predictions
- Signal collectors are async and concurrent
- Velocity scoring accounts for cross-source signal boosting
- SQLite storage is zero-config (auto-creates at ~/.zeitgeist/)
