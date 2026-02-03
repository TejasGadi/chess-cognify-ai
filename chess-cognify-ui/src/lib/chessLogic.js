import { parsePgn } from 'chessops/pgn';
import { Chess } from 'chessops/chess';
import { makeUci, makeSquare, parseUci } from 'chessops/util';
import { makeFen, parseFen } from 'chessops/fen';
import { parseSan, makeSan } from 'chessops/san';

// Helper to parse PGN and get all positions (FENs) and moves
export function parseGame(pgn) {
    if (!pgn) return { moves: [], positions: ['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'], headers: {} };

    try {
        const games = parsePgn(pgn);
        if (games.length === 0) return { moves: [], positions: [], headers: {} };

        const game = games[0];
        const headers = game.headers;

        // Replay game to get FENs
        const position = Chess.default();
        const positions = [makeFen(position.toSetup())];
        const moves = [];

        for (const node of game.moves.mainline()) {
            const move = parseSan(position, node.san);
            if (!move) {
                console.error("Invalid move in PGN:", node.san);
                break;
            }

            const uci = makeUci(move);
            position.play(move);
            const fen = makeFen(position.toSetup());
            positions.push(fen);

            moves.push({
                uci,
                san: node.san,
                ply: moves.length + 1,
                fen: fen
            });
        }

        return {
            headers,
            moves,
            positions
        };
    } catch (e) {
        console.error("PGN Parse Error", e);
        return { moves: [], positions: ['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'], headers: {} };
    }
}

/**
 * Apply a UCI move to a position and return the new FEN (for Analysis Board).
 * Handles promotion: 5-char UCI (e.g. e7e8q); if pawn to last rank and UCI is 4 chars, defaults to queen.
 * @param {string} fen - Current position FEN
 * @param {string} uci - Move in UCI format (e.g. "e2e4" or "e7e8q")
 * @returns {string|null} New FEN after the move, or null if invalid
 */
export function applyMove(fen, uci) {
    try {
        const setup = parseFen(fen).unwrap();
        const position = Chess.fromSetup(setup).unwrap();
        let move = parseUci(uci);
        if (!move && uci.length === 4) {
            move = parseUci(uci + 'q');
        }
        if (!move) return null;
        position.play(move);
        return makeFen(position.toSetup());
    } catch (e) {
        console.error("applyMove Error", e, "FEN:", fen, "UCI:", uci);
        return null;
    }
}

/**
 * Convert UCI move to SAN for a given FEN (for Analysis Board move list).
 * @param {string} fen - Position FEN before the move
 * @param {string} uci - Move in UCI format
 * @returns {string|null} SAN string or null if invalid
 */
export function uciToSan(fen, uci) {
    try {
        const setup = parseFen(fen).unwrap();
        const position = Chess.fromSetup(setup).unwrap();
        let move = parseUci(uci);
        if (!move && uci.length === 4) move = parseUci(uci + 'q');
        if (!move) return null;
        return makeSan(position, move);
    } catch (e) {
        return null;
    }
}

// Helper to get legal moves for chessground
export function getDests(fen) {
    try {
        const setup = parseFen(fen).unwrap();
        const position = Chess.fromSetup(setup).unwrap();
        const dests = new Map();

        for (const [from, toSet] of position.allDests()) {
            const fromSq = makeSquare(from);
            const toSqs = [];
            for (const to of toSet) {
                toSqs.push(makeSquare(to));
            }
            if (toSqs.length > 0) {
                dests.set(fromSq, toSqs);
            }
        }
        return dests;
    } catch (e) {
        console.error("Dests Error", e, "FEN:", fen);
        return new Map();
    }
}
/**
 * Generate a PGN string from a list of SAN moves and optional headers.
 * @param {Array} moves - Array of { san, ... }
 * @param {Object} headers - Dictionary of PGN headers
 * @returns {string} PGN string
 */
export function generatePgn(moves, headers = {}) {
    let pgn = "";

    // Default headers if not provided
    const h = {
        Event: "Self Analysis",
        Site: "Chess Cognify AI",
        Date: new Date().toISOString().split('T')[0].replace(/-/g, '.'),
        Round: "?",
        White: "Player",
        Black: "Stockfish",
        Result: "*",
        ...headers
    };

    for (const [key, value] of Object.entries(h)) {
        pgn += `[${key} "${value}"]\n`;
    }
    pgn += "\n";

    // Add moves
    for (let i = 0; i < moves.length; i++) {
        if (i % 2 === 0) {
            pgn += `${Math.floor(i / 2) + 1}. `;
        }
        pgn += `${moves[i].san} `;
    }

    return pgn.trim();
}
