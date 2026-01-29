# Chess Coach Web API

FastAPI web application for chess game analysis and mistake detection.

## Local Development

### Prerequisites

- Python 3.8+
- Stockfish engine installed and available in PATH, or set `STOCKFISH_PATH` environment variable

### Setup

From the **project root** (`chess_coach_v2`), not from the `web` folder:

```powershell
# Activate your venv first, then install web deps
pip install -r web/requirements.txt

# Run the server (use python -m so uvicorn is found without being on PATH)
python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000/ in your browser.

### Environment Variables

- `STOCKFISH_PATH`: Path to Stockfish executable (default: "stockfish" - expects it in PATH)

## API Endpoints

- `GET /` - Web UI (single-page app)
- `GET /health` - Health check
- `POST /api/analyze` - Analyze a game from PGN

### Example API Usage

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5..."}'
```

## Deployment on Render.com

1. **Create a new Web Service** on Render
2. **Connect your GitHub repository**
3. **Settings:**
   - **Root Directory**: `web`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**: 
     - `STOCKFISH_PATH`: Set to path where Stockfish is installed (or use Docker)

### Using Docker (Recommended for Stockfish)

Create a `Dockerfile` in the `web/` directory:

```dockerfile
FROM python:3.10-slim

# Install Stockfish
RUN apt-get update && apt-get install -y stockfish && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (needed for chess_engine imports)
COPY .. /app/..

WORKDIR /app/../web

# Expose port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Then on Render:
- **Docker**: Enable Docker
- **Dockerfile Path**: `web/Dockerfile`
- **Docker Context**: `.` (root of repo)
