import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import useGameStore from '@/store/gameStore';
import Chessboard from '@/components/Chessboard';
import MoveList from '@/components/MoveList';
import GameChat from '@/components/GameChat';
import EvalBar from '@/components/EvalBar';
import GameDetailedStats from '@/components/GameDetailedStats';
import { parseGame, getDests } from '@/lib/chessLogic';
import { evaluatePosition } from '@/lib/api';
import * as Tabs from '@radix-ui/react-tabs';
import { Info, MessageSquare, Activity, CheckCircle2, AlertCircle, Loader2, Trophy, Target, AlertTriangle } from 'lucide-react';

const GameView = () => {
    const { gameId } = useParams();
    const { currentGame, analysisData, isLoading, fetchGameDetails, checkAnalysisStatus } = useGameStore();
    const [currentPly, setCurrentPly] = useState(0);
    const [liveEval, setLiveEval] = useState({ evalCp: 0, mate: null, isLoading: false });
    const [showStatus, setShowStatus] = useState(true);

    // Derived state for the game
    const gameLogic = useMemo(() => {
        if (currentGame?.pgn) {
            return parseGame(currentGame.pgn);
        }
        return { moves: [], positions: ['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'] };
    }, [currentGame?.pgn]);

    useEffect(() => {
        if (gameId) {
            fetchGameDetails(gameId);
        }
    }, [gameId, fetchGameDetails]);

    // Polling effect for background analysis
    useEffect(() => {
        if (!gameId || !currentGame) return;

        const isAnalyzing = currentGame.status === 'pending' || currentGame.status === 'analyzing';
        if (!isAnalyzing) {
            // If we just finished polling, we might want to refresh details once more for final summary
            if (currentGame.status === 'completed' && !analysisData?.summary) {
                fetchGameDetails(gameId);
            }
            return;
        }

        const pollInterval = setInterval(() => {
            checkAnalysisStatus(gameId);
        }, 3000); // Poll every 3 seconds

        return () => clearInterval(pollInterval);
    }, [gameId, currentGame?.status, checkAnalysisStatus, fetchGameDetails, analysisData?.summary]);

    // Check if we are currently polling (for UI feedback)
    const isPolling = currentGame?.status === 'pending' || currentGame?.status === 'analyzing';

    // Auto-dismiss completed status after 5 seconds
    useEffect(() => {
        if (currentGame?.status === 'completed' && showStatus) {
            const timer = setTimeout(() => {
                setShowStatus(false);
            }, 5000);
            return () => clearTimeout(timer);
        }
    }, [currentGame?.status, showStatus]);

    // Reset showStatus when gameId changes
    useEffect(() => {
        setShowStatus(true);
    }, [gameId]);

    // Current FEN
    const currentFen = gameLogic.positions[currentPly] || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

    // Live evaluation effect - fetch Stockfish eval whenever FEN changes
    useEffect(() => {
        let isCancelled = false;

        const fetchEvaluation = async () => {
            if (!currentFen) return;

            setLiveEval(prev => ({ ...prev, isLoading: true }));

            try {
                const result = await evaluatePosition(currentFen, 15);
                if (!isCancelled) {
                    setLiveEval({
                        evalCp: result.eval_cp,
                        mate: result.mate,
                        isLoading: false
                    });
                }
            } catch (error) {
                console.error('Failed to fetch live evaluation:', error);
                if (!isCancelled) {
                    setLiveEval(prev => ({ ...prev, isLoading: false }));
                }
            }
        };

        fetchEvaluation();

        return () => {
            isCancelled = true;
        };
    }, [currentFen]);

    // Calculate valid dests for local interaction
    const dests = useMemo(() => {
        return getDests(currentFen);
    }, [currentFen]);

    // Handle user move on board
    const handleMove = useCallback((from, to) => {
        const uci = `${from}${to}`;
        const nextMove = gameLogic.moves[currentPly];

        if (nextMove && nextMove.uci.startsWith(uci)) {
            setCurrentPly(p => p + 1);
        } else {
            console.log("Variation attempted or incorrect move", uci);
        }
    }, [gameLogic, currentPly]);

    // Find analysis for current ply
    const currentMoveAnalysis = useMemo(() => {
        if (!analysisData?.moves) return null;
        const analysis = analysisData.moves.find(m => m.ply === currentPly);
        return analysis;
    }, [analysisData, currentPly]);

    if (isLoading && !currentGame) {
        return <div className="h-full flex items-center justify-center">Loading game data...</div>;
    }

    if (!currentGame) {
        return <div className="h-full p-8 text-destructive">Game not found</div>;
    }

    // Determine whose turn it is for 'movable' color
    const turnColor = currentFen.split(' ')[1] === 'w' ? 'white' : 'black';

    return (
        <div className="flex h-screen flex-col md:flex-row overflow-hidden">
            {/* Center - Board with Evaluation Bar */}
            <div className="flex-1 bg-background/50 flex flex-col items-center justify-center p-4 min-h-[50vh] relative">
                {/* Analysis Status Notification Bar */}
                {currentGame && showStatus && (currentGame.status !== 'completed' || (isPolling === false && currentGame.status === 'completed')) && (
                    <div className="absolute top-8 left-1/2 -translate-x-1/2 z-20 w-full max-w-sm px-4">
                        <div className={`p-3 rounded-xl border shadow-xl backdrop-blur-md flex items-center gap-3 transition-all duration-500 animate-in fade-in slide-in-from-top-4
                            ${currentGame.status === 'failed'
                                ? 'bg-destructive/10 border-destructive/20 text-destructive shadow-destructive/5'
                                : currentGame.status === 'completed'
                                    ? 'bg-green-500/10 border-green-500/20 text-green-600 shadow-green-500/5'
                                    : 'bg-primary/10 border-primary/20 text-primary shadow-primary/5'}
                        `}>
                            {currentGame.status === 'failed' ? (
                                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            ) : currentGame.status === 'completed' ? (
                                <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-green-600" />
                            ) : (
                                <Loader2 className="w-5 h-5 flex-shrink-0 animate-spin" />
                            )}
                            <div className="flex-1 min-w-0">
                                <p className="text-[10px] font-bold uppercase tracking-[0.2em] opacity-70">
                                    {currentGame.status === 'failed' ? 'Error' : currentGame.status === 'completed' ? 'Success' : 'Processing'}
                                </p>
                                <p className="text-sm font-semibold truncate">
                                    {currentGame.status === 'failed'
                                        ? (currentGame.error_message || 'Analysis failed')
                                        : currentGame.status === 'completed'
                                            ? 'Analysis complete!'
                                            : 'AI is analyzing your game...'}
                                </p>
                            </div>

                            <div className="flex items-center gap-2">
                                {(currentGame.status === 'analyzing' || currentGame.status === 'pending') && (
                                    <div className="flex gap-1 pr-1">
                                        <div className="w-1 h-1 rounded-full bg-primary animate-pulse"></div>
                                        <div className="w-1 h-1 rounded-full bg-primary animate-pulse [animation-delay:200ms]"></div>
                                        <div className="w-1 h-1 rounded-full bg-primary animate-pulse [animation-delay:400ms]"></div>
                                    </div>
                                )}
                                <button
                                    onClick={() => setShowStatus(false)}
                                    className="p-1 hover:bg-black/5 rounded-md transition-colors"
                                >
                                    <AlertCircle className="w-4 h-4 rotate-45 opacity-50" />
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                <div className="flex gap-4 w-full max-w-[85vh] items-stretch">
                    {/* Evaluation Bar */}
                    <EvalBar
                        evalCp={liveEval.evalCp}
                        mate={liveEval.mate}
                        className="h-auto"
                    />

                    {/* Chessboard */}
                    <div className="flex-1 aspect-square shadow-2xl rounded-xl overflow-hidden border-4 border-card relative group">
                        <Chessboard
                            fen={currentFen}
                            lastMove={currentPly > 0 ? {
                                from: gameLogic.moves[currentPly - 1]?.uci.slice(0, 2),
                                to: gameLogic.moves[currentPly - 1]?.uci.slice(2, 4)
                            } : null}
                            orientation={currentGame.metadata?.player_color || 'white'}
                            onMove={handleMove}
                            movable={{
                                color: turnColor,
                                free: false,
                                dests: dests
                            }}
                        />
                    </div>
                </div>

                {/* Board Controls */}
                <div className="mt-4 flex gap-2">
                    <button onClick={() => setCurrentPly(0)} className="px-3 py-1 bg-card rounded border">|&lt;</button>
                    <button onClick={() => setCurrentPly(p => Math.max(0, p - 1))} className="px-3 py-1 bg-card rounded border">&lt;</button>
                    <span className="px-3 py-1 bg-card rounded border min-w-[3rem] text-center">{currentPly} / {gameLogic.moves.length}</span>
                    <button onClick={() => setCurrentPly(p => Math.min(gameLogic.moves.length, p + 1))} className="px-3 py-1 bg-card rounded border">&gt;</button>
                    <button onClick={() => setCurrentPly(gameLogic.moves.length)} className="px-3 py-1 bg-card rounded border">&gt;|</button>
                </div>
            </div>

            {/* Right Sidebar - Analysis & Chat */}
            <div className="w-full md:w-96 border-l bg-card flex flex-col h-[60vh] md:h-full">
                <div className="p-4 border-b">
                    <h2 className="font-bold truncate" title={currentGame.metadata?.title}>
                        {currentGame.metadata?.title || "Game Analysis"}
                    </h2>
                    <div className="text-sm text-muted-foreground flex justify-between mt-1">
                        <span>{currentGame.metadata?.White || "White"}</span>
                        <span className="font-bold text-xs bg-secondary px-1 rounded">vs</span>
                        <span>{currentGame.metadata?.Black || "Black"}</span>
                    </div>
                </div>

                <Tabs.Root defaultValue="moves" className="flex-1 flex flex-col overflow-hidden">
                    <Tabs.List className="flex border-b">
                        <Tabs.Trigger value="moves" className="flex-1 px-4 py-3 text-sm font-medium border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary hover:text-foreground/80 transition-colors flex items-center justify-center gap-2">
                            <Activity className="w-4 h-4" /> Moves
                        </Tabs.Trigger>
                        <Tabs.Trigger value="chat" className="flex-1 px-4 py-3 text-sm font-medium border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary hover:text-foreground/80 transition-colors flex items-center justify-center gap-2">
                            <MessageSquare className="w-4 h-4" /> Coach
                        </Tabs.Trigger>
                        <Tabs.Trigger value="info" className="flex-1 px-4 py-3 text-sm font-medium border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary hover:text-foreground/80 transition-colors flex items-center justify-center gap-2">
                            <Info className="w-4 h-4" /> Info
                        </Tabs.Trigger>
                    </Tabs.List>

                    <Tabs.Content value="moves" className="flex-1 overflow-auto">
                        {/* Analysis Box */}
                        <div className="p-4 bg-muted/30 border-b flex flex-col justify-center text-center relative group">
                            {/* Debug info hidden unless hovering */}
                            <div className="hidden group-hover:block absolute top-1 right-1 text-[10px] text-muted-foreground bg-background p-1 border rounded opacity-50 hover:opacity-100">
                                Ply: {currentPly} | Data: {analysisData?.moves?.length || 0}
                            </div>

                            {currentMoveAnalysis ? (
                                <div className="space-y-2 text-left">
                                    {currentMoveAnalysis.top_moves && currentMoveAnalysis.top_moves.length > 0 && (
                                        <div className="space-y-1.5 py-2 border-b mb-2">
                                            {currentMoveAnalysis.top_moves.map((m, idx) => (
                                                <div key={idx} className="flex items-start gap-2 text-xs group/line">
                                                    <div className={`flex-shrink-0 w-12 text-center py-0.5 rounded font-mono font-bold
                                                        ${m.eval >= 0 ? 'bg-zinc-100 text-zinc-900' : 'bg-zinc-800 text-zinc-100'}
                                                    `}>
                                                        {m.eval_str}
                                                    </div>
                                                    <div className="flex-1 text-muted-foreground leading-tight line-clamp-2">
                                                        {m.pv_san && m.pv_san.length > 0 ? (
                                                            m.pv_san.map((pvMove, pvIdx) => (
                                                                <span key={pvIdx}>
                                                                    {pvIdx % 2 === 0 ? (
                                                                        <span className="text-foreground/60 mr-1">
                                                                            {Math.floor((currentMoveAnalysis.ply + pvIdx) / 2) + 1}.
                                                                            {(currentMoveAnalysis.ply + pvIdx) % 2 === 1 && "..."}
                                                                        </span>
                                                                    ) : null}
                                                                    <span className={`mr-1.5 ${pvIdx === 0 ? 'font-bold text-foreground' : 'text-foreground/80'}`}>
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

                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-sm font-medium text-muted-foreground mr-1">Your move:</span>
                                        <span className="text-sm font-bold">{currentMoveAnalysis.move_san}</span>
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide
                                            ${currentMoveAnalysis.label === 'Best' ? 'bg-green-500/10 text-green-500' :
                                                currentMoveAnalysis.label === 'Good' ? 'bg-emerald-500/10 text-emerald-500' :
                                                    currentMoveAnalysis.label === 'Inaccuracy' ? 'bg-yellow-500/10 text-yellow-500' :
                                                        currentMoveAnalysis.label === 'Mistake' ? 'bg-orange-500/10 text-orange-500' :
                                                            currentMoveAnalysis.label === 'Blunder' ? 'bg-red-500/10 text-red-500' :
                                                                'bg-blue-500/10 text-blue-500'}
                                        `}>
                                            {currentMoveAnalysis.label}
                                        </span>
                                        {currentMoveAnalysis.centipawn_loss !== undefined && currentMoveAnalysis.centipawn_loss > 0 && (
                                            <span className="text-[10px] text-muted-foreground">
                                                -{currentMoveAnalysis.centipawn_loss} cp
                                            </span>
                                        )}
                                    </div>

                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                        {currentMoveAnalysis.explanation || "No explanation available."}
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <p className="text-sm text-muted-foreground flex flex-col items-center gap-2">
                                        {currentGame.status === 'failed' ? (
                                            <>
                                                <AlertCircle className="w-8 h-8 text-destructive/50" />
                                                <span className="text-destructive font-medium">Analysis encountered an error</span>
                                            </>
                                        ) : currentGame.status === 'analyzing' || currentGame.status === 'pending' ? (
                                            <>
                                                <Loader2 className="w-8 h-8 text-primary/50 animate-spin" />
                                                <span>Waiting for AI insights...</span>
                                            </>
                                        ) : currentPly === 0 ? (
                                            "Game Start. Make a move to see analysis."
                                        ) : (
                                            "No analysis data for this move."
                                        )}
                                    </p>
                                </div>
                            )}
                        </div>

                        <div className="p-4">
                            <MoveList
                                moves={gameLogic.moves}
                                currentPly={currentPly}
                                onMoveSelect={setCurrentPly}
                            />
                        </div>
                    </Tabs.Content>

                    <Tabs.Content value="chat" className="flex-1 overflow-hidden">
                        <GameChat gameId={gameId} />
                    </Tabs.Content>

                    <Tabs.Content value="info" className="flex-1 p-4 overflow-auto">
                        <div className="space-y-4">
                            {analysisData?.summary?.details ? (
                                <GameDetailedStats
                                    summary={analysisData.summary}
                                    metadata={currentGame.metadata}
                                />
                            ) : (
                                <div className="bg-card rounded-xl border p-6 text-center space-y-4 shadow-sm">
                                    <div className="flex justify-center">
                                        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                                            <Trophy className="w-8 h-8 text-primary" />
                                        </div>
                                    </div>
                                    <h3 className="text-lg font-bold">Game Summary</h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-4 bg-muted/50 rounded-lg">
                                            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Accuracy</p>
                                            <p className="text-2xl font-black">{analysisData?.summary?.accuracy || '-'}%</p>
                                        </div>
                                        <div className="p-4 bg-muted/50 rounded-lg">
                                            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Est. Rating</p>
                                            <p className="text-2xl font-black">{analysisData?.summary?.estimated_rating || '-'}</p>
                                        </div>
                                    </div>
                                    <p className="text-sm text-muted-foreground italic">
                                        More detailed stats will appear here once the new analysis system processes this game.
                                    </p>
                                </div>
                            )}

                            {analysisData?.summary?.weaknesses && analysisData.summary.weaknesses.length > 0 && (
                                <div className="bg-card rounded-xl border overflow-hidden shadow-sm">
                                    <div className="bg-muted/50 px-4 py-2 border-b flex justify-between items-center">
                                        <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Key Areas for Improvement</span>
                                    </div>
                                    <div className="p-4 space-y-3">
                                        {analysisData.summary.weaknesses.map((w, i) => (
                                            <div key={i} className="flex gap-3 p-3 bg-muted/30 rounded-lg border border-muted/50 items-start group hover:bg-muted/50 transition-colors">
                                                <div className="p-1.5 bg-background rounded border border-muted mt-0.5 shadow-sm group-hover:scale-110 transition-transform">
                                                    <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />
                                                </div>
                                                <p className="text-sm font-medium leading-relaxed">{w}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </Tabs.Content>
                </Tabs.Root >
            </div >
        </div >
    );
};

export default GameView;
