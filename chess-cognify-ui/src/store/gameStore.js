import { create } from 'zustand';
import api from '../lib/api';

const useGameStore = create((set, get) => ({
    games: [],
    currentGame: null,
    analysisData: null,
    isLoading: false,
    error: null,

    // Fetch all games
    fetchGames: async () => {
        set({ isLoading: true });
        try {
            const response = await api.get('/api/games');
            const games = response.data;
            set((state) => {
                const updates = { games, isLoading: false };
                // Also update currentGame if it's in the list
                if (state.currentGame) {
                    const updatedCurrent = games.find(g => g.game_id === state.currentGame.game_id);
                    if (updatedCurrent) {
                        updates.currentGame = updatedCurrent;
                    }
                }
                return updates;
            });
        } catch (error) {
            set({ error: error.message, isLoading: false });
        }
    },

    // Upload PGN
    uploadGame: async (pgn) => {
        set({ isLoading: true, error: null });
        try {
            const response = await api.post('/api/games/upload', { pgn });
            await get().fetchGames(); // Refresh list
            return response.data; // Returns game object with game_id
        } catch (error) {
            set({ error: error.message, isLoading: false });
            throw error;
        }
    },

    // Trigger Analysis (now backgrounded)
    analyzeGame: async (pgn) => {
        set({ isLoading: true, error: null });
        try {
            const response = await api.post('/api/games/analyze', { pgn });
            const game = response.data;

            // Update currentGame state with the new game info
            set({
                currentGame: game,
                isLoading: false
            });

            return game;
        } catch (error) {
            set({ error: error.message, isLoading: false });
            throw error;
        }
    },

    // Check individual game status
    checkAnalysisStatus: async (gameId) => {
        try {
            const response = await api.get(`/api/games/${gameId}`);
            const game = response.data;

            set((state) => ({
                currentGame: state.currentGame?.game_id === gameId ? game : state.currentGame,
                games: state.games.map(g => g.game_id === gameId ? game : g)
            }));

            // Fetch review data if completed OR currently analyzing
            // This allows "streaming" move-by-move updates
            if (game.status === 'completed' || game.status === 'analyzing') {
                const reviewRes = await api.get(`/api/games/${gameId}/review`);
                set({ analysisData: reviewRes.data });
            }

            if (game.status === 'failed') {
                set({ error: game.error_message || 'Analysis failed' });
                return 'failed';
            }

            return game.status;
        } catch (error) {
            console.error('Error checking status:', error);
            return 'error';
        }
    },

    // Get specific game details
    fetchGameDetails: async (gameId) => {
        set({ isLoading: true });
        try {
            const [gameRes, reviewRes] = await Promise.all([
                api.get(`/api/games/${gameId}`),
                // We attempt to get the review, might 404 if not analyzed yet
                api.get(`/api/games/${gameId}/review`).catch(() => ({ data: null }))
            ]);

            set({
                currentGame: gameRes.data,
                analysisData: reviewRes.data,
                isLoading: false
            });
        } catch (error) {
            set({ error: error.message, isLoading: false });
        }
    },

    // Delete Game
    deleteGame: async (gameId) => {
        try {
            await api.delete(`/api/games/${gameId}`);
            set((state) => ({
                games: state.games.filter(g => g.game_id !== gameId),
                currentGame: state.currentGame?.game_id === gameId ? null : state.currentGame
            }));
        } catch (error) {
            set({ error: error.message });
        }
    },

    // Rename Game (Update Metadata)
    renameGame: async (gameId, newTitle) => {
        try {
            const metadata = { title: newTitle };
            const response = await api.patch(`/api/games/${gameId}`, { metadata });
            set((state) => ({
                games: state.games.map(g => g.game_id === gameId ? response.data : g),
                currentGame: state.currentGame?.game_id === gameId ? response.data : state.currentGame
            }));
        } catch (error) {
            set({ error: error.message });
        }
    },

    // Update Game (Generic update for any fields)
    updateGame: async (gameId, updates) => {
        try {
            const response = await api.patch(`/api/games/${gameId}`, updates);
            set((state) => ({
                games: state.games.map(g => g.game_id === gameId ? response.data : g),
                currentGame: state.currentGame?.game_id === gameId ? response.data : state.currentGame
            }));
        } catch (error) {
            set({ error: error.message });
            throw error;
        }
    }
}));

export default useGameStore;
