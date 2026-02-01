# Analysis Board (Self Analysis) – Plan

## Separation from Game Analysis

**Self Analysis (Analysis Board) is a separate feature and tab from Game Analysis.**

- **Game Analysis** (`/analysis`, `/analysis/:gameId`): For analyzing an uploaded/completed game. User steps through the game’s moves; engine lines and “Your move” come from cached analysis; board is constrained to the game line.
- **Self Analysis / Analysis Board** (`/analysis-board`): Standalone board for free exploration. User can play any move as White or Black; no game id; eval and top 5 engine lines update live; “Your move” shows the last move played. No shared state or tab with Game Analysis.

They are distinct entry points, routes, and UIs. The Analysis Board only reuses the same UI *components* and layout patterns (EvalBar, board, right panel with engine lines) for consistency, not the same page or flow.

---

## Overview

Add a third feature **Analysis Board** (Self Analysis) where the user can make any move from both sides. The board shows an eval bar and top 5 engine lines that update on each move; **"Your move: e4"** is displayed below the engine lines on the right panel, reusing the same UI patterns as the game analysis (GameView) tab.

## Summary of implementation

| Area | Change |
|------|--------|
| Backend | Extend `POST /api/evaluate` with optional `multipv`; return `top_moves` + `last_move_san` |
| Frontend API | Add `evaluatePositionWithLines(fen, depth, multipv)` |
| chessLogic | Add `applyMove(fen, uci)` → new FEN |
| New page | **AnalysisBoard.jsx** – board (free movement both sides), EvalBar, right panel with top 5 lines + "Your move: …" |
| Routing/Nav | Route **`/analysis-board`** and link in nav as its own entry (separate from Game Analysis) |

## Key implementation points

1. **New route:** `/analysis-board` only; no overlap with `/analysis` or `/analysis/:gameId`.
2. **New page:** `AnalysisBoard.jsx` – no game id, no MoveList of a game, no Coach/Info tabs; just board + eval bar + engine lines + "Your move".
3. **Navigation:** Add a dedicated link for "Analysis Board" or "Self Analysis" (e.g. in Layout or Navbar) so users open it as a separate feature from "Analysis" (game list / game view).
