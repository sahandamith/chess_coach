# Chess Coach Deployment Guide

This folder contains the **Chess Coach Web UI** for deployment to **GitHub Pages**. The frontend is static (HTML/JS/CSS) and requires a backend API to function.

## GitHub Pages Setup (Frontend)

The static files in this folder (`index.html`, `app.js`, `style.css`) are deployed to GitHub Pages automatically.

### Prerequisites
- GitHub Pages enabled in your repo settings
- Choose: **Source** → Branch: `master`, Folder: `/ (root)` or `/docs`

### How It Works
1. GitHub Pages serves the `docs/` folder as your website
2. Users access the webpage at: `https://sahandamith.github.io/chess_coach/`
3. The UI loads and displays the analysis interface

## Backend API Setup (Chess Analysis)

The Chess Coach app requires a **Python backend** running somewhere to perform chess analysis with Stockfish.

### Option 1: Local Development
```bash
# From the repo root
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in your browser. The app will work because the frontend defaults to `http://localhost:8000` as the API endpoint.

### Option 2: Production Deployment

You need to deploy `main.py` (the FastAPI backend) to a service that supports Python/ASGI:

**Recommended Services:**
- **Railway.app** (recommended — easiest)
- **Render.com** (was previously used)
- **Fly.io**
- **Heroku** (deprecated but still works)
- **PythonAnywhere**
- **AWS Lambda** (with API Gateway)

### Configuring the Frontend to Use Your Backend

After deploying the backend to a service, you need to tell the frontend where to find it.

1. **Option A: Update `docs/index.html`** (persistent, for all users)
   - Add this before the `<script src="./app.js">` line:
   ```html
   <script>
     window.API_BASE = 'https://your-backend-url.com';
   </script>
   ```
   Example: `https://chess-coach-api.railway.app`

2. **Option B: Configure at Runtime** (for testing)
   - Open your browser console (F12)
   - Run: `window.API_BASE = 'https://your-backend-url.com'`
   - Reload the page

### Example: Deploy to Railway

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and create project:**
   ```bash
   railway login
   railway init
   ```

3. **Set environment variables:**
   ```bash
   railway variables set STOCKFISH_PATH=/app/.stockfish/stockfish-ubuntu-latest-x86_64
   ```

4. **Deploy:**
   ```bash
   railway up
   ```

5. **Get your backend URL** from Railway dashboard (something like `https://chess-coach-api.railway.app`)

6. **Update `docs/index.html`** with your backend URL:
   ```html
   <script>
     window.API_BASE = 'https://chess-coach-api.railway.app';
   </script>
   ```

7. **Commit and push** — GitHub Pages will auto-deploy

## Architecture

```
User Browser (GitHub Pages)
    ↓ (loads HTML/JS)
https://sahandamith.github.io/chess_coach/
    ↓ (API calls to)
Your Backend (Railway/Render/etc.)
    ↓ (runs analysis with Stockfish)
Returns JSON results
```

## Files

| Folder | Purpose |
|--------|---------|
| `docs/` | Static frontend files (served by GitHub Pages) |
| `static/` | Source files for static content (edit these) |
| `main.py` | FastAPI backend (deploy this elsewhere) |
| `chess_engine/` | Chess analysis engine (required by backend) |
| `local/` | Desktop GUI (optional) |

## Troubleshooting

**"Backend not configured" error:**
- The frontend can't reach your backend API
- Make sure `window.API_BASE` is set correctly in `docs/index.html`
- Verify your backend is running and accessible

**"Invalid JSON" or "Server error" messages:**
- Check that your backend is running
- Open browser console (F12) to see the exact error
- Verify the API endpoint is correct

**CORS errors:**
- Your backend's CORS settings may be too restrictive
- In `main.py`, ensure the backend allows requests from your GitHub Pages URL
