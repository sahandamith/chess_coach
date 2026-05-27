# Chess Coach

Two separate implementations so you can develop and deploy independently:

- **`local/`** – Desktop app (Tkinter GUI, matplotlib). Run locally; add features here without touching the web app.
- **Root (web app)** – FastAPI web application for chess game analysis and mistake detection. Static files served via GitHub Pages; backend runs on any ASGI host.

## Local (desktop)

```bash
cd local
pip install -r requirements.txt
python chess_analyzer.py
```

Set Stockfish path in `local/chess_analyzer.py` (`STOCKFISH_PATH`) or install Stockfish and put it on `PATH`.

## Web (FastAPI backend)

### Prerequisites

- Python 3.8+
- Stockfish engine installed and available in `PATH`, or set the `STOCKFISH_PATH` environment variable

### Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000/ in your browser.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `STOCKFISH_PATH` | `stockfish` | Path to Stockfish executable (must be in PATH if not set) |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI (single-page app) |
| `GET` | `/health` | Health check |
| `POST` | `/api/analyze` | Analyze a game from PGN |

### Example

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5..."}'
```

## Repository layout

```
chess_coach/
├── chess_engine/       # Shared analysis engine (web copy)
├── static/             # Frontend (index.html, app.js, style.css) – served by GitHub Pages
├── main.py             # FastAPI application entry point
├── requirements.txt    # Python dependencies for the web app
├── local/              # Desktop-only code (Tkinter GUI, matplotlib)
│   ├── chess_engine/
│   ├── chess_analyzer.py
│   └── requirements.txt
└── CNAME               # GitHub Pages custom domain
```

> **Note:** `local/` and the web app (`chess_engine/`, `main.py`, etc.) maintain independent copies of the engine. Sync `chess_engine/` between them manually when you want to share analyzer changes.
