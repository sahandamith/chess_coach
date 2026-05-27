# Chess Coach

Free, open-source chess game analyzer. Paste a PGN, get instant feedback on mistakes, best moves, and variations.

**Live Demo:** https://sahandamith.github.io/chess_coach/

---

## 🚀 Quick Start

### **For Users (GitHub Pages)**
1. Visit: https://sahandamith.github.io/chess_coach/
2. Paste your game PGN
3. Click "Analyze Game"
4. See mistakes, best moves, and replay analysis

> **Note:** You'll need to deploy the backend API separately. See [Deployment Guide](docs/DEPLOYMENT.md).

### **For Developers (Local)**

**Backend (FastAPI + Stockfish):**
```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Then open http://localhost:8000 in your browser.

**Desktop (Tkinter GUI - Optional):**
```bash
cd local
pip install -r requirements.txt
python chess_analyzer.py
```

---

## 📁 Project Structure

```
chess_coach/
├── docs/                    # GitHub Pages frontend (static HTML/JS/CSS)
│   ├── index.html          # Main analysis interface
│   ├── feedback.html        # Feedback page
│   ├── app.js              # Frontend logic
│   ├── style.css           # Styling
│   └── DEPLOYMENT.md       # Deployment instructions
│
├── static/                  # Source files for frontend (edit these)
│   ├── index.html
│   ├── feedback.html
│   ├── app.js
│   └── style.css
│
├── main.py                  # FastAPI backend (chess analysis server)
├── requirements.txt         # Python dependencies
│
├── chess_engine/            # Shared chess analysis engine
│   ├── analyzer.py          # Game analyzer (loads PGN, evaluates positions)
│   ├── mistake_analyzer.py  # Mistake detection & categorization
│   └── gui.py               # GUI utilities
│
├── local/                   # Desktop app (optional, Tkinter-based)
│   ├── chess_analyzer.py
│   ├── chess_engine/        # Copy of shared engine
│   └── requirements.txt
│
└── CNAME                    # GitHub Pages custom domain
```

---

## 🎮 Features

✅ **Instant Analysis** – Evaluates every position with Stockfish
✅ **Mistake Detection** – Identifies blunders, mistakes, and inaccuracies
✅ **Best Move Suggestions** – Shows alternative lines with evaluations
✅ **Interactive Replay** – Play through the game move-by-move
✅ **Eval Graph** – Visualize advantage swings over time
✅ **Free & Open Source** – No paywalls, no ads

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | HTML5, JavaScript (Chessboard.js), CSS |
| **Backend** | FastAPI (Python), Stockfish UCI engine |
| **Deployment** | GitHub Pages (frontend) + Any ASGI host (backend) |
| **Chess Logic** | python-chess library, Stockfish engine |

---

## 🚢 Deployment

### Frontend (GitHub Pages)
The `docs/` folder is automatically served by GitHub Pages. No action needed after push.

**Verify GitHub Pages settings:**
- Settings → Pages → **Source:** `Deploy from a branch`
- **Branch:** `master`, **Folder:** `/ (root)`

### Backend (Flask/FastAPI)
You must deploy the backend (main.py) to a separate ASGI host:

**Recommended:**
- [Railway.app](https://railway.app) (easiest)
- [Render.com](https://render.com)
- [Fly.io](https://fly.io)
- [Heroku](https://heroku.com)

**See:** [Deployment Guide](docs/DEPLOYMENT.md) for step-by-step instructions.

---

## 📋 Prerequisites

### To Run Locally
- Python 3.8+
- Stockfish chess engine (download from https://stockfishchess.org/download/)

### To Deploy
- GitHub account (for GitHub Pages frontend)
- Railway/Render account (or other ASGI host for backend)

---

## 🐛 How It Works

1. **User uploads PGN** → Frontend sends to backend API
2. **Backend loads game** → ChessAnalyzer parses moves, evaluates positions with Stockfish
3. **Mistakes detected** → MistakeAnalyzer categorizes errors (hanging piece, king safety, etc.)
4. **Best lines computed** → Shows alternatives with evaluations
5. **Frontend displays results** → Interactive board, move list, eval graph
6. **User replays game** → Step through with board updates and annotations

---

## 📊 Example API Response

```json
{
  "game": {
    "white": "Player1",
    "black": "Player2",
    "result": "1-0"
  },
  "mistakes": [
    {
      "move_number": 15,
      "move_san": "Nf6",
      "evaluation_before": 50,
      "evaluation_after": -150,
      "best_move_san": "d5",
      "best_moves": ["d5"],
      "continuation_moves": ["Nc3", "e4"]
    }
  ],
  "positions": [/* all position evaluations */]
}
```

---

## 💬 Feedback & Suggestions

Found a bug? Have a feature request? Click "Feedback & suggestions" on the app or open an issue on GitHub.

---

## 📜 License

Open source. Use freely.

---

## 🎯 Development Notes

- **Local & Web are independent:** `local/` and `chess_engine/` in root maintain separate copies
- **Sync changes:** When updating the chess analysis engine, sync `chess_engine/` between `local/` and root manually
- **GitHub Pages limitation:** Static files only; backend must be deployed elsewhere
- **CORS:** Backend CORS must allow requests from your GitHub Pages URL

See [Deployment Guide](docs/DEPLOYMENT.md) for more details.
