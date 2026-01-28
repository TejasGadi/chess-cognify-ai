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
        <ScrollArea className="h-full w-full">
            <div className="grid grid-cols-[3rem_1fr_1fr] text-sm">
                {pairs.map((pair, index) => (
                    <React.Fragment key={index}>
                        <div className="p-2 bg-muted/50 text-muted-foreground font-mono text-center border-b">
                            {pair.number}.
                        </div>
                        <div
                            className={cn(
                                "p-2 border-b cursor-pointer hover:bg-accent/50 transition-colors",
                                currentPly === pair.white?.ply ? "bg-primary/20 font-bold text-primary" : ""
                            )}
                            onClick={() => onMoveSelect(pair.white?.ply)}
                        >
                            {pair.white?.san}
                            {/* Annotation could go here */}
                        </div>
                        <div
                            className={cn(
                                "p-2 border-b cursor-pointer hover:bg-accent/50 transition-colors",
                                pair.black ? (currentPly === pair.black?.ply ? "bg-primary/20 font-bold text-primary" : "") : ""
                            )}
                            onClick={() => pair.black && onMoveSelect(pair.black?.ply)}
                        >
                            {pair.black?.san}
                        </div>
                    </React.Fragment>
                ))}
            </div>
        </ScrollArea>
    );
};

export default MoveList;
