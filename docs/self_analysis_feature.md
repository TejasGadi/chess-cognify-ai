# Feature: Real-Time Self Analysis Board

The Self Analysis Board is a specialized environment for interactive exploration. It provides immediate, high-fidelity feedback from Stockfish, allowing users to play through "what-if" scenarios.

## 1. Feature Description
- **Infinite Variation Exploration**: Users can deviate from the main line to explore specialized branches.
- **Dynamic Multi-PV**: View up to 10 alternative lines simultaneously, helping to understand relative position quality.
- **Evaluation Visuals**: A real-time "Eval Bar" that fluctuates based on centipawn scores or forced mate sequences.
- **Engine Config**: Adjusting evaluation depth and multi-line count on the fly.
- **State Persistence**: Though ephemeral, the board maintains a history of the current session's moves for easy back-and-forth navigation.

## 2. Low-Level Architecture

### Core Architecture Components
1.  **Frontend (React/Chessground)**: Uses `chessground` for the board UI. High-performance piece movement and legal move highlights are calculated locally using `chessops`.
2.  **API Gateway (FastAPI)**: Single-purpose endpoint (`/api/evaluate`) designed for low-latency request handling.
3.  **Stockfish Service (Process Manager)**: An asynchronous wrapper that interacts with the Stockfish binary via the UCI (Universal Chess Interface) protocol.
4.  **Process Lock Mechanism**: A critical `asyncio.Lock` that prevents the API from overwhelming the host CPU by spawning multiple engine processes.

### Component Diagram
```mermaid
graph LR
    UI[React Interface] -- FEN -- API[FastAPI /evaluate]
    API -- Lock Request -- Lock[asyncio.Lock]
    Lock -- Access Granted -- SM[StockfishService]
    SM -- UCI Commands -- SF[Stockfish Binary]
    SF -- Score/PV -- SM
    SM -- Compiled Data -- UI
```

## 3. Implementation Details

### Singleton & Lifecycle Management
The application uses a singleton pattern for the Stockfish service to ensure only one instance of the engine is alive.
- **Initialization**: Booted when the first request hits the API.
- **Cleanup**: The engine is gracefully shut down via the FastAPI `shutdown` event to prevent "zombie" processes.

### UCI Integration Logic
The service communicates with Stockfish using the following UCI orchestration:
1.  `isready`: Verifies engine state.
2.  `position fen [target_fen]`: Updates the internal engine board.
3.  `setoption name MultiPV value [N]`: Configures the number of lines.
4.  `go depth [D]`: Commands the engine to search.
5.  **Output Parsing**: Scans for `info depth ... score cp ... pv ...` to extract depth, score, and principal variation.

### Adaptive Locking Logic
To prevent rapid-fire moves (e.g., a user clicking back and forth quickly) from causing process leaks, the code implements:
```python
async def _get_engine(self):
    async with self._lock:  # Only one request can start/access instance setup
        if self._engine is None:
            # Popen binary and config
            ...
```

## 4. Data Flows

### Move Evaluation Flow
1.  **UI Interaction**: User moves a piece. React updates the `currentFen`.
2.  **Debounce**: React waits 300ms of inactivity before firing the API request.
3.  **Request Construction**: Front-end sends:
    ```json
    { "fen": "rnb...", "depth": 15, "multipv": 3 }
    ```
4.  **Backend Processing**:
    - **Validation**: `chess.Board(fen)` checks if the position is legal.
    - **Locking**: The request waits if another analysis is already in progress.
    - **Engine Sync**: `await engine.configure({"Threads": 4, "Hash": 256})`
    - **Engine Go**: `await engine.analysis(board, depth=15, multipv=3)`
5.  **Transformation**: UCI scores are converted to a standard `eval_str` (e.g., `-1.20` or `M5`).
6.  **Response**: UI receives structured move data and updates the `EngineAnalysisPanel`.

## 5. Comprehensive Example

### UCI Communication Sequence (internal)
```text
> uci
< uciok
> position fen rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1
> go depth 15 multipv 2
< info depth 1 seldepth 1 multipv 1 score cp 5 nodes 24 nps 24000 hashfull 0 pv e7e5
< info depth 15 ... score cp 15 ... pv e7e5 g1f3 ...
< bestmove e7e5
```

### Final API Response Object
```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
  "eval_str": "+0.15",
  "eval_cp": 15,
  "best_move": "e7e5",
  "mate": null,
  "top_moves": [
    {
      "rank": 1,
      "move": "e7e5",
      "move_san": "e5",
      "eval": 15,
      "eval_str": "+0.15",
      "pv_san": ["e5", "Nf3", "Nc6", "Bb5"]
    },
    {
      "rank": 2,
      "move": "c7c5",
      "move_san": "c5",
      "eval": -8,
      "eval_str": "-0.08",
      "pv_san": ["c5", "Nf3", "d6", "d4"]
    }
  ]
}
```
