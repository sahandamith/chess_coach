"""
Chess Coach Web API – FastAPI app for game analysis and mistake review.
Designed to run on any ASGI host.
"""
import os
import sys
import io
import json
import uuid
import threading
import time
from typing import Any, Dict, List, Optional

# Run from repo root so we can import chess_engine
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import chess
import chess.engine
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Chess Coach API", version="1.0.0")

# Mount static files (HTML, JS, CSS)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

#
# Analysis job store (so the web UI can stream live logs)
#
_ANALYSIS_JOBS: Dict[str, Dict[str, Any]] = {}
_ANALYSIS_JOBS_LOCK = threading.Lock()
_STDIO_LOCK = threading.Lock()  # redirecting sys.stdout/sys.stderr is process-wide


def _job_append_log(job_id: str, line: str) -> None:
    line = (line or "").rstrip("\r")
    if not line:
        return
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if not job:
            return
        logs: List[str] = job.setdefault("logs", [])
        logs.append(line)
        # Prevent unbounded growth in long sessions
        if len(logs) > 4000:
            del logs[:2000]


def _job_update_last_log(job_id: str, line: str) -> None:
    """Replace the last log line with this line if it was a progress line (same-line update)."""
    line = (line or "").strip()
    if not line:
        return
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if not job:
            return
        logs: List[str] = job.setdefault("logs", [])
        if not logs:
            logs.append(line)
            return
        last = logs[-1]
        if (last.startswith("Analyzed move ") or last.startswith("Computing detail ")
                or last.startswith("Analyzing game ")):
            logs[-1] = line
        else:
            logs.append(line)


class _JobLogStream:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self._buf = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buf += s
        # Handle \r: update same line in job logs (e.g. "Analyzed move 5/40\r" replaces last progress line)
        while "\r" in self._buf:
            before, self._buf = self._buf.split("\r", 1)
            _job_update_last_log(self.job_id, before)
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            _job_append_log(self.job_id, line)
        return len(s)

    def flush(self) -> None:
        if self._buf:
            _job_append_log(self.job_id, self._buf)
            self._buf = ""


def _background_mistake_pv(job_id: str, engine_path: str) -> None:
    """Compute mistake PV/evals in background and update job result in place (full quality)."""
    engine = None
    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        engine.configure({"Hash": 16})
        with _ANALYSIS_JOBS_LOCK:
            job = _ANALYSIS_JOBS.get(job_id)
            if not job or job.get("status") != "done":
                return
            mistakes = (job.get("result") or {}).get("mistakes") or []
        for i, m in enumerate(mistakes):
            fen_before = m.get("position_before_fen")
            fen_after = m.get("position_after_fen")
            move_uci = m.get("move_played_uci") or ""
            if not fen_before or not fen_after or not move_uci:
                continue
            try:
                pv_data = compute_mistake_pv(
                    engine, fen_before, fen_after, move_uci, time_limit=1.0
                )
                with _ANALYSIS_JOBS_LOCK:
                    job = _ANALYSIS_JOBS.get(job_id)
                    if not job or not job.get("result"):
                        return
                    mis = job["result"].get("mistakes")
                    if mis and i < len(mis):
                        mis[i]["continuation_moves"] = pv_data.get("continuation_moves")
                        mis[i]["continuation_evals"] = pv_data.get("continuation_evals")
                        mis[i]["best_moves"] = pv_data.get("best_moves")
                        mis[i]["best_evals"] = pv_data.get("best_evals")
                        mis[i]["start_eval"] = pv_data.get("start_eval")
            except Exception:
                pass
    finally:
        if engine is not None:
            try:
                engine.quit()
            except Exception:
                pass


def _run_analysis_job(job_id: str, pgn_string: str) -> None:
    from chess_engine.analyzer import ChessAnalyzer

    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = time.time()

    engine_path = get_stockfish_path()
    analyzer = None

    # Capture stdout/stderr so the browser can show the same progress as the terminal.
    with _STDIO_LOCK:
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = _JobLogStream(job_id)  # type: ignore[assignment]
        sys.stderr = _JobLogStream(job_id)  # type: ignore[assignment]
        try:
            analyzer = ChessAnalyzer(engine_path, move_time_ms=400)
            analyzer.open_engine()

            if not analyzer.load_pgn_string(pgn_string):
                raise ValueError("Invalid PGN")

            analyzer.analyze_game()
            analyzer.analyze_mistakes()

            # Return immediately with game + mistakes (no PV yet); PV computed in background
            mistake_list = analyzer.get_mistake_analyses()
            mistakes = [serialize_mistake(m) for m in mistake_list]
            results = analyzer.get_analysis_results()
            evals = []
            for r in results:
                evals.append({
                    "fen": r.get("fen"),
                    "eval": r.get("eval") if isinstance(r.get("eval"), (int, float)) else None,
                    "move_san": r.get("move_san"),
                    "move_uci": r.get("move_uci"),
                    "is_white_move": r.get("is_white_move"),
                    "mistake_category": r.get("mistake_category"),
                })

            game = analyzer.game
            headers = game.headers if game else {}
            result_payload = {
                "game": {
                    "white": headers.get("White", "?"),
                    "black": headers.get("Black", "?"),
                    "result": headers.get("Result", "?"),
                },
                "positions": evals,
                "mistakes": mistakes,
            }

            with _ANALYSIS_JOBS_LOCK:
                job = _ANALYSIS_JOBS.get(job_id)
                if job:
                    job["status"] = "done"
                    job["result"] = result_payload
                    job["finished_at"] = time.time()
            # Compute mistake PVs in background (full quality); result is updated in place
            threading.Thread(
                target=_background_mistake_pv,
                args=(job_id, engine_path),
                daemon=True,
            ).start()
        except Exception as e:
            with _ANALYSIS_JOBS_LOCK:
                job = _ANALYSIS_JOBS.get(job_id)
                if job:
                    job["status"] = "error"
                    job["error"] = str(e)
                    job["finished_at"] = time.time()
        finally:
            try:
                if analyzer is not None:
                    analyzer.close_engine()
            except Exception:
                pass
            try:
                sys.stdout.flush()  # type: ignore[union-attr]
                sys.stderr.flush()  # type: ignore[union-attr]
            except Exception:
                pass
            sys.stdout, sys.stderr = old_out, old_err


def get_stockfish_path():
    """Resolve Stockfish executable path."""
    # Try environment variable first (for Render/production)
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    # Fallback to PATH (works in Docker and local systems)
    return "stockfish"


def serialize_move(m):
    """Convert Move object or string to UCI string for JSON."""
    if m is None:
        return None
    if hasattr(m, "uci"):
        return m.uci()
    return str(m) if isinstance(m, str) else None


def serialize_best_moves(best_moves):
    """Make best_moves / variation structures JSON-serializable."""
    if not best_moves:
        return []
    out = []
    for b in best_moves:
        move = b.get("move")
        variation = b.get("variation") or []
        out.append({
            "move": serialize_move(move),
            "move_uci": b.get("move_uci") or serialize_move(move),
            "move_san": b.get("move_san"),
            "eval": b.get("eval"),
            "depth": b.get("depth"),
            "variation": [
                {
                    "move": serialize_move(v.get("move")),
                    "move_uci": v.get("move_uci"),
                    "move_san": v.get("move_san"),
                }
                for v in variation
            ],
        })
    return out


def _score_from_info(info):
    """Extract centipawn eval from engine analyse result (handles list or single dict)."""
    if info is None:
        return None
    inf = info[0] if isinstance(info, list) and info else info
    if not isinstance(inf, dict) or "score" not in inf:
        return None
    try:
        score = inf["score"].white().score(mate_score=10000)
        return int(score) if score is not None else None
    except (TypeError, AttributeError):
        return None


def get_evals_for_fens(engine, fens, time_limit=0.2):
    """Run engine on each FEN and return list of centipawn evals (White's perspective)."""
    evals = []
    for fen in fens:
        if not fen:
            evals.append(None)
            continue
        try:
            board = chess.Board(fen)
            info = engine.analyse(board, chess.engine.Limit(time=time_limit))
            score = _score_from_info(info)
            evals.append(score)
        except Exception:
            evals.append(None)
    return evals


# At least 10 full moves (20 plies) for mistake and best-alternative PVs
MIN_PV_PLIES = 22  # request 22 plies so we reliably get at least 10 full moves


def get_pv_from_fen(engine, fen, time_limit=0.4, min_depth=0):
    """Analyze a FEN position and return PV moves with evals.
    Use min_depth > 0 to get longer PVs; engine stops when time or depth is reached.
    """
    if not fen:
        return {"variation": [], "evals": []}
    
    try:
        board = chess.Board(fen)
        limit = (
            chess.engine.Limit(time=time_limit, depth=min_depth)
            if min_depth > 0
            else chess.engine.Limit(time=time_limit)
        )
        info = engine.analyse(board, limit, multipv=1)
        info_list = info if isinstance(info, list) else [info]
        if not info_list or "pv" not in info_list[0] or len(info_list[0]["pv"]) == 0:
            return {"variation": [], "evals": []}
        pv_moves = info_list[0]["pv"]
        variation = []
        fens = []
        temp_board = board.copy()
        
        # Build variation with moves and FENs
        for move in pv_moves:
            if move not in temp_board.legal_moves:
                break
            try:
                variation.append({
                    "move": move.uci(),
                    "move_uci": move.uci(),
                    "move_san": temp_board.san(move)
                })
                temp_board.push(move)
                fens.append(temp_board.fen())
            except (ValueError, AssertionError):
                break
        
        # Get evals for each position in the PV
        evals = get_evals_for_fens(engine, fens, time_limit=0.15)
        
        return {
            "variation": variation,
            "evals": evals
        }
    except Exception as e:
        print(f"Error getting PV from FEN: {e}")
        return {"variation": [], "evals": []}


def _uci_from_variation_item(v):
    """Get UCI string from a variation item (may have move object or move_uci)."""
    uci = v.get("move_uci")
    if uci:
        return uci if isinstance(uci, str) else (getattr(uci, "uci", lambda: None)() or str(uci))
    m = v.get("move")
    if m is None:
        return None
    return m.uci() if hasattr(m, "uci") else str(m)


def build_continuation_fens(mistake):
    """Build list of FENs along the mistake continuation (after mistake, then each reply)."""
    after_fen = mistake.get("position_after_fen")
    if not after_fen:
        return []
    cont = mistake.get("continuation_moves") or []
    if not cont or not cont[0].get("variation"):
        return [after_fen]
    fens = [after_fen]
    board = chess.Board(after_fen)
    for v in cont[0]["variation"]:
        uci = _uci_from_variation_item(v)
        if not uci:
            continue
        try:
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                board.push(move)
                fens.append(board.fen())
        except (ValueError, AssertionError):
            pass
    return fens


def build_best_fens(mistake):
    """Build list of FENs along the best line (after best move, then each in variation)."""
    before_fen = mistake.get("position_before_fen")
    if not before_fen:
        return []
    best_list = mistake.get("best_moves") or []
    if not best_list or not best_list[0].get("variation"):
        return []
    board = chess.Board(before_fen)
    fens = []
    for v in best_list[0]["variation"]:
        uci = _uci_from_variation_item(v)
        if not uci:
            continue
        try:
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                board.push(move)
                fens.append(board.fen())
        except (ValueError, AssertionError):
            pass
    return fens


def serialize_mistake(mistake):
    """Convert one mistake analysis to a JSON-safe dict."""
    mp = mistake.get("move_played")
    move_played_uci = mp.uci() if hasattr(mp, "uci") else (str(mp) if mp else "")
    out = {
        "position_index": mistake.get("position_index"),
        "chess_move": mistake.get("chess_move"),
        "severity": mistake.get("severity"),
        "phase": mistake.get("phase"),
        "move_played_san": mistake.get("move_played_san"),
        "move_played_uci": move_played_uci,
        "position_before_fen": mistake.get("position_before_fen"),
        "position_after_fen": mistake.get("position_after_fen"),
        "position_fen": mistake.get("position_fen"),
        "prev_eval": mistake.get("prev_eval"),
        "curr_eval": mistake.get("curr_eval"),
        "eval_drop": mistake.get("eval_drop"),
        "primary_category": mistake.get("primary_category"),
        "details": mistake.get("details"),
        "best_moves": serialize_best_moves(mistake.get("best_moves") or []),
        "continuation_moves": [
            {"variation": serialize_best_moves(c.get("variation") or [])}
            for c in (mistake.get("continuation_moves") or [])
        ],
    }
    if mistake.get("continuation_evals") is not None:
        out["continuation_evals"] = mistake["continuation_evals"]
    if mistake.get("best_evals") is not None:
        out["best_evals"] = mistake["best_evals"]
    if mistake.get("start_eval") is not None:
        out["start_eval"] = mistake["start_eval"]
    return out


def compute_mistake_pv(engine, fen_before, fen_after, move_played_uci, time_limit=0.5):
    """
    Compute continuation and best PV for one mistake. Used during first analysis
    so mistake detail can show boards immediately when user clicks.
    Returns dict with continuation_moves, continuation_evals, best_moves, best_evals, start_eval.
    """
    if not fen_before or not fen_after:
        return {
            "continuation_moves": [{"variation": []}],
            "continuation_evals": [],
            "best_moves": [{"variation": []}],
            "best_evals": [],
            "start_eval": None,
        }
    move_uci = (move_played_uci or "").strip() if isinstance(move_played_uci, str) else (
        getattr(move_played_uci, "uci", lambda: None)() or ""
    )
    try:
        after_result = get_pv_from_fen(engine, fen_after, time_limit=time_limit, min_depth=MIN_PV_PLIES)
        continuation_variation = []
        continuation_evals = []
        if move_uci:
            try:
                board_before = chess.Board(fen_before)
                move = chess.Move.from_uci(move_uci)
                if move in board_before.legal_moves:
                    continuation_variation.append({
                        "move": move_uci,
                        "move_uci": move_uci,
                        "move_san": board_before.san(move)
                    })
                    board_after = chess.Board(fen_after)
                    info = engine.analyse(board_after, chess.engine.Limit(time=0.2))
                    continuation_evals.append(_score_from_info(info))
            except Exception:
                pass
        continuation_variation.extend(after_result["variation"])
        continuation_evals.extend(after_result["evals"])

        before_result = get_pv_from_fen(engine, fen_before, time_limit=time_limit, min_depth=MIN_PV_PLIES)
        best_variation = before_result["variation"]
        best_evals = before_result["evals"]

        start_eval = None
        try:
            board_start = chess.Board(fen_before)
            info_start = engine.analyse(board_start, chess.engine.Limit(time=0.2))
            start_eval = _score_from_info(info_start)
        except Exception:
            pass

        return {
            "continuation_moves": [{"variation": continuation_variation}],
            "continuation_evals": continuation_evals,
            "best_moves": [{"variation": best_variation}],
            "best_evals": best_evals,
            "start_eval": start_eval,
        }
    except Exception as e:
        print(f"compute_mistake_pv error: {e}")
        return {
            "continuation_moves": [{"variation": []}],
            "continuation_evals": [],
            "best_moves": [{"variation": []}],
            "best_evals": [],
            "start_eval": None,
        }


class AnalyzeRequest(BaseModel):
    pgn: str


class AnalyzeMistakeRequest(BaseModel):
    pgn: str
    mistake_index: int


class AnalyzeFensRequest(BaseModel):
    fen_after_mistake: str  # For mistake continuation board
    fen_before_mistake: str  # For best alternative board
    move_played_uci: str  # The mistake move UCI


class FeedbackRequest(BaseModel):
    comment: str
    email: Optional[str] = None


def _feedback_file_path() -> str:
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError:
        pass
    return os.path.join(data_dir, "feedback.jsonl")


@app.get("/api/feedback")
async def get_feedback():
    """
    Return all feedback entries for public display (comment + date only, no email).
    Newest first.
    """
    path = _feedback_file_path()
    entries: List[Dict[str, Any]] = []
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        entries.append({
                            "ts": obj.get("ts"),
                            "comment": (obj.get("comment") or "").strip(),
                        })
                    except (json.JSONDecodeError, TypeError):
                        continue
        except OSError:
            pass
    entries.sort(key=lambda x: (x.get("ts") or 0), reverse=True)
    return {"feedback": entries}


@app.get("/feedback")
async def feedback_page():
    """Serve the feedback/suggestions page."""
    path = os.path.join(STATIC_DIR, "feedback.html")
    if os.path.isfile(path):
        return FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    raise HTTPException(status_code=404, detail="Feedback page not found")


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Store user feedback/suggestions for future improvements.
    Appends to a local file (one JSON object per line).
    """
    comment = (request.comment or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="Comment is required")
    email = (request.email or "").strip() or None
    path = _feedback_file_path()
    entry = {
        "ts": time.time(),
        "comment": comment[:2000],
        "email": email[:256] if email else None,
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not save feedback: {e}")
    return {"ok": True, "message": "Thank you for your feedback."}


@app.post("/api/analyze-job")
async def analyze_job(request: AnalyzeRequest):
    """
    Start an analysis job and stream logs via GET /api/analyze-job/{job_id}.
    This lets the web UI show the same progress lines you see in the terminal.
    """
    pgn_string = (request.pgn or "").strip()
    if not pgn_string:
        raise HTTPException(status_code=400, detail="PGN string is required")

    job_id = uuid.uuid4().hex
    with _ANALYSIS_JOBS_LOCK:
        _ANALYSIS_JOBS[job_id] = {
            "status": "queued",
            "logs": [],
            "result": None,
            "error": None,
            "created_at": time.time(),
        }

    t = threading.Thread(target=_run_analysis_job, args=(job_id, pgn_string), daemon=True)
    t.start()

    return {"job_id": job_id}


@app.get("/api/analyze-job/{job_id}")
async def analyze_job_status(job_id: str, since: int = 0):
    """
    Poll job status and fetch logs incrementally.
    Pass `since` as the last log index you’ve already received.
    """
    with _ANALYSIS_JOBS_LOCK:
        job = _ANALYSIS_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Unknown job id")

        logs: List[str] = job.get("logs") or []
        next_index = len(logs)

        payload: Dict[str, Any] = {
            "job_id": job_id,
            "status": job.get("status"),
            "logs": list(logs),
            "next": next_index,
            "error": job.get("error"),
        }

        if job.get("status") == "done":
            payload["result"] = job.get("result")

        return payload


@app.get("/")
async def index():
    """Serve the single-page app. Disable caching so users always get latest HTML."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "Chess Coach API. Use POST /api/analyze with {\"pgn\": \"...\"}."}


@app.get("/health")
async def health():
    """Health check for load balancers."""
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Analyze a game from PGN: run engine analysis and mistake detection.
    Returns game info, evals per position, and list of mistakes with FENs and best lines.
    """
    from chess_engine.analyzer import ChessAnalyzer

    pgn_string = (request.pgn or "").strip()
    if not pgn_string:
        raise HTTPException(status_code=400, detail="PGN string is required")

    engine_path = get_stockfish_path()
    try:
        analyzer = ChessAnalyzer(engine_path, move_time_ms=200)
        analyzer.open_engine()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Engine unavailable: {str(e)}. Set STOCKFISH_PATH or install Stockfish."
        )

    try:
        if not analyzer.load_pgn_string(pgn_string):
            raise HTTPException(status_code=400, detail="Invalid PGN")
        analyzer.analyze_game()
        analyzer.analyze_mistakes()
    except HTTPException:
        raise
    except Exception as e:
        # Try to close engine, but don't fail if it's already dead
        try:
            analyzer.close_engine()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    mistake_analyses = analyzer.get_mistake_analyses()
    engine = analyzer.engine
    for m in mistake_analyses:
        fen_before = m.get("position_before_fen")
        fen_after = m.get("position_after_fen")
        mp = m.get("move_played")
        move_uci = mp.uci() if hasattr(mp, "uci") else (str(mp) if mp else "")
        if fen_before and fen_after and move_uci:
            pv_data = compute_mistake_pv(engine, fen_before, fen_after, move_uci, time_limit=0.5)
            m["continuation_moves"] = pv_data.get("continuation_moves")
            m["continuation_evals"] = pv_data.get("continuation_evals")
            m["best_moves"] = pv_data.get("best_moves")
            m["best_evals"] = pv_data.get("best_evals")
            m["start_eval"] = pv_data.get("start_eval")
    mistakes = [serialize_mistake(m) for m in mistake_analyses]
    results = analyzer.get_analysis_results()
    evals = []
    for r in results:
        evals.append({
            "fen": r.get("fen"),
            "eval": r.get("eval") if isinstance(r.get("eval"), (int, float)) else None,
            "move_san": r.get("move_san"),
            "move_uci": r.get("move_uci"),
            "is_white_move": r.get("is_white_move"),
            "mistake_category": r.get("mistake_category"),
        })

    try:
        analyzer.close_engine()
    except Exception:
        pass  # Engine might already be closed

    game = analyzer.game
    headers = game.headers if game else {}
    return {
        "game": {
            "white": headers.get("White", "?"),
            "black": headers.get("Black", "?"),
            "result": headers.get("Result", "?"),
        },
        "positions": evals,
        "mistakes": mistakes,
    }


@app.post("/api/analyze-mistake-fens")
async def analyze_mistake_fens(request: AnalyzeFensRequest):
    """
    Analyze mistake boards by analyzing only the specific FEN positions.
    Much faster than re-analyzing the entire game.
    """
    engine_path = get_stockfish_path()
    engine = None
    
    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        engine.configure({"Hash": 16})
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Engine unavailable: {str(e)}. Set STOCKFISH_PATH or install Stockfish."
        )

    try:
        # 1. Mistake board: PV from FEN after mistake (at least 10 full moves)
        after_result = get_pv_from_fen(engine, request.fen_after_mistake, time_limit=1.0, min_depth=MIN_PV_PLIES)
        
        # Build continuation: mistake move first, then PV from after mistake
        continuation_variation = []
        continuation_evals = []
        
        # Add the mistake move first
        if request.move_played_uci:
            try:
                board_before = chess.Board(request.fen_before_mistake)
                move = chess.Move.from_uci(request.move_played_uci)
                if move in board_before.legal_moves:
                    continuation_variation.append({
                        "move": request.move_played_uci,
                        "move_uci": request.move_played_uci,
                        "move_san": board_before.san(move)
                    })
                    # Get eval for position after mistake move (this is the position after the mistake)
                    board_after = chess.Board(request.fen_after_mistake)
                    info = engine.analyse(board_after, chess.engine.Limit(time=0.2))
                    continuation_evals.append(_score_from_info(info))
            except Exception as e:
                print(f"Error adding mistake move: {e}")
        
        # Add PV moves from position after mistake
        # Note: after_result["evals"] are evals AFTER each PV move, so they align correctly
        continuation_variation.extend(after_result["variation"])
        continuation_evals.extend(after_result["evals"])
        
        # 2. Best alternative board: PV from FEN before mistake (at least 10 full moves)
        before_result = get_pv_from_fen(engine, request.fen_before_mistake, time_limit=1.0, min_depth=MIN_PV_PLIES)
        
        best_variation = before_result["variation"]
        best_evals = before_result["evals"]
        
        # Get eval for start position (before mistake)
        start_eval = None
        try:
            board_start = chess.Board(request.fen_before_mistake)
            info_start = engine.analyse(board_start, chess.engine.Limit(time=0.2))
            start_eval = _score_from_info(info_start)
        except Exception as e:
            print(f"Error getting start eval: {e}")
        
    except Exception as e:
        try:
            engine.quit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Mistake analysis failed: {str(e)}")
    
    try:
        engine.quit()
    except Exception:
        pass

    return {
        "continuation_moves": [{"variation": continuation_variation}],
        "continuation_evals": continuation_evals,
        "best_moves": [{"variation": best_variation}],
        "best_evals": best_evals,
        "start_eval": start_eval,
    }
