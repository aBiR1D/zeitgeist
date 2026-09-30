# 🔮 Zeitgeist

**AI that predicts trending topics 24-72 hours BEFORE they trend.**

> Google Trends tells you NOW. Zeitgeist tells you TOMORROW.

## Overview

Zeitgeist monitors early signals from multiple sources and uses AI to identify patterns and emerging trends before they peak:

| Source | What it watches | Status |
|--------|----------------|--------|
| **HackerNews** | Top & new stories, velocity of upvotes | ✅ Active |
| **Reddit** | Rising posts from tech subreddits | ✅ Active |
| **GitHub** | Trending repositories by stars | ✅ Active |
| **ArXiv** | Recent ML/CS paper submissions | 🔜 Coming |
| **Patents** | New tech patent filings | 🔜 Coming |
| **Job Postings** | Emerging skill demand | 🔜 Coming |

Each prediction includes:
- **Topic** — What's about to trend
- **Confidence Score** — 0-100% likelihood
- **Predicted Peak** — When it'll peak (24-72h window)
- **Velocity** — How fast signals are accelerating
- **Explanation** — AI-generated reasoning
- **Recommended Actions** — What to do about it

## Installation

```bash
git clone https://github.com/yourusername/zeitgeist.git
cd zeitgeist
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Quick Start

```bash
# Demo with mock data (no API keys needed)
zeitgeist scan --mock

# Live scan from real sources
zeitgeist scan

# View predictions
zeitgeist predict

# See available sources
zeitgeist sources

# Check prediction history
zeitgeist history
```

## Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

**Without API keys**, Zeitgeist uses heuristic-based predictions (keyword clustering + velocity scoring). **With API keys**, it uses Claude or GPT for more sophisticated pattern recognition.

## API Server

```bash
uvicorn zeitgeist.api.app:app --reload --port 8000
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/scan` | POST | Trigger a full scan |
| `/api/v1/predictions` | GET | Latest predictions |
| `/api/v1/sources` | GET | List sources |

## MCP Integration

Zeitgeist includes an MCP server for AI assistant integration:

```json
{
  "mcpServers": {
    "zeitgeist": {
      "command": "python",
      "args": ["-m", "zeitgeist.mcp.server"]
    }
  }
}
```

**MCP Tools:**
- `scan_trends` — Scan all sources and predict
- `get_predictions` — Get latest predictions
- `explain_zeitgeist` — What is Zeitgeist?

## How It Works

1. **Collect** — Async collectors fetch data from HN, Reddit, GitHub APIs
2. **Analyze** — Velocity scoring with cross-source boosting
3. **Cluster** — Related signals grouped by keyword overlap
4. **Predict** — AI (or heuristics) generates confidence-scored predictions
5. **Store** — Predictions saved to SQLite for accuracy tracking
6. **Report** — Rich terminal output with color-coded confidence bars

## Testing

```bash
python -m pytest tests/ -v
```

## License

MIT
