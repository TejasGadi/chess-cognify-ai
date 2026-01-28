import React from 'react';
import { cn } from '@/lib/utils';

/**
 * EvalBar Component - Visual evaluation bar similar to Lichess/Chess.com
 * 
 * Displays Stockfish evaluation as:
 * - Visual bar (white at bottom, black at top)
 * - Numeric value (e.g., "+1.2" or "M3")
 * 
 * @param {Object} props
 * @param {number} props.evalCp - Evaluation in centipawns (positive = white advantage)
 * @param {number|null} props.mate - Mate in N moves (positive = white mates, negative = black mates)
 * @param {string} props.className - Additional CSS classes
 */
export function EvalBar({ evalCp = 0, mate = null, className }) {
    // Calculate bar percentage (0-100)
    // At eval=0, bar is 50% (equal)
    // At eval=+500 (5 pawns), bar is ~90% white
    // At eval=-500, bar is ~10% white
    const calculateBarPercentage = () => {
        if (mate !== null) {
            // Mate positions: show extreme advantage
            return mate > 0 ? 95 : 5;
        }

        // Convert centipawns to percentage using a sigmoid-like function
        // This prevents the bar from being too extreme at moderate advantages
        const pawns = evalCp / 100;
        const maxPawns = 5; // Cap at ±5 pawns for visual purposes
        const clampedPawns = Math.max(-maxPawns, Math.min(maxPawns, pawns));

        // Map -5 to 5 pawns to 5% to 95%
        const percentage = 50 + (clampedPawns / maxPawns) * 45;
        return Math.round(percentage);
    };

    // Format evaluation text
    const formatEval = () => {
        if (mate !== null) {
            const mateIn = Math.abs(mate);
            return mate > 0 ? `M${mateIn}` : `-M${mateIn}`;
        }

        const pawns = evalCp / 100;
        if (pawns >= 0) {
            return `+${pawns.toFixed(1)}`;
        }
        return pawns.toFixed(1);
    };

    const whitePercentage = calculateBarPercentage();
    const blackPercentage = 100 - whitePercentage;
    const evalText = formatEval();

    // Determine if eval should be shown on white or black side
    const showOnWhiteSide = evalCp >= 0 || (mate !== null && mate > 0);

    return (
        <div className={cn("flex flex-col h-full w-12 relative", className)}>
            {/* Evaluation Bar */}
            <div className="flex-1 flex flex-col border-2 border-border rounded-md overflow-hidden bg-background">
                {/* Black advantage (top) */}
                <div
                    className="bg-black transition-all duration-300 ease-out relative"
                    style={{ height: `${blackPercentage}%` }}
                >
                    {!showOnWhiteSide && blackPercentage > 15 && (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-white text-xs font-bold">
                                {evalText}
                            </span>
                        </div>
                    )}
                </div>

                {/* White advantage (bottom) */}
                <div
                    className="bg-white transition-all duration-300 ease-out relative"
                    style={{ height: `${whitePercentage}%` }}
                >
                    {showOnWhiteSide && whitePercentage > 15 && (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-black text-xs font-bold">
                                {evalText}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* Numeric evaluation below bar (always visible) */}
            <div className="mt-2 text-center">
                <span className={cn(
                    "text-sm font-mono font-semibold",
                    showOnWhiteSide ? "text-foreground" : "text-muted-foreground"
                )}>
                    {evalText}
                </span>
            </div>
        </div>
    );
}

export default EvalBar;
