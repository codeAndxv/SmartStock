# SmartStock

[中文版](README_CN.md)

A-share limit-up stock scanner with next-day movement prediction.

## Product Goals

- Scan all stocks that hit the daily limit-up (涨停) on a given trading day
- Analyze each stock's recent trading pattern, industry, and fundamentals
- Predict next-day movement using a multi-factor scoring model
- Present results in a sortable web table with real-time progress

## How It Works

1. Fetches the daily limit-up pool from AKShare (东方财富 data source)
2. For each stock, pulls 30-day OHLCV bars (Sina) and company profile (Xueqiu)
3. Scores the stock on 6 factors: consecutive limits, broken seals, seal time, turnover, volume trend, price trend
4. Maps the total score to a predicted next-day change percentage
5. Streams progress to the frontend via SSE (Server-Sent Events)

## Project Structure

```
SmartStock/
├── backend/                # FastAPI server + Python environment
│   ├── .venv/              # Virtual environment
│   ├── pyproject.toml      # Python dependencies
│   ├── app.py              # API endpoints
│   ├── core/               # Business logic
│   │   ├── scan_limit_up.py # Scanning & prediction
│   │   └── stock_info.py   # AKShare data helpers
│   └── cli/                # CLI tools
│       └── main.py         # CLI example
├── web/                    # Vue 3 + Vite frontend
│   └── src/
│       ├── App.vue
│       └── components/
│           └── LimitUpTable.vue
└── API_NOTES.md            # AKShare API connectivity notes
```

## Environment Setup

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
cd ..
```

### Frontend

```bash
cd web
npm install
```

## Start the App

Open two terminals:

```bash
# Terminal 1 — Backend (port 8000)
source backend/.venv/bin/activate
uvicorn backend.app:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (port 5173)
cd web
npm run dev
```

Then open http://localhost:5173, click "涨停分析" in the sidebar, and hit "开始扫描".

## CLI Usage

```bash
source backend/.venv/bin/activate
python -m backend.cli.main [STOCK_CODE] [DAYS]
```
