import React, { useEffect, useRef, useState } from 'react';
import { Chessground as ChessgroundApi } from '@lichess-org/chessground';

// Import CSS directly from the package if available, or assume we copied them.
// Inspecting the package structure suggests checking for assets.
import '@lichess-org/chessground/assets/chessground.base.css';
import '@lichess-org/chessground/assets/chessground.brown.css';
import '@lichess-org/chessground/assets/chessground.cburnett.css';

const Chessboard = ({ fen, orientation = 'white', onMove, lastMove, check, ...props }) => {
    const ref = useRef(null);
    const [api, setApi] = useState(null);

    useEffect(() => {
        if (ref.current && !api) {
            const chessground = ChessgroundApi(ref.current, {
                fen: fen || 'start',
                orientation,
                events: {
                    move: (orig, dest) => {
                        if (onMove) onMove(orig, dest);
                    },
                },
                highlight: {
                    lastMove: true,
                    check: true,
                },
                movable: {
                    color: 'both',
                    free: false,
                    dests: undefined,
                    ...props.movable // allow overriding
                }
            });
            setApi(chessground);
        } else if (api) {
            // Update config
            api.set({
                fen: fen,
                orientation,
                lastMove: lastMove ? [lastMove.from, lastMove.to] : undefined,
                check: check,
                movable: {
                    color: 'both',
                    free: false,
                    dests: undefined,
                    ...props.movable
                }
            });
        }
    }, [fen, orientation, lastMove, check]);

    // Handle dests update if passed (for legality)
    // Logic to calculate dests should be outside or passed in.

    return (
        <div
            ref={ref}
            style={{ width: '100%', aspectRatio: '1' }}
            className="cg-wrap"
        />
    );
};

export default Chessboard;
