import React from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

const MoveList = ({ moves, currentPly, onMoveSelect }) => {
    // Group moves into pairs (White, Black)
    const pairs = [];
    for (let i = 0; i < moves.length; i += 2) {
        pairs.push({
            number: Math.floor(i / 2) + 1,
            white: moves[i],
            black: moves[i + 1]
        });
    }

    return (
        <ScrollArea className="h-full w-full bg-background rounded-md border">
            <div className="w-full text-sm">
                {pairs.map((pair, index) => (
                    <div
                        key={index}
                        className={cn(
                            "flex items-stretch border-b last:border-0 hover:bg-muted/30 transition-colors",
                            index % 2 === 0 ? "bg-background" : "bg-muted/10"
                        )}
                    >
                        {/* Move Number Column */}
                        <div className="w-12 flex-shrink-0 flex items-center justify-center bg-muted/30 text-muted-foreground font-mono text-xs border-r">
                            {pair.number}.
                        </div>

                        {/* White Move */}
                        <div
                            className={cn(
                                "flex-1 flex items-center px-4 py-2 cursor-pointer hover:bg-accent/50 transition-colors",
                                currentPly === pair.white?.ply
                                    ? "bg-primary/20 font-bold text-primary"
                                    : "text-foreground"
                            )}
                            onClick={() => onMoveSelect(pair.white?.ply)}
                        >
                            {pair.white?.san}
                        </div>

                        {/* Black Move */}
                        <div
                            className={cn(
                                "flex-1 flex items-center px-4 py-2 cursor-pointer border-l hover:bg-accent/50 transition-colors",
                                pair.black
                                    ? (currentPly === pair.black?.ply
                                        ? "bg-primary/20 font-bold text-primary"
                                        : "text-foreground")
                                    : "text-transparent"
                            )}
                            onClick={() => pair.black && onMoveSelect(pair.black?.ply)}
                        >
                            {pair.black?.san || "..."}
                        </div>
                    </div>
                ))}

                {/* Empty State / Spacer if list is short */}
                {pairs.length === 0 && (
                    <div className="p-8 text-center text-muted-foreground text-xs">
                        Moves will appear here
                    </div>
                )}
            </div>
        </ScrollArea>
    );
};

export default MoveList;
