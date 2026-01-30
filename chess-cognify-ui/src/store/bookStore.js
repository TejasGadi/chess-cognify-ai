import { create } from 'zustand';
import api from '../lib/api';

const useBookStore = create((set, get) => ({
    books: [],
    currentBook: null,
    isLoading: false,
    error: null,

    // Fetch all books
    fetchBooks: async () => {
        set({ isLoading: true });
        try {
            const response = await api.get('/api/books');
            const books = response.data;
            set((state) => {
                const updates = { books, isLoading: false };
                // Also update currentBook if it's in the list
                if (state.currentBook) {
                    const updatedCurrent = books.find(b => b.book_id === state.currentBook.book_id);
                    if (updatedCurrent) {
                        updates.currentBook = updatedCurrent;
                    }
                }
                return updates;
            });
        } catch (error) {
            set({ error: error.message, isLoading: false });
        }
    },

    // Upload Book
    uploadBook: async (file) => {
        set({ isLoading: true, error: null });
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await api.post('/api/books/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            await get().fetchBooks(); // Refresh list
            return response.data; // { message, book_id, filename }
        } catch (error) {
            set({ error: error.message, isLoading: false });
            throw error;
        }
    },

    // Get specific book details
    fetchBookDetails: async (bookId) => {
        set({ isLoading: true });
        try {
            const response = await api.get(`/api/books/${bookId}`);
            set({
                currentBook: response.data,
                isLoading: false
            });
        } catch (error) {
            set({ error: error.message, isLoading: false });
        }
    },

    // Check individual book status
    checkBookStatus: async (bookId) => {
        try {
            const response = await api.get(`/api/books/${bookId}/status`);
            const statusData = response.data; // { status, message, filename, chunks }

            set((state) => {
                const updatedBooks = state.books.map(b =>
                    b.book_id === bookId ? { ...b, status: statusData.status, error_message: statusData.error } : b
                );

                const updates = { books: updatedBooks };

                if (state.currentBook?.book_id === bookId) {
                    updates.currentBook = { ...state.currentBook, status: statusData.status, error_message: statusData.error };
                }

                return updates;
            });

            return statusData.status;
        } catch (error) {
            console.error('Error checking status:', error);
            return 'error';
        }
    },

    // Delete Book
    deleteBook: async (bookId) => {
        try {
            await api.delete(`/api/books/${bookId}`);
            set((state) => ({
                books: state.books.filter(b => b.book_id !== bookId),
                currentBook: state.currentBook?.book_id === bookId ? null : state.currentBook
            }));
        } catch (error) {
            set({ error: error.message });
        }
    }
}));

export default useBookStore;
