# Chess Coach

Two separate implementations so you can develop and deploy independently:

- **`local/`** – Desktop app (Tkinter GUI, matplotlib). Run locally, add features here without touching the web app.
- **`web/`** – Web app for [Render.com](https://render.com). Self-contained (includes its own copy of the engine). Deploy from this folder or set Render’s root to `web`.

## Local (desktop)

```bash
cd local
pip install -r requirements.txt
python chess_analyzer.py
```

Set Stockfish path in `local/chess_analyzer.py` (`STOCKFISH_PATH`) or install Stockfish and put it on `PATH`.

## Web (Render, Docker)

The `web/` app can be deployed with **Docker** so Stockfish is included in the image.

**Local run (no Docker):**
```bash
cd web
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Docker (recommended for Render):**
```bash
cd web
docker build -t chess-coach-web .
docker run -p 8000:8000 chess-coach-web
```

On **Render**, use a **Docker** web service:
- **Root Directory:** `web`
- **Dockerfile path:** `Dockerfile` (uses `web/Dockerfile`)
- No Start Command needed; the image runs `uvicorn` with `$PORT`.
- Stockfish is installed inside the image; you do **not** need to set `STOCKFISH_PATH` unless you override it.

## Git layout

- `local/` – local-only code; not required for Render.
- `web/` – everything needed for Render (FastAPI app, static files, `chess_engine` copy).
- You can add features in `local/` or `web/` independently; sync `chess_engine` between them when you want to share analyzer changes.
