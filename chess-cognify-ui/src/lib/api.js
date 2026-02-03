import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 900000, // 15 minutes
});

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error.response || error.message);
        return Promise.reject(error);
    }
);

/**
 * Evaluate a chess position using Stockfish
 * @param {string} fen - FEN position string
 * @param {number} depth - Analysis depth (default: 15)
 * @returns {Promise} Evaluation data
 */
export const evaluatePosition = async (fen, depth = 15) => {
    const response = await api.post('/api/evaluate', { fen, depth });
    return response.data;
};

/**
 * Evaluate position and get top engine lines (for Analysis Board)
 * @param {string} fen - FEN position string
 * @param {number} depth - Analysis depth (default: 15)
 * @param {number} multipv - Number of top lines (default: 5)
 * @returns {Promise} { eval_cp, mate, top_moves, last_move_san, ... }
 */
export const evaluatePositionWithLines = async (fen, depth = 15, multipv = 5) => {
    const response = await api.post('/api/evaluate', { fen, depth, multipv });
    return response.data;
};

export default api;

