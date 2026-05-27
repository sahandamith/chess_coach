// API Configuration: Set the backend endpoint
// For local development: http://localhost:8000
// For production: Update this to your backend URL (e.g., https://api.yourhost.com)
const API_BASE = window.API_BASE || window.location.origin;

// Define button handler immediately so it exists even if DOMContentLoaded fails
window.startAnalyze = function () {
  if (typeof window.__runAnalyze === 'function') {
    window.__runAnalyze();
  } else {
    alert(
      'Backend not configured.\n\n' +
      'Set window.API_BASE before loading this page.\n\n' +
      'Local development:\n' +
      '1. Open a terminal in the project folder\n' +
      '2. Run: uvicorn main:app --reload --port 8000\n' +
      '3. In your browser open: http://localhost:8000\n\n' +
      'GitHub Pages deployment:\n' +
      'Update API_BASE to your backend URL (e.g., https://api.yourhost.com)\n\n' +
      'For help, press F12 and check the Console tab for errors.'
    );
  }
};

let currentAnalysisData = null;
let currentJobId = null;
let currentPgn = null;
let flatMistakesList = null;
let replayBoard = null;
const replayState = { fens: [], positions: [], index: 0 };
let replayAllEvals = null;

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Parse response as JSON; on failure return undefined or throw with a clear message. */
async function parseJsonResponse(resp, defaultVal = undefined) {
  const text = await resp.text();
  try {
    return text ? JSON.parse(text) : defaultVal;
  } catch (e) {
    if (defaultVal !== undefined) return defaultVal;
    const preview = (text || resp.statusText || 'Empty response').slice(0, 80);
    throw new Error(resp.ok ? `Invalid JSON: ${preview}` : `Server error (${resp.status}): ${preview}`);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('pgn-form');
  const pgnInput = document.getElementById('pgn');
  const analyzeBtn = document.getElementById('analyze-btn');
  const resultDiv = document.getElementById('result');
  const analysisStatusDiv = document.getElementById('analysis-status');
  const mistakesDiv = document.getElementById('mistakes');
  const positionsDiv = document.getElementById('positions');
  const replayCard = document.getElementById('replay-card');
  const replayInfoEl = document.getElementById('replay-info');
  const replayPrevBtn = document.getElementById('replay-prev');
  const replayResetBtn = document.getElementById('replay-reset');
  const replayNextBtn = document.getElementById('replay-next');

  function formatEval(evalCp) {
    const n = evalCp != null ? Number(evalCp) : null;
    if (n == null || isNaN(n)) return '—';
    const pawns = n / 100.0;
    return pawns.toFixed(1);
  }

  // Eval bar: white at bottom, black at top; center = 0; range -8 to +8 pawns
  function evalToPercent(evalCp) {
    if (evalCp == null || isNaN(evalCp)) return 50;
    const pawns = evalCp / 100.0;
    const clamped = Math.max(-8, Math.min(8, pawns));
    return 50 + (clamped / 8) * 50; // 0 -> 50%, +8 -> 100%, -8 -> 0%
  }

  function setEvalBar(barWrapEl, evalCp) {
    if (!barWrapEl) return;
    const whiteEl = barWrapEl.querySelector('.eval-bar-white');
    const blackEl = barWrapEl.querySelector('.eval-bar-black');
    const labelEl = barWrapEl.querySelector('.eval-bar-label');
    const percent = evalToPercent(evalCp);
    if (whiteEl) whiteEl.style.height = percent + '%';
    if (blackEl) {
      blackEl.style.flex = 'none';
      blackEl.style.height = (100 - percent) + '%';
    }
    if (labelEl) {
      if (evalCp == null || isNaN(evalCp)) labelEl.textContent = '0';
      else {
        const pawns = evalCp / 100;
        const clamped = Math.max(-8, Math.min(8, pawns));
        labelEl.textContent = (clamped >= 0 ? '+' : '') + clamped.toFixed(1);
      }
    }
  }

  // chess.js 0.10 move() expects { from, to } or (from, to), not UCI string
  function uciToMove(uci) {
    if (!uci || typeof uci !== 'string') return null;
    uci = uci.trim();
    if (uci.length >= 4) {
      const from = uci.slice(0, 2);
      const to = uci.slice(2, 4);
      const promotion = uci.length > 4 ? uci[4].toLowerCase() : undefined;
      return promotion ? { from: from, to: to, promotion: promotion } : { from: from, to: to };
    }
    return null;
  }

  function applyUci(chess, uci) {
    const move = uciToMove(typeof uci === 'string' ? uci : (uci && (uci.uci ? uci.uci() : uci.move_uci || uci.move)));
    if (!move) return null;
    try {
      return chess.move(move);
    } catch (e) {
      return null;
    }
  }

  function updateReplayInfo() {
    const { fens, positions, index } = replayState;
    if (!fens.length) return;
    const replayPvMovesEl = document.getElementById('replay-pv-moves');

    // Backend sends positions[0]=start (no move), positions[1]=after white's 1st, positions[2]=after black's 1st, ...
    if (positions.length > 1 && positions[1] && positions[1].fen && (!positions[1].move_san || !positions[1].move_san.trim()) && positions[1].move_uci) {
      try {
        const c = new Chess();
        c.load(positions[0] && positions[0].fen ? positions[0].fen : START_FEN);
        const mv = applyUci(c, positions[1].move_uci);
        if (mv && mv.san) positions[1].move_san = mv.san;
      } catch (e) { /* ignore */ }
    }

    // Move list: row 1 = positions[1] (white), positions[2] (black); row 2 = [3],[4]; ...
    if (replayPvMovesEl) {
      replayPvMovesEl.innerHTML = '';
      const cols = document.createElement('div');
      cols.className = 'moves-columns';
      const left = document.createElement('div');
      left.className = 'moves-table';
      const right = document.createElement('div');
      right.className = 'moves-table';
      cols.appendChild(left);
      cols.appendChild(right);

      const fullMoves = Math.floor((positions.length - 1) / 2);
      for (let m = 0; m < fullMoves; m++) {
        const row = document.createElement('div');
        row.className = 'moves-row';
        const numSpan = document.createElement('span');
        numSpan.className = 'move-num';
        numSpan.textContent = String(m + 1) + '.';
        row.appendChild(numSpan);

        const whitePos = positions[2 * m + 1];
        const blackPos = positions[2 * m + 2];

        if (whitePos) {
          const whiteMoveIdx = 2 * m + 1;
          let whiteMoveSan = whitePos.move_san || (whitePos.move_uci ? String(whitePos.move_uci) : '');
          if ((!whiteMoveSan || !whiteMoveSan.trim()) && whitePos.move_uci) {
            try {
              const c = new Chess();
              c.load(positions[0] && positions[0].fen ? positions[0].fen : START_FEN);
              for (let i = 0; i < 2 * m; i++) applyUci(c, positions[i + 1].move_uci);
              const mv = applyUci(c, whitePos.move_uci);
              if (mv && mv.san) whiteMoveSan = mv.san;
            } catch (e) { /* ignore */ }
          }
          if (whiteMoveSan && whiteMoveSan.trim()) {
            const whiteSpan = document.createElement('span');
            whiteSpan.className = 'pv-move move-white' + (whiteMoveIdx === index ? ' current' : '');
            whiteSpan.textContent = whiteMoveSan;
            whiteSpan.dataset.index = String(whiteMoveIdx);
            whiteSpan.addEventListener('click', () => {
              replayState.index = whiteMoveIdx;
              if (replayBoard) replayBoard.position(replayState.fens[whiteMoveIdx]);
              updateReplayInfo();
            });
            row.appendChild(whiteSpan);
          } else {
            const blank = document.createElement('span');
            blank.className = 'move-blank';
            row.appendChild(blank);
          }
        } else {
          const blank = document.createElement('span');
          blank.className = 'move-blank';
          row.appendChild(blank);
        }

        if (blackPos) {
          const blackMoveIdx = 2 * m + 2;
          let blackMoveSan = blackPos.move_san || (blackPos.move_uci ? String(blackPos.move_uci) : '');
          if ((!blackMoveSan || !blackMoveSan.trim()) && blackPos.move_uci) {
            try {
              const c = new Chess();
              c.load(positions[0] && positions[0].fen ? positions[0].fen : START_FEN);
              for (let i = 0; i < 2 * m + 1; i++) applyUci(c, positions[i + 1].move_uci);
              const mv = applyUci(c, blackPos.move_uci);
              if (mv && mv.san) blackMoveSan = mv.san;
            } catch (e) { /* ignore */ }
          }
          if (blackMoveSan && blackMoveSan.trim()) {
            const blackSpan = document.createElement('span');
            blackSpan.className = 'pv-move move-black' + (blackMoveIdx === index ? ' current' : '');
            blackSpan.textContent = blackMoveSan;
            blackSpan.dataset.index = String(blackMoveIdx);
            blackSpan.addEventListener('click', () => {
              replayState.index = blackMoveIdx;
              if (replayBoard) replayBoard.position(replayState.fens[blackMoveIdx]);
              updateReplayInfo();
            });
            row.appendChild(blackSpan);
          } else {
            const blank = document.createElement('span');
            blank.className = 'move-blank';
            row.appendChild(blank);
          }
        } else {
          const blank = document.createElement('span');
          blank.className = 'move-blank';
          row.appendChild(blank);
        }

        (m % 2 === 0 ? left : right).appendChild(row);
      }
      replayPvMovesEl.appendChild(cols);
    }

    const currentPos = positions[index];
    setEvalBar(document.getElementById('replay-eval-bar-wrap'), currentPos && currentPos.eval != null ? currentPos.eval : null);
    if (replayPrevBtn) replayPrevBtn.disabled = index <= 0;
    if (replayNextBtn) replayNextBtn.disabled = index >= fens.length - 1;

    const plotCanvas = document.getElementById('replay-eval-plot');
    if (plotCanvas && replayAllEvals && Array.isArray(replayAllEvals)) {
      const mistakes = (currentAnalysisData && currentAnalysisData.mistakes) || [];
      drawSingleEvalPlot(plotCanvas, replayAllEvals, index, mistakes);
    }
  }

  let isAnalyzing = false;

  async function analyze() {
    if (isAnalyzing) {
      console.log('Analysis already in progress, ignoring duplicate call');
      return;
    }
    
    if (typeof console !== 'undefined' && console.log) console.log('Analyze function called');
    const pgn = (pgnInput && pgnInput.value) ? pgnInput.value.trim() : '';
    if (!pgn) {
      alert('Please paste a PGN first');
      return;
    }

    isAnalyzing = true;
    if (analyzeBtn) {
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = 'Analyzing...';
    }
    if (resultDiv) resultDiv.textContent = 'Analyzing...';
    if (analysisStatusDiv) {
      analysisStatusDiv.style.display = 'block';
      analysisStatusDiv.textContent = 'Loading PGN and initializing engine...';
    }
    if (mistakesDiv) mistakesDiv.innerHTML = '';
    var detailsEl = document.getElementById('mistake-details');
    if (detailsEl) detailsEl.innerHTML = '';
    if (positionsDiv) positionsDiv.innerHTML = '';
    if (replayCard) replayCard.style.display = 'none';

    try {
      // Start analysis job so we can stream progress (moves analyzed)
      const analyzeColor = document.getElementById('analyze-color')?.value || 'white';
      const startResp = await fetch(`${API_BASE}/api/analyze-job`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pgn, analyze_color: analyzeColor }),
      });
      const startData = await parseJsonResponse(startResp, {});
      if (!startResp.ok) {
        const errorMsg = 'Error: ' + (startData.detail || startResp.statusText);
        resultDiv.textContent = errorMsg;
        if (analysisStatusDiv) analysisStatusDiv.textContent = 'Analysis failed: ' + errorMsg;
        return;
      }
      const job_id = startData.job_id;
      if (!job_id) {
        resultDiv.textContent = 'Error: No job_id in response.';
        return;
      }
      let since = 0;
      let allLogs = [];
      const pollIntervalMs = 400;

      function updateStatusFromLogs(logs) {
        if (!analysisStatusDiv) return;
        if (!logs.length) {
          analysisStatusDiv.textContent = 'Analyzing game...';
          return;
        }
        let lastMoveProgress = null;
        for (let i = logs.length - 1; i >= 0; i--) {
          const m = logs[i].match(/Analyzed move ([\d.]+)\/(\d+)/);
          if (m) {
            lastMoveProgress = { current: parseFloat(m[1]), total: parseInt(m[2], 10) };
            break;
          }
        }
        const analyzingMistakes = logs.some(l => l.indexOf('Analyzing mistakes') !== -1);
        const complete = logs.some(l => l.indexOf('Analysis complete') !== -1);
        const foundMistakes = logs.find(l => /Found \d+ mistakes?\./.test(l));
        const detailProgress = (() => {
          for (let i = logs.length - 1; i >= 0; i--) {
            const match = logs[i].match(/Computing detail for mistake (\d+)\/(\d+)/);
            if (match) return { current: parseInt(match[1], 10), total: parseInt(match[2], 10) };
          }
          return null;
        })();
        let text = '';
        if (detailProgress) {
          text = `Computing detail for mistake ${detailProgress.current} of ${detailProgress.total}`;
          if (foundMistakes) text += '\n' + foundMistakes.trim();
        } else if (lastMoveProgress) {
          const cur = lastMoveProgress.current;
          text = `Move ${cur % 1 === 0 ? Math.round(cur) : cur.toFixed(1)} of ${lastMoveProgress.total}`;
          if (analyzingMistakes) text += '\nAnalyzing mistakes...';
          else if (complete) text += '\nAnalysis complete.';
          if (foundMistakes) text += '\n' + foundMistakes.trim();
        } else if (analyzingMistakes) {
          text = 'Analyzing mistakes...';
          if (foundMistakes) text += '\n' + foundMistakes.trim();
        } else {
          // Show progress from API
          text = 'Analyzing game...';
          if (window.__lastProgress) {
            const p = window.__lastProgress;
            text = `Analyzed ${p.move_num}/${p.total_moves}: ${p.move_san}`;
          }
        }
        analysisStatusDiv.textContent = text;
      }

      const poll = () =>
        fetch(`${API_BASE}/api/analyze-job/${job_id}?since=${since}`)
          .then(async (r) => ({ r, payload: await parseJsonResponse(r, null) }))
          .then(({ r, payload }) => {
            if (payload == null) return;
            const fullLogs = payload.logs || [];
            since = payload.next != null ? payload.next : since;
            allLogs = fullLogs;
            // Capture progress info from API response
            if (payload.progress) {
              window.__lastProgress = payload.progress;
            }
            updateStatusFromLogs(allLogs);
            if (payload.status === 'done') {
              clearInterval(intervalId);
              if (analysisStatusDiv) {
                analysisStatusDiv.textContent = 'Analysis complete! Rendering results...';
                analysisStatusDiv.style.display = 'none';
              }
              const data = payload.result;
              if (!data) {
                resultDiv.textContent = 'Analysis finished but no result received.';
                return;
              }
              currentAnalysisData = data;
              currentJobId = job_id;
              currentPgn = pgn;
              renderResult(data);
              return;
            }
            if (payload.status === 'error') {
              clearInterval(intervalId);
              const errorMsg = payload.error || 'Analysis failed.';
              resultDiv.textContent = errorMsg;
              if (analysisStatusDiv) analysisStatusDiv.textContent = 'Error: ' + errorMsg;
              return;
            }
          })
          .catch((e) => {
            clearInterval(intervalId);
            if (typeof console !== 'undefined' && console.error) console.error('Poll error:', e);
            resultDiv.textContent = 'Error: ' + e.message;
            if (analysisStatusDiv) analysisStatusDiv.textContent = 'Error: ' + e.message;
          });

      const intervalId = setInterval(poll, pollIntervalMs);
      poll();
    } catch (e) {
      if (typeof console !== 'undefined' && console.error) console.error('Exception during analysis:', e);
      if (resultDiv) resultDiv.textContent = 'Error: ' + e.message;
      if (analysisStatusDiv) analysisStatusDiv.textContent = 'Error: ' + e.message;
    } finally {
      isAnalyzing = false;
      if (analyzeBtn) {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze Game';
      }
      // Status div is hidden in the poll callback when status === 'done'; keep visible while polling for progress
    }
  }

  // Wire the real analyze function so startAnalyze() runs it
  window.__runAnalyze = function () { analyze(); };

  function renderResult(data) {
    // Show sections 2, 3, 4 once we have results
    document.querySelectorAll('.section-later').forEach(function (el) {
      el.classList.remove('section-later');
    });

    const game = data.game || {};
    resultDiv.textContent = `${game.white || '?'} vs ${game.black || '?'} (${game.result || '?'})`;

    const positions = data.positions || [];
    // Ensure we always have correct SAN labels (avoid "Move 1" placeholders)
    // Derive SAN from UCI when missing.
    try {
      const chess = new Chess();
      chess.load(START_FEN);
      positions.forEach((p) => {
        const uci = p && p.move_uci ? String(p.move_uci) : null;
        if (uci) {
          const m = applyUci(chess, uci);
          if (m && (!p.move_san || typeof p.move_san !== 'string' || !p.move_san.trim())) {
            p.move_san = m.san;
          }
        }
      });
    } catch (e) {
      // Non-fatal; fallback to server-provided move_san
    }

    // Build replay - backend sends positions[0]=start, positions[1]=after move 1, ...
    if (positions.length > 0 && replayCard) {
      replayState.fens = positions.map(p => p.fen).filter(Boolean);
      replayState.positions = positions;
      replayState.index = 0;
      replayCard.style.display = 'block';
      const boardConfig = {
        position: replayState.fens[0],
        draggable: false,
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
      };
      if (!replayBoard && typeof ChessBoard !== 'undefined') {
        replayBoard = ChessBoard('replay-board', boardConfig);
      } else if (replayBoard) {
        replayBoard.position(replayState.fens[0]);
      }
      setEvalBar(document.getElementById('replay-eval-bar-wrap'), positions[0] && positions[0].eval != null ? positions[0].eval : null);
      replayAllEvals = positions.map(p => (p && p.eval != null ? p.eval : null));
      updateReplayInfo();
    }

    const mistakes = data.mistakes || [];
    renderMistakeSummaryAndList(mistakes);
    renderReplayMistakesMini();
  }

  function renderReplayMistakesMini() {
    const el = document.getElementById('replay-mistakes-mini');
    if (!el) return;
    el.innerHTML = '';
    if (!flatMistakesList || !flatMistakesList.length) {
      el.innerHTML = '<div class="mistakes-empty">No mistakes detected.</div>';
      return;
    }
    const list = document.createElement('div');
    list.className = 'mistake-mini-list';
    flatMistakesList.slice(0, 50).forEach((m, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'mistake-link';
      const label =
        m && m.chess_move != null
          ? `Move ${m.chess_move.toFixed ? m.chess_move.toFixed(1) : m.chess_move}`
          : `#${idx + 1}`;
      btn.textContent = `${label} • ${m.severity || ''} • ${m.move_played_san || m.move_played || ''}`;
      btn.addEventListener('click', () => showMistakeDetails(m, idx));
      list.appendChild(btn);
    });
    el.appendChild(list);
  }

  function drawSingleEvalPlot(canvas, evalsCp, currentIndex, mistakes) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const plotWidth = width - 2 * padding;
    const plotHeight = height - 2 * padding;

    ctx.fillStyle = '#2f3640';
    ctx.fillRect(0, 0, width, height);

    const data = (evalsCp || []).map(v => (v == null || isNaN(v) ? null : v)).filter(v => v != null);
    if (!data.length) return;

    const total = Math.max(evalsCp.length, 2);
    const yMin = -800;
    const yMax = 800;
    const yRange = yMax - yMin;
    const evalToY = (cp) => padding + plotHeight - ((Math.max(-800, Math.min(800, cp)) - yMin) / yRange) * plotHeight;
    const idxToX = (i) => padding + (i / Math.max(total - 1, 1)) * plotWidth;

    const move15Idx = Math.min(30, total - 1);
    const move30Idx = Math.min(60, total - 1);
    ctx.strokeStyle = 'rgba(46, 204, 113, 0.5)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(idxToX(move15Idx), padding);
    ctx.lineTo(idxToX(move15Idx), height - padding);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(231, 76, 60, 0.5)';
    ctx.beginPath();
    ctx.moveTo(idxToX(move30Idx), padding);
    ctx.lineTo(idxToX(move30Idx), height - padding);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.strokeStyle = '#636e72';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();

    ctx.strokeStyle = '#b2bec3';
    ctx.beginPath();
    ctx.moveTo(padding, evalToY(0));
    ctx.lineTo(width - padding, evalToY(0));
    ctx.stroke();

    ctx.strokeStyle = '#81ecec';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < evalsCp.length; i++) {
      const cp = evalsCp[i];
      if (cp == null || isNaN(cp)) continue;
      const x = idxToX(i);
      const y = evalToY(cp);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    const mistakeList = mistakes || [];
    mistakeList.forEach((m) => {
      const posIdx = m.position_index;
      if (posIdx == null || posIdx < 0 || posIdx >= evalsCp.length) return;
      const cp = evalsCp[posIdx];
      if (cp == null || isNaN(cp)) return;
      const x = idxToX(posIdx);
      const y = evalToY(cp);
      const sev = (m.severity || '').toLowerCase();
      if (sev === 'blunder') {
        ctx.strokeStyle = '#E74C3C';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - 6, y - 6);
        ctx.lineTo(x + 6, y + 6);
        ctx.moveTo(x + 6, y - 6);
        ctx.lineTo(x - 6, y + 6);
        ctx.stroke();
      } else if (sev === 'mistake') {
        ctx.fillStyle = '#F39C12';
        ctx.strokeStyle = '#636e72';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
      } else if (sev === 'inaccuracy') {
        ctx.fillStyle = '#a29bfe';
        ctx.strokeStyle = '#636e72';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, y - 6);
        ctx.lineTo(x + 6, y + 5);
        ctx.lineTo(x - 6, y + 5);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
    });

    if (typeof currentIndex === 'number' && currentIndex >= 0) {
      const x = idxToX(Math.min(currentIndex, total - 1));
      ctx.strokeStyle = 'rgba(255, 234, 167, 0.65)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, height - padding);
      ctx.stroke();
    }

    ctx.fillStyle = '#b2bec3';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    for (let cp = -800; cp <= 800; cp += 200) {
      const y = evalToY(cp);
      if (y < padding || y > height - padding) continue;
      const pawns = (cp / 100).toFixed(1);
      ctx.fillText((cp >= 0 ? '+' : '') + pawns, padding - 6, y + 4);
    }
    ctx.save();
    ctx.translate(14, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText('Eval (pawns)', 0, 0);
    ctx.restore();

    const xTickStep = Math.max(1, Math.floor(total / 15));
    ctx.textAlign = 'center';
    ctx.font = '10px sans-serif';
    for (let i = 0; i < total; i += xTickStep) {
      const x = idxToX(i);
      const moveNum = Math.floor(i / 2);
      ctx.fillText(String(moveNum), x, height - padding + 14);
    }
    ctx.fillText('Move', width / 2, height - 4);

    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Opening', padding + (idxToX(move15Idx) - padding) / 2, height - 22);
    ctx.fillText('Middlegame', idxToX(move15Idx) + (idxToX(move30Idx) - idxToX(move15Idx)) / 2, height - 22);
    ctx.fillText('Endgame', idxToX(move30Idx) + (width - padding - idxToX(move30Idx)) / 2, height - 22);

    const legX = width - 130;
    const legY = padding + 6;
    ctx.fillStyle = 'rgba(45, 52, 54, 0.92)';
    ctx.strokeStyle = '#636e72';
    ctx.fillRect(legX, legY, 118, 48);
    ctx.strokeRect(legX, legY, 118, 48);
    ctx.textAlign = 'left';
    ctx.font = '11px sans-serif';
    const iconX = legX + 6;
    const rowH = 16;
    ctx.strokeStyle = '#E74C3C';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(iconX - 4, legY + 6);
    ctx.lineTo(iconX + 4, legY + 14);
    ctx.moveTo(iconX + 4, legY + 6);
    ctx.lineTo(iconX - 4, legY + 14);
    ctx.stroke();
    ctx.fillStyle = '#b2bec3';
    ctx.fillText('Blunder', legX + 26, legY + 14);
    ctx.fillStyle = '#F39C12';
    ctx.strokeStyle = '#636e72';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(iconX, legY + 6 + rowH, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#b2bec3';
    ctx.fillText('Mistake', legX + 26, legY + 14 + rowH);
    ctx.fillStyle = '#a29bfe';
    ctx.strokeStyle = '#636e72';
    ctx.beginPath();
    ctx.moveTo(iconX, legY + 6 + rowH * 2 - 4);
    ctx.lineTo(iconX + 5, legY + 6 + rowH * 2 + 6);
    ctx.lineTo(iconX - 5, legY + 6 + rowH * 2 + 6);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#b2bec3';
    ctx.fillText('Inaccuracy', legX + 26, legY + 14 + rowH * 2);
  }

  function renderMistakeSummaryAndList(mistakes) {
    if (!mistakesDiv) return;

    if (!mistakes || !mistakes.length) {
      mistakesDiv.innerHTML = '<div class="mistakes-empty">No mistakes detected.</div>';
      return;
    }

    // Aggregate by phase and severity
    const phasesOrder = ['Opening', 'Middlegame', 'Endgame'];
    const severities = ['Inaccuracy', 'Mistake', 'Blunder'];
    const phaseStats = {};
    const phaseBuckets = {};

    mistakes.forEach((m) => {
      const phase = m.phase || 'Other';
      const sev = m.severity || 'Other';
      if (!phaseStats[phase]) {
        phaseStats[phase] = { total: 0 };
        severities.forEach(s => { phaseStats[phase][s] = 0; });
      }
      if (!phaseBuckets[phase]) {
        phaseBuckets[phase] = [];
      }
      phaseStats[phase].total += 1;
      if (phaseStats[phase][sev] != null) {
        phaseStats[phase][sev] += 1;
      }
      phaseBuckets[phase].push(m);
    });

    // Always show Opening, Middlegame, Endgame; then any others
    const phaseKeys = [
      ...phasesOrder,
      ...Object.keys(phaseStats).filter(p => !phasesOrder.includes(p)),
    ];

    let html = '<div class="mistakes-summary">';
    html += '<h3>Phase overview</h3>';
    html += '<div class="mistakes-summary-grid">';
    phaseKeys.forEach((phase) => {
      const stats = phaseStats[phase] || { total: 0, Inaccuracy: 0, Mistake: 0, Blunder: 0 };
      html += `<div class="mistakes-summary-card">
        <div class="phase-title">${phase}</div>
        <div class="phase-total">${stats.total} issues</div>
        <div class="phase-breakdown">
          <span class="badge badge-inaccuracy">${stats.Inaccuracy || 0} inaccuracies</span>
          <span class="badge badge-mistake">${stats.Mistake || 0} mistakes</span>
          <span class="badge badge-blunder">${stats.Blunder || 0} blunders</span>
        </div>
      </div>`;
    });
    html += '</div></div>';

    html += '<div class="mistakes-by-phase">';
    html += '<h3>Mistakes by phase</h3>';
    phaseKeys.forEach((phase) => {
      const list = phaseBuckets[phase] || [];
      html += `<div class="phase-group" data-phase="${phase}">
        <h4 class="phase-group-title">${phase} <span class="phase-count">(${list.length})</span></h4>
        <div class="phase-mistakes-visual">`;
      if (list.length === 0) {
        html += '<p class="phase-no-mistakes">No mistakes in this phase.</p>';
      } else {
        html += '<div class="phase-mistake-cards">';
        list.forEach((m, idx) => {
          const moveLabel =
            m.chess_move != null
              ? `Move ${m.chess_move.toFixed ? m.chess_move.toFixed(1) : m.chess_move}`
              : `#${idx + 1}`;
          const sevClass =
            m.severity === 'Blunder' ? 'sev-blunder' :
            m.severity === 'Mistake' ? 'sev-mistake' :
            m.severity === 'Inaccuracy' ? 'sev-inaccuracy' : '';
          html += `<div class="mistake-card ${sevClass}" data-phase="${phase}" data-idx="${idx}">
            <div class="mistake-card-move">${moveLabel}</div>
            <div class="mistake-card-severity">${m.severity || ''}</div>
            <div class="mistake-card-san">${m.move_played_san || m.move_played || ''}</div>
          </div>`;
        });
        html += '</div>';
      }
      html += '</div></div>';
    });
    html += '</div>';

    mistakesDiv.innerHTML = html;

    // Wire click handlers for each mistake card (same order as flat)
    flatMistakesList = [];
    phaseKeys.forEach(phase => {
      (phaseBuckets[phase] || []).forEach(m => flatMistakesList.push(m));
    });
    const items = mistakesDiv.querySelectorAll('.mistake-card');
    items.forEach((el, index) => {
      el.addEventListener('click', () => {
        const m = flatMistakesList[index];
        if (m) showMistakeDetails(m, index);
      });
    });
  }

  async function showMistakeDetails(mistake, mistakeIndex) {
    const details = document.getElementById('mistake-details');
    if (!details) return;
    details.innerHTML = '';

    const view = document.createElement('div');
    view.className = 'mistake-view';

    const loadingDiv = document.createElement('div');
    loadingDiv.style.padding = '1rem';
    loadingDiv.style.textAlign = 'center';
    loadingDiv.textContent = 'Analyzing mistake with Stockfish...';

    let continuationEvals = mistake.continuation_evals || [];
    let bestEvals = mistake.best_evals || [];
    let continuationMoves = mistake.continuation_moves || [];
    let bestMoves = mistake.best_moves || [];
    let startEval = mistake.start_eval != null ? mistake.start_eval : null;

    let hasStoredPv = (continuationMoves[0] && continuationMoves[0].variation && continuationMoves[0].variation.length) ||
      (bestMoves[0] && bestMoves[0].variation && bestMoves[0].variation.length);
    const hasEvals = (continuationEvals.length > 0 && continuationEvals.some(e => e != null)) ||
      (bestEvals.length > 0 && bestEvals.some(e => e != null)) ||
      (startEval != null && !isNaN(Number(startEval)));
    if (!hasStoredPv) view.appendChild(loadingDiv);
    details.appendChild(view);

    const boardsContainer = document.createElement('div');
    boardsContainer.className = 'boards-container';

    try {
      if (!mistake.position_before_fen || !mistake.position_after_fen) {
        throw new Error('Mistake data incomplete');
      }

      // Fetch from job when we need moves and/or evals (background may have filled evals later)
      if (currentJobId && (!hasStoredPv || !hasEvals)) {
        try {
          const jobResp = await fetch(`${API_BASE}/api/analyze-job/${currentJobId}`);
          const jobPayload = await parseJsonResponse(jobResp, null);
          if (jobPayload && jobPayload.result && jobPayload.result.mistakes && jobPayload.result.mistakes[mistakeIndex]) {
            const updated = jobPayload.result.mistakes[mistakeIndex];
            const gotMoves = updated.continuation_moves?.[0]?.variation?.length || updated.best_moves?.[0]?.variation?.length;
            const gotEvals = (updated.continuation_evals?.length > 0 && updated.continuation_evals.some(e => e != null)) ||
              (updated.best_evals?.length > 0 && updated.best_evals.some(e => e != null));
            if (gotMoves) {
              if (updated.continuation_moves) continuationMoves = updated.continuation_moves;
              if (updated.best_moves) bestMoves = updated.best_moves;
              hasStoredPv = true;
            }
            if (gotEvals) {
              continuationEvals = updated.continuation_evals || [];
              bestEvals = updated.best_evals || [];
              startEval = updated.start_eval != null ? updated.start_eval : null;
            }
            if (jobPayload.result) currentAnalysisData = jobPayload.result;
          }
        } catch (e) { /* ignore */ }
      }

      // If we still lack moves or evals, call on-demand API (always returns both)
      const stillNeedData = !hasStoredPv || !((continuationEvals.length > 0 && continuationEvals.some(e => e != null)) ||
        (bestEvals.length > 0 && bestEvals.some(e => e != null)) ||
        (startEval != null && !isNaN(Number(startEval))));
      if (stillNeedData) {
        const resp = await fetch(`${API_BASE}/api/analyze-mistake-fens`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fen_after_mistake: mistake.position_after_fen,
            fen_before_mistake: mistake.position_before_fen,
            move_played_uci: mistake.move_played_uci || ''
          }),
        });
        const analysisData = await parseJsonResponse(resp, null);
        if (analysisData == null) throw new Error('Invalid response from server');
        if (!resp.ok) throw new Error(analysisData.detail || resp.statusText);
        continuationEvals = analysisData.continuation_evals || [];
        bestEvals = analysisData.best_evals || [];
        continuationMoves = analysisData.continuation_moves || [];
        bestMoves = analysisData.best_moves || [];
        startEval = analysisData.start_eval != null ? analysisData.start_eval : null;
      }

      // Left board: Mistake continuation
      // The continuationMoves from backend already includes the mistake move as first move
      const leftSection = createBoardSection(
        'Why It\'s a Mistake',
        mistake.position_before_fen,
        continuationMoves,
        null, // Don't add mistake move separately - it's already in continuationMoves
        null,
        false,
        continuationEvals,
        bestEvals,
        startEval
      );
      boardsContainer.appendChild(leftSection);

      // Right board: Best alternative
      const rightSection = createBoardSection(
        'Best Alternative',
        mistake.position_before_fen,
        bestMoves,
        null,
        null,
        true,
        continuationEvals,
        bestEvals,
        startEval
      );
      boardsContainer.appendChild(rightSection);

      view.appendChild(boardsContainer);
      
      const plotContainer = document.createElement('div');
      plotContainer.style.marginTop = '2rem';
      plotContainer.style.padding = '1rem';
      plotContainer.style.background = '#2f3640';
      plotContainer.style.borderRadius = '8px';
      const plotTitle = document.createElement('h4');
      plotTitle.textContent = 'Evaluation Comparison';
      plotTitle.style.marginTop = '0';
      plotTitle.style.marginBottom = '1rem';
      plotTitle.style.color = '#f5f6fa';
      plotContainer.appendChild(plotTitle);
      
      const canvas = document.createElement('canvas');
      canvas.width = 800;
      canvas.height = 300;
      canvas.style.width = '100%';
      canvas.style.maxWidth = '800px';
      canvas.style.height = 'auto';
      plotContainer.appendChild(canvas);

      drawEvalPlot(canvas, startEval, continuationEvals, bestEvals);
      
      view.appendChild(plotContainer);
      if (loadingDiv.parentNode) loadingDiv.remove();
    } catch (error) {
      if (loadingDiv.parentNode) {
        loadingDiv.textContent = 'Error analyzing mistake: ' + error.message;
      } else {
        const errEl = document.createElement('div');
        errEl.className = 'mistake-error';
        errEl.style.padding = '1rem';
        errEl.style.color = '#ff7675';
        errEl.textContent = 'Error analyzing mistake: ' + error.message;
        view.appendChild(errEl);
      }
      console.error('Error analyzing mistake:', error);
    }
  }

  function uciToSquare(uci) {
    if (!uci || typeof uci !== 'string' || uci.length < 4) return null;
    return { from: uci.slice(0, 2), to: uci.slice(2, 4) };
  }

  function squareToPixel(sq, squareSize) {
    squareSize = squareSize || 460 / 8;
    const file = sq.charCodeAt(0) - 97;
    const rank = parseInt(sq[1], 10) - 1;
    const x = (file + 0.5) * squareSize;
    const y = (7 - rank + 0.5) * squareSize;
    return { x, y };
  }

  function drawEvalPlot(canvas, startEval, continuationEvals, bestEvals) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const plotWidth = width - 2 * padding;
    const plotHeight = height - 2 * padding;
    
    ctx.fillStyle = '#2f3640';
    ctx.fillRect(0, 0, width, height);
    
    const continuationData = (continuationEvals || []).filter(e => e != null);
    const bestData = (bestEvals || []).filter(e => e != null);
    
    if (continuationData.length === 0 && bestData.length === 0) return;
    
    const yMin = -800;
    const yMax = 800;
    const yRange = yMax - yMin;
    
    const evalToY = (eval) => {
      const cp = Math.max(-800, Math.min(800, eval));
      return padding + plotHeight - ((cp - yMin) / yRange) * plotHeight;
    };
    
    const indexToX = (idx, total) => padding + (idx / Math.max(total - 1, 1)) * plotWidth;
    const maxPoints = Math.max(continuationData.length, bestData.length, 1);
    
    // Draw grid lines
    ctx.strokeStyle = '#2d3436';
    ctx.lineWidth = 1;
    // Horizontal line at 0
    const zeroY = evalToY(0);
    ctx.beginPath();
    ctx.moveTo(padding, zeroY);
    ctx.lineTo(width - padding, zeroY);
    ctx.stroke();
    
    // Draw axes
    ctx.strokeStyle = '#636e72';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();
    
    // Draw continuation line (mistake line) in red/orange (scaled to shared x-axis)
    if (continuationData.length > 0) {
      ctx.strokeStyle = '#ff7675';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < continuationData.length; i++) {
        const x = indexToX(i, maxPoints);
        const y = evalToY(continuationData[i]);
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
      
      // Draw points
      ctx.fillStyle = '#ff7675';
      for (let i = 0; i < continuationData.length; i++) {
        const x = indexToX(i, maxPoints);
        const y = evalToY(continuationData[i]);
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    }
    
    // Draw best line in green/cyan (scaled to shared x-axis)
    if (bestData.length > 0) {
      ctx.strokeStyle = '#81ecec';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < bestData.length; i++) {
        const x = indexToX(i, maxPoints);
        const y = evalToY(bestData[i]);
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
      
      // Draw points
      ctx.fillStyle = '#81ecec';
      for (let i = 0; i < bestData.length; i++) {
        const x = indexToX(i, maxPoints);
        const y = evalToY(bestData[i]);
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    }

    // X-axis tick values (move indices)
    const xTickStep = maxPoints <= 5 ? 1 : Math.ceil(maxPoints / 5);
    ctx.fillStyle = '#b2bec3';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    for (let i = 0; i < maxPoints; i += xTickStep) {
      const x = indexToX(i, maxPoints);
      ctx.fillText(String(i), x, height - padding + 16);
    }
    ctx.fillText('Move', width / 2, height - 4);

    // Y-axis tick values: -8 to +8 pawns
    ctx.textAlign = 'right';
    ctx.fillStyle = '#b2bec3';
    for (let cp = -800; cp <= 800; cp += 200) {
      const y = evalToY(cp);
      if (y >= padding && y <= height - padding) {
        const pawns = (Number(cp) / 100).toFixed(1);
        ctx.fillText((cp >= 0 ? '+' : '') + pawns, padding - 6, y + 4);
      }
    }

    ctx.save();
    ctx.translate(12, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillStyle = '#b2bec3';
    ctx.fillText('Eval (pawns)', 0, 0);
    ctx.restore();

    // Legend: bottom-left so it doesn't overlap the curves
    const legendX = padding + 8;
    const legendY = height - padding - 52;
    ctx.fillStyle = 'rgba(45, 52, 54, 0.92)';
    ctx.strokeStyle = '#636e72';
    ctx.fillRect(legendX, legendY, 120, 44);
    ctx.strokeRect(legendX, legendY, 120, 44);
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillStyle = '#ff7675';
    ctx.fillRect(legendX + 8, legendY + 12, 14, 2);
    ctx.fillStyle = '#b2bec3';
    ctx.fillText('Mistake line', legendX + 26, legendY + 16);
    ctx.fillStyle = '#81ecec';
    ctx.fillRect(legendX + 8, legendY + 30, 14, 2);
    ctx.fillStyle = '#b2bec3';
    ctx.fillText('Best line', legendX + 26, legendY + 34);
  }

  function drawArrow(overlayEl, uci, isWhiteMove, squareSize) {
    squareSize = squareSize || 460 / 8;
    if (!overlayEl || !uci || uci.length < 4) return;
    const uciStr = typeof uci === 'string' ? uci : (uci.move_uci || uci.move || '');
    if (uciStr.length < 4) return;
    const fromSq = uciStr.slice(0, 2);
    const toSq = uciStr.slice(2, 4);
    const from = squareToPixel(fromSq, squareSize);
    const to = squareToPixel(toSq, squareSize);
    const color = isWhiteMove ? 'rgba(255,255,255,0.75)' : 'rgba(50,50,50,0.9)';
    const stroke = isWhiteMove ? 2 : 2.5;
    const markerId = 'arrow-' + (isWhiteMove ? 'w' : 'b') + '-' + overlayEl.id;
    overlayEl.innerHTML = '';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 460 460');
    svg.setAttribute('width', '460');
    svg.setAttribute('height', '460');
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', markerId);
    marker.setAttribute('markerWidth', '10');
    marker.setAttribute('markerHeight', '7');
    marker.setAttribute('refX', '9');
    marker.setAttribute('refY', '3.5');
    marker.setAttribute('orient', 'auto');
    const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    poly.setAttribute('points', '0 0, 10 3.5, 0 7');
    poly.setAttribute('fill', color);
    marker.appendChild(poly);
    defs.appendChild(marker);
    svg.appendChild(defs);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', from.x);
    line.setAttribute('y1', from.y);
    line.setAttribute('x2', to.x);
    line.setAttribute('y2', to.y);
    line.setAttribute('stroke', color);
    line.setAttribute('stroke-width', stroke);
    line.setAttribute('marker-end', 'url(#' + markerId + ')');
    svg.appendChild(line);
    overlayEl.appendChild(svg);
  }

  function createBoardSection(title, startFen, moves, mistakeMoveUci, mistakeMoveSan, isBest, continuationEvals, bestEvals, startEval) {
    continuationEvals = continuationEvals || [];
    bestEvals = bestEvals || [];
    const evals = isBest ? bestEvals : continuationEvals;
    startEval = startEval !== undefined ? startEval : null;

    const section = document.createElement('div');
    section.className = 'board-section';

    if (title) {
      const caption = document.createElement('div');
      caption.className = 'board-section-caption';
      caption.style.fontWeight = '600';
      caption.style.marginBottom = '0.5rem';
      caption.style.color = '#f5f6fa';
      caption.textContent = title;
      section.appendChild(caption);
    }

    const boardWithEval = document.createElement('div');
    boardWithEval.className = 'board-with-eval';

    const boardWrapperOuter = document.createElement('div');
    boardWrapperOuter.className = 'board-wrapper-outer';
    boardWrapperOuter.style.position = 'relative';
    boardWrapperOuter.style.width = '460px';
    boardWrapperOuter.style.height = '460px';

    const boardWrapper = document.createElement('div');
    boardWrapper.className = 'board-wrapper';
    const boardId = `board-${isBest ? 'best' : 'mistake'}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    boardWrapper.id = boardId;
    boardWrapper.style.width = '460px';
    boardWrapper.style.height = '460px';
    boardWrapperOuter.appendChild(boardWrapper);

    const arrowsOverlay = document.createElement('div');
    arrowsOverlay.className = 'board-arrows-overlay';
    arrowsOverlay.id = boardId + '-arrows';
    boardWrapperOuter.appendChild(arrowsOverlay);

    boardWithEval.appendChild(boardWrapperOuter);

    const barWrap = document.createElement('div');
    barWrap.className = 'eval-bar-wrap';
    barWrap.innerHTML = '<div class="eval-bar"><div class="eval-bar-white"></div><div class="eval-bar-black"></div></div><div class="eval-bar-label">0</div>';
    boardWithEval.appendChild(barWrap);
    section.appendChild(boardWithEval);

    const boardInfo = document.createElement('div');
    boardInfo.className = 'board-info';
    boardInfo.id = boardId + '-info';
    boardInfo.style.display = 'none';
    section.appendChild(boardInfo);

    const materialInfo = document.createElement('div');
    materialInfo.className = 'material-info';
    materialInfo.id = boardId + '-material';
    section.appendChild(materialInfo);

    const pvMovesList = document.createElement('div');
    pvMovesList.className = 'pv-moves-list';
    pvMovesList.id = boardId + '-pv';
    section.appendChild(pvMovesList);

    const nav = document.createElement('div');
    nav.className = 'board-nav';
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '◀ Prev';
    const resetBtn = document.createElement('button');
    resetBtn.className = 'board-nav-reset';
    resetBtn.textContent = 'Reset';
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Next ▶';
    nav.appendChild(prevBtn);
    nav.appendChild(resetBtn);
    nav.appendChild(nextBtn);
    section.appendChild(nav);

    let variation = [];
    if (moves && moves.length > 0 && moves[0] && moves[0].variation) {
      variation = moves[0].variation;
    }

    // Build UCI list, then derive SAN with chess.js so PV always shows full/clean moves
    const moveUcis = [];
    variation.forEach((v) => {
      const u = v && (v.move_uci || v.move);
      if (u) moveUcis.push(String(u));
    });
    const moveLabels = ['Start'];
    try {
      const chess = new Chess();
      chess.load(startFen);
      moveUcis.forEach((uci) => {
        const m = applyUci(chess, uci);
        moveLabels.push(m && m.san ? m.san : uci);
      });
    } catch (e) {
      moveUcis.forEach((uci) => moveLabels.push(uci));
    }

    const positionsCount = moveLabels.length;
    let currentIndex = 0;

    function renderPvMoves() {
      pvMovesList.innerHTML = '';
      // Start button
      const startBtn = document.createElement('span');
      startBtn.className = 'pv-move start' + (currentIndex === 0 ? ' current' : '');
      startBtn.textContent = 'Start';
      startBtn.dataset.index = '0';
      startBtn.addEventListener('click', () => {
        currentIndex = 0;
        updateBoard();
      });
      pvMovesList.appendChild(startBtn);

      const cols = document.createElement('div');
      cols.className = 'moves-columns';
      const left = document.createElement('div');
      left.className = 'moves-table';
      const right = document.createElement('div');
      right.className = 'moves-table';
      cols.appendChild(left);
      cols.appendChild(right);

      const fullMoves = Math.ceil((moveLabels.length - 1) / 2);
      for (let m = 0; m < fullMoves; m++) {
        const row = document.createElement('div');
        row.className = 'moves-row';

        const numSpan = document.createElement('span');
        numSpan.className = 'move-num';
        numSpan.textContent = String(m + 1) + '.';
        row.appendChild(numSpan);

        const whiteIdx = 1 + m * 2;
        const blackIdx = whiteIdx + 1;
        const whiteLabel = moveLabels[whiteIdx];
        const blackLabel = moveLabels[blackIdx];

        if (whiteLabel) {
          const whiteSpan = document.createElement('span');
          whiteSpan.className = 'pv-move move-white' + (whiteIdx === currentIndex ? ' current' : '');
          whiteSpan.textContent = whiteLabel;
          whiteSpan.dataset.index = String(whiteIdx);
          whiteSpan.addEventListener('click', () => {
            currentIndex = whiteIdx;
            updateBoard();
          });
          row.appendChild(whiteSpan);
        } else {
          const blank = document.createElement('span');
          blank.className = 'move-blank';
          row.appendChild(blank);
        }

        if (blackLabel) {
          const blackSpan = document.createElement('span');
          blackSpan.className = 'pv-move move-black' + (blackIdx === currentIndex ? ' current' : '');
          blackSpan.textContent = blackLabel;
          blackSpan.dataset.index = String(blackIdx);
          blackSpan.addEventListener('click', () => {
            currentIndex = blackIdx;
            updateBoard();
          });
          row.appendChild(blackSpan);
        } else {
          const blank = document.createElement('span');
          blank.className = 'move-blank';
          row.appendChild(blank);
        }

        // left column gets 1,3,5...; right gets 2,4,6...
        (m % 2 === 0 ? left : right).appendChild(row);
      }

      pvMovesList.appendChild(cols);
    }

    const config = {
      position: startFen,
      draggable: false,
      pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
    };
    let board;
    const sqSize = 460 / 8;

    function updateBoard() {
      if (!board) return;
      const chess = new Chess();
      try {
        chess.load(startFen);
      } catch (e) {
        boardInfo.textContent = 'Error loading position: ' + e.message;
        return;
      }

      prevBtn.disabled = currentIndex <= 0;
      nextBtn.disabled = currentIndex >= positionsCount - 1;

      if (currentIndex === 0) {
        board.position(startFen);
        boardInfo.textContent = 'Position before the mistake.';
        const startCp = startEval != null ? Number(startEval) : null;
        materialInfo.textContent = startCp != null && !isNaN(startCp) ? 'Eval: ' + formatEval(startCp) : 'Eval: —';
        setEvalBar(barWrap, startCp);
        arrowsOverlay.innerHTML = '';
      } else {
        for (let i = 0; i < currentIndex && i < moveUcis.length; i++) {
          const u = moveUcis[i];
          applyUci(chess, typeof u === 'string' ? u : (u && (u.move_uci || u.move)) || u);
        }
        board.position(chess.fen());
        const evalIdx = currentIndex - 1;
        const raw = evals[evalIdx];
        const cp = raw != null ? Number(raw) : null;
        
        // Format move display: pair white and black moves together
        let moveText = '';
        const whiteToMoveStart = startFen && startFen.indexOf(' w ') >= 0;
        
        if (currentIndex % 2 === 1) {
          // After first move (odd index) - show just that move
          // If white to move at start: index 1 = white move 0.5
          // If black to move at start: index 1 = black move 0.5
          const moveNum = 0.5;
          const moveSan = moveLabels[currentIndex];
          moveText = `Move ${moveNum.toFixed(1)}: ${moveSan}`;
        } else if (currentIndex > 0 && currentIndex % 2 === 0) {
          // After second move (even index) - show both moves together
          // Index 2: show move 0.5 and move 1.0
          // Index 4: show move 1.5 and move 2.0, etc.
          const whiteMoveNum = currentIndex / 2 - 0.5;
          const blackMoveNum = currentIndex / 2;
          const firstMoveSan = moveLabels[currentIndex - 1];
          const secondMoveSan = moveLabels[currentIndex];
          moveText = `Move ${whiteMoveNum.toFixed(1)}: ${firstMoveSan}, Move ${blackMoveNum.toFixed(1)}: ${secondMoveSan}`;
        }
        
        boardInfo.textContent = moveText;
        materialInfo.textContent = (cp != null && !isNaN(cp)) ? 'Eval: ' + formatEval(cp) : 'Eval: —';
        setEvalBar(barWrap, cp);

        const lastUci = moveUcis[currentIndex - 1];
        const uciStr = lastUci && (typeof lastUci === 'string' ? lastUci : (lastUci.move_uci || lastUci.move));
        const isWhiteMove = whiteToMoveStart ? (currentIndex - 1) % 2 === 0 : (currentIndex - 1) % 2 === 1;
        if (uciStr && uciStr.length >= 4) {
          drawArrow(arrowsOverlay, typeof uciStr === 'string' ? uciStr : uciStr, isWhiteMove, sqSize);
        } else {
          arrowsOverlay.innerHTML = '';
        }
      }

      // Update current highlighting for all moves
      pvMovesList.querySelectorAll('.pv-move').forEach((el) => {
        const elIndex = parseInt(el.dataset.index || '0', 10);
        el.classList.toggle('current', elIndex === currentIndex);
      });
    }

    if (typeof ChessBoard !== 'undefined') {
      requestAnimationFrame(() => {
        board = ChessBoard(boardId, config);
        renderPvMoves();
        updateBoard();
      });
    }

    prevBtn.addEventListener('click', () => {
      if (currentIndex > 0) currentIndex--;
      updateBoard();
    });

    resetBtn.addEventListener('click', () => {
      currentIndex = 0;
      updateBoard();
      if (pvMovesList.querySelectorAll('.pv-move').length) {
        pvMovesList.querySelectorAll('.pv-move').forEach((el, idx) => {
          el.classList.toggle('current', idx === 0);
        });
      }
    });

    nextBtn.addEventListener('click', () => {
      if (currentIndex < positionsCount - 1) currentIndex++;
      updateBoard();
    });

    return section;
  }

  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation(); // Prevent other handlers
      if (!isAnalyzing && window.startAnalyze) {
        window.startAnalyze();
      }
    }, true); // Use capture phase to handle early
  }
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation(); // Prevent other handlers
      // Don't call analyze here - button click handler will handle it
      // This prevents double execution when button is clicked inside form
    }, true); // Use capture phase to handle early
  }

  if (replayPrevBtn) {
    replayPrevBtn.addEventListener('click', () => {
      if (replayState.index > 0) {
        replayState.index--;
        if (replayBoard) replayBoard.position(replayState.fens[replayState.index]);
        updateReplayInfo();
      }
    });
  }
  if (replayResetBtn) {
    replayResetBtn.addEventListener('click', () => {
      replayState.index = 0;
      if (replayBoard) replayBoard.position(replayState.fens[0]);
      updateReplayInfo();
    });
  }
  if (replayNextBtn) {
    replayNextBtn.addEventListener('click', () => {
      if (replayState.index < replayState.fens.length - 1) {
        replayState.index++;
        if (replayBoard) replayBoard.position(replayState.fens[replayState.index]);
        updateReplayInfo();
      }
    });
  }
});

