import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import Chessboard from '@/components/Chessboard';
import EvalBar from '@/components/EvalBar';
import SelfAnalysisSidebar from '@/components/SelfAnalysis/SelfAnalysisSidebar';
import PGNImportDialog from '@/components/SelfAnalysis/PGNImportDialog';
import { getDests, applyMove, uciToSan, parseGame, generatePgn } from '@/lib/chessLogic';
import { evaluatePositionWithLines } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { RotateCcw, RotateCw, ChevronFirst, ChevronLeft, ChevronRight, ChevronLast, Copy, Download, Share2 } from 'lucide-react';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const SelfAnalysisPage = () => {
    // --- State: Game ---
    const [positions, setPositions] = useState([START_FEN]);
    const [moves, setMoves] = useState([]); // Array of { san, uci, ply }
    const [currentPly, setCurrentPly] = useState(0);
    const [orientation, setOrientation] = useState('white');

    // --- State: Analysis ---
    const [isAnalysisActive, setIsAnalysisActive] = useState(true);
    const [engineDepth, setEngineDepth] = useState(15);
    const [liveEval, setLiveEval] = useState({ evalCp: 0, mate: null, isLoading: false });
    const [topLines, setTopLines] = useState([]);
    const [multipv, setMultipv] = useState(3);
    const [activeTab, setActiveTab] = useState('analysis');

    // --- Refs for async operations ---
    const positionsRef = useRef(positions);
    const currentPlyRef = useRef(currentPly);
    const analysisTimeoutRef = useRef(null);

    // Sync refs
    positionsRef.current = positions;
    currentPlyRef.current = currentPly;

    // Derived state
    const currentFen = positions[currentPly] ?? START_FEN;
    const turnColor = currentFen.split(' ')[1] === 'w' ? 'white' : 'black';
    const lastMove = currentPly > 0 && moves[currentPly - 1]
        ? { from: moves[currentPly - 1].uci.slice(0, 2), to: moves[currentPly - 1].uci.slice(2, 4) }
        : null;

    // Legal moves for Chessground
    const dests = useMemo(() => getDests(currentFen), [currentFen]);

    // --- Effect: Run Analysis ---
    useEffect(() => {
        if (!isAnalysisActive) {
            setLiveEval(prev => ({ ...prev, isLoading: false }));
            return;
        }

        // Clear previous timeout
        if (analysisTimeoutRef.current) {
            clearTimeout(analysisTimeoutRef.current);
        }

        setLiveEval(prev => ({ ...prev, isLoading: true }));

        // Debounce analysis request by 300ms
        analysisTimeoutRef.current = setTimeout(() => {
            evaluatePositionWithLines(currentFen, engineDepth, multipv)
                .then((result) => {
                    // Check if we are still on the same FEN (optional optimization, but simplified here)
                    setLiveEval({
                        evalCp: result.eval_cp ?? 0,
                        mate: result.mate ?? null,
                        isLoading: false,
                    });
                    setTopLines(result.top_moves || []);
                })
                .catch((err) => {
                    console.error('Self analysis eval failed:', err);
                    setLiveEval(prev => ({ ...prev, isLoading: false }));
                });
        }, 300);

        return () => {
            if (analysisTimeoutRef.current) {
                clearTimeout(analysisTimeoutRef.current);
            }
        };
    }, [currentFen, isAnalysisActive, engineDepth, multipv]);

    // --- Handlers ---

    const handleMove = useCallback((from, to) => {
        const ply = currentPlyRef.current;
        const posList = positionsRef.current;
        const fenBefore = posList[ply] ?? START_FEN;

        const uci = `${from}${to}`;
        const newFen = applyMove(fenBefore, uci);

        if (!newFen) return; // Invalid move logic check (though dests should prevent this)

        const san = uciToSan(fenBefore, uci) ?? '...';
        const nextPly = ply + 1;

        // Truncate future if making a move from middle
        const newPositions = [...posList.slice(0, nextPly), newFen];
        // For moves, we also need to slice. Note moves array is 0-indexed where ply 1 is index 0.
        // If currentPly is 0, we keep 0 moves. If currentPly is 1, we keep 1 move (index 0).
        const newMoves = [
            ...moves.slice(0, ply),
            { san, uci, ply: nextPly }
        ];

        setPositions(newPositions);
        setMoves(newMoves);
        setCurrentPly(nextPly);
    }, [moves]);

    const handleReset = useCallback(() => {
        setPositions([START_FEN]);
        setMoves([]);
        setCurrentPly(0);
        setTopLines([]);
        setLiveEval({ evalCp: 0, mate: null, isLoading: false });
    }, []);

    const handleFlip = useCallback(() => {
        setOrientation(o => (o === 'white' ? 'black' : 'white'));
    }, []);

    const handleMoveSelect = useCallback((plyOrMove) => {
        // MoveList might pass the move object or just ply
        const ply = typeof plyOrMove === 'number' ? plyOrMove : plyOrMove.ply;
        setCurrentPly(ply);
    }, []);

    const handlePgnImport = useCallback((pgn) => {
        const { moves: parsedMoves, positions: parsedPositions, headers } = parseGame(pgn);

        if (parsedPositions.length === 0) return;

        setPositions(parsedPositions);
        setMoves(parsedMoves);
        setCurrentPly(parsedMoves.length); // Jump to end of loaded game

        // Handle orientation based on headers (optional, usually start as white)
        // setOrientation('white');

        setTopLines([]); // Clear analysis until new fetch
    }, []);

    const copyToClipboard = (text, label) => {
        navigator.clipboard.writeText(text).then(() => {
            // Simple visual feedback via console or could use a toast
            console.log(`${label} copied to clipboard`);
        });
    };

    const downloadPgn = () => {
        const pgn = generatePgn(moves);
        const element = document.createElement("a");
        const file = new Blob([pgn], { type: 'text/plain' });
        element.href = URL.createObjectURL(file);
        element.download = `analysis_${new Date().getTime()}.pgn`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    };

    return (
        <TooltipProvider>
            <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-background">
                {/* Left/Center: Board Area */}
                <div className="flex-1 flex flex-col items-center justify-center p-4 min-bg-secondary/10 relative">
                    <div className="flex gap-2 w-full max-w-[80vh] aspect-square items-stretch">
                        {/* Eval Bar */}
                        <div className="flex-shrink-0 w-8 md:w-12">
                            <EvalBar
                                evalCp={liveEval.evalCp}
                                mate={liveEval.mate}
                                className="h-full rounded-sm shadow-sm"
                            />
                        </div>

                        {/* Board */}
                        <div className="flex-1 rounded-lg overflow-hidden shadow-2xl border-4 border-card/50 bg-card">
                            <Chessboard
                                fen={currentFen}
                                lastMove={lastMove}
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

                    {/* Board Controls (Bottom) */}
                    <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                        <PGNImportDialog onImport={handlePgnImport} />

                        <div className="h-8 w-px bg-border mx-2" />

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="outline" size="icon"
                                    onClick={() => setCurrentPly(0)}
                                    disabled={currentPly === 0}
                                >
                                    <ChevronFirst className="w-4 h-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Start</TooltipContent>
                        </Tooltip>

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="outline" size="icon"
                                    onClick={() => setCurrentPly(p => Math.max(0, p - 1))}
                                    disabled={currentPly === 0}
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Previous Move</TooltipContent>
                        </Tooltip>

                        <span className="text-sm font-mono font-medium min-w-[3rem] text-center text-muted-foreground mx-1">
                            {currentPly} / {moves.length}
                        </span>

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="outline" size="icon"
                                    onClick={() => setCurrentPly(p => Math.min(moves.length, p + 1))}
                                    disabled={currentPly === moves.length}
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Next Move</TooltipContent>
                        </Tooltip>

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="outline" size="icon"
                                    onClick={() => setCurrentPly(moves.length)}
                                    disabled={currentPly === moves.length}
                                >
                                    <ChevronLast className="w-4 h-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>End</TooltipContent>
                        </Tooltip>

                        <div className="h-8 w-px bg-border mx-2" />

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button variant="outline" onClick={handleReset} className="px-3">
                                    <RotateCcw className="w-4 h-4 mr-2" /> Reset
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Reset Board</TooltipContent>
                        </Tooltip>

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button variant="outline" onClick={handleFlip} className="px-3">
                                    <RotateCw className="w-4 h-4 mr-2" /> Flip
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Flip Board</TooltipContent>
                        </Tooltip>

                        <div className="h-8 w-px bg-border mx-2" />

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button variant="outline" size="icon" onClick={() => copyToClipboard(currentFen, 'FEN')}>
                                    <Copy className="w-4 h-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Copy FEN</TooltipContent>
                        </Tooltip>

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button variant="outline" size="icon" onClick={() => copyToClipboard(generatePgn(moves), 'PGN')}>
                                    <Share2 className="w-4 h-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Copy PGN</TooltipContent>
                        </Tooltip>

                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button variant="outline" size="icon" onClick={downloadPgn}>
                                    <Download className="w-4 h-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Download PGN</TooltipContent>
                        </Tooltip>
                    </div>
                </div>

                {/* Right: Sidebar */}
                <div className="w-full md:w-[400px] flex-shrink-0 h-full">
                    <SelfAnalysisSidebar
                        activeTab={activeTab}
                        setActiveTab={setActiveTab}

                        // Engine Props
                        engineLines={topLines}
                        engineDepth={engineDepth}
                        isAnalysisLoading={liveEval.isLoading}
                        isAnalysisActive={isAnalysisActive}
                        onToggleAnalysis={setIsAnalysisActive}
                        multipv={multipv}
                        onMultipvChange={setMultipv}

                        // Move List Props
                        moves={moves}
                        currentPly={currentPly}
                        onMoveSelect={handleMoveSelect}
                    />
                </div>
            </div>
        </TooltipProvider>
    );
};

export default SelfAnalysisPage;
