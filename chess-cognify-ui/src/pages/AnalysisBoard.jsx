import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import Chessboard from '@/components/Chessboard';
import EvalBar from '@/components/EvalBar';
import MoveList from '@/components/MoveList';
import { getDests, applyMove, uciToSan } from '@/lib/chessLogic';
import { evaluatePositionWithLines } from '@/lib/api';
import { RotateCcw, RotateCw, Loader2, Activity } from 'lucide-react';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const AnalysisBoard = () => {
    const [positions, setPositions] = useState([START_FEN]);
    const [moves, setMoves] = useState([]);
    const [currentPly, setCurrentPly] = useState(0);
    const [orientation, setOrientation] = useState('white');
    const [liveEval, setLiveEval] = useState({ evalCp: 0, mate: null, isLoading: false });
    const [topLines, setTopLines] = useState([]);
    const [evalError, setEvalError] = useState(null);

    const positionsRef = useRef(positions);
    const currentPlyRef = useRef(currentPly);
    positionsRef.current = positions;
    currentPlyRef.current = currentPly;

    const currentFen = positions[currentPly] ?? START_FEN;
    const lastMove = currentPly > 0 && moves[currentPly - 1]
        ? { from: moves[currentPly - 1].uci.slice(0, 2), to: moves[currentPly - 1].uci.slice(2, 4) }
        : null;

    const dests = useMemo(() => getDests(currentFen), [currentFen]);
    const turnColor = currentFen.split(' ')[1] === 'w' ? 'white' : 'black';

    useEffect(() => {
        let isCancelled = false;
        setLiveEval(prev => ({ ...prev, isLoading: true }));
        setEvalError(null);

        evaluatePositionWithLines(currentFen, 15, 5)
            .then((result) => {
                if (isCancelled) return;
                setLiveEval({
                    evalCp: result.eval_cp ?? 0,
                    mate: result.mate ?? null,
                    isLoading: false,
                });
                setTopLines(result.top_moves || []);
            })
            .catch((err) => {
                if (isCancelled) return;
                console.error('Analysis board eval failed:', err);
                setEvalError(err.message || 'Evaluation failed');
                setLiveEval(prev => ({ ...prev, isLoading: false }));
            });

        return () => { isCancelled = true; };
    }, [currentFen]);

    const handleMove = useCallback((from, to) => {
        const ply = currentPlyRef.current;
        const posList = positionsRef.current;
        const fenBefore = posList[ply] ?? START_FEN;

        const uci = `${from}${to}`;
        const newFen = applyMove(fenBefore, uci);
        if (!newFen) return;

        const san = uciToSan(fenBefore, uci) ?? '...';
        const nextPly = ply + 1;

        setPositions(prev => [...prev.slice(0, nextPly), newFen]);
        setMoves(prev => [...prev.slice(0, ply), { san, uci, ply: nextPly }]);
        setCurrentPly(nextPly);
    }, []);

    const handleReset = useCallback(() => {
        setPositions([START_FEN]);
        setMoves([]);
        setCurrentPly(0);
    }, []);

    const handleFlip = useCallback(() => {
        setOrientation(o => (o === 'white' ? 'black' : 'white'));
    }, []);

    return (
        <div className="flex h-screen flex-col md:flex-row overflow-hidden">
            <div className="flex-1 bg-background/50 flex flex-col items-center justify-center p-4 min-h-[50vh] relative">
                <div className="flex gap-4 w-full max-w-[85vh] items-stretch">
                    <EvalBar
                        evalCp={liveEval.evalCp}
                        mate={liveEval.mate}
                        className="h-auto"
                    />
                    <div className="flex-1 aspect-square shadow-2xl rounded-xl overflow-hidden border-4 border-card relative group">
                        <Chessboard
                            fen={currentFen}
                            lastMove={currentPly > 0 ? lastMove : null}
                            orientation={orientation}
                            onMove={handleMove}
                            movable={{
                                color: turnColor,
                                free: false,
                                dests: dests,
                            }}
                        />
                    </div>
                </div>

                <div className="mt-4 flex gap-2">
                    <button onClick={() => setCurrentPly(0)} className="px-3 py-1 bg-card rounded border">|&lt;</button>
                    <button onClick={() => setCurrentPly(p => Math.max(0, p - 1))} className="px-3 py-1 bg-card rounded border">&lt;</button>
                    <span className="px-3 py-1 bg-card rounded border min-w-[3rem] text-center">{currentPly} / {moves.length}</span>
                    <button onClick={() => setCurrentPly(p => Math.min(moves.length, p + 1))} className="px-3 py-1 bg-card rounded border">&gt;</button>
                    <button onClick={() => setCurrentPly(moves.length)} className="px-3 py-1 bg-card rounded border">&gt;|</button>
                    <button onClick={handleReset} className="px-3 py-1 bg-card rounded border ml-2 flex items-center gap-1.5">
                        <RotateCcw className="w-4 h-4" /> Reset
                    </button>
                    <button onClick={handleFlip} className="px-3 py-1 bg-card rounded border flex items-center gap-1.5">
                        <RotateCw className="w-4 h-4" /> Flip
                    </button>
                </div>
            </div>

            <div className="w-full md:w-96 border-l bg-card flex flex-col h-[60vh] md:h-full">
                <div className="p-4 border-b">
                    <h2 className="font-bold">Analysis Board</h2>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        Free analysis — play any move for both sides
                    </p>
                </div>

                <div className="flex-1 overflow-auto flex flex-col">
                    <div className="p-4 bg-muted/30 border-b flex flex-col justify-center text-center relative group">
                        {liveEval.isLoading && (
                            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground py-2">
                                <Loader2 className="w-4 h-4 animate-spin" /> Analyzing…
                            </div>
                        )}
                        {evalError && (
                            <p className="text-sm text-destructive py-2">{evalError}</p>
                        )}
                        {!liveEval.isLoading && topLines.length > 0 && (
                            <div className="space-y-1.5 py-2 text-left">
                                {topLines.map((m, idx) => (
                                    <div key={idx} className="flex items-start gap-2 text-xs">
                                        <div
                                            className={`flex-shrink-0 w-12 text-center py-0.5 rounded font-mono font-bold
                                                ${m.eval >= 0 ? 'bg-zinc-100 text-zinc-900' : 'bg-zinc-800 text-zinc-100'}
                                            `}
                                        >
                                            {m.eval_str}
                                        </div>
                                        <div className="flex-1 text-muted-foreground leading-tight">
                                            {m.pv_san && m.pv_san.length > 0 ? (
                                                m.pv_san.map((pvMove, pvIdx) => (
                                                    <span key={pvIdx}>
                                                        {pvIdx > 0 && ' '}
                                                        <span className={pvIdx === 0 ? 'font-bold text-foreground' : 'text-foreground/80'}>
                                                            {pvMove}
                                                        </span>
                                                    </span>
                                                ))
                                            ) : (
                                                <span className="font-bold text-foreground">{m.move_san}</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="p-4">
                        <MoveList
                            moves={moves}
                            currentPly={currentPly}
                            onMoveSelect={setCurrentPly}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AnalysisBoard;
