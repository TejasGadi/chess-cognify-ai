import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Plus, Trash2, Clock, Activity, AlertCircle, ChevronRight, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import useBookStore from '@/store/bookStore';
import { cn } from '@/lib/utils';

const BooksList = () => {
    const { books, fetchBooks, deleteBook, isLoading } = useBookStore();
    const navigate = useNavigate();

    useEffect(() => {
        fetchBooks();
    }, [fetchBooks]);

    // Periodically refresh if any book is processing
    useEffect(() => {
        const needsPolling = books.some(b => b.status === 'pending' || b.status === 'processing');
        let interval;

        if (needsPolling) {
            interval = setInterval(() => {
                fetchBooks();
            }, 3000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [books, fetchBooks]);

    const getStatusIcon = (status) => {
        switch (status) {
            case 'completed': return <Clock className="h-4 w-4 text-green-500" />;
            case 'processing':
            case 'pending': return <Activity className="h-4 w-4 text-primary animate-spin" />;
            case 'failed': return <AlertCircle className="h-4 w-4 text-destructive" />;
            default: return null;
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed': return "bg-green-500/10 text-green-500 border-green-500/20";
            case 'processing':
            case 'pending': return "bg-primary/10 text-primary border-primary/20";
            case 'failed': return "bg-destructive/10 text-destructive border-destructive/20";
            default: return "bg-muted text-muted-foreground border-border";
        }
    };

    return (
        <div className="container mx-auto max-w-5xl p-6 space-y-8">
            <div className="flex items-center justify-between pb-4 border-b">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Book Companion</h1>
                    <p className="text-muted-foreground mt-1">Chat with your chess library using AI</p>
                </div>
                <Button onClick={() => navigate('/books/upload')} className="gap-2">
                    <Plus className="h-4 w-4" /> Upload New Book
                </Button>
            </div>

            {isLoading && books.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-500">
                    <Activity className="h-10 w-10 text-primary animate-spin mb-4" />
                    <p className="text-muted-foreground">Loading your library...</p>
                </div>
            ) : books.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed rounded-2xl bg-muted/30 text-center animate-in zoom-in-95 duration-500">
                    <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mb-6">
                        <BookOpen className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">No books uploaded yet</h3>
                    <p className="text-muted-foreground max-w-sm mb-8">
                        Upload a chess PDF to start analyzing strategies and positions from your favorite books.
                    </p>
                    <Button onClick={() => navigate('/books/upload')} size="lg">
                        Upload your first book
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {books.map((book) => (
                        <Card
                            key={book.book_id}
                            className="group hover:shadow-lg transition-all border-border/50 hover:border-primary/50 overflow-hidden cursor-pointer flex flex-col h-full"
                            onClick={() => {
                                if (book.status === 'completed') {
                                    navigate(`/books/${book.book_id}`);
                                }
                            }}
                        >
                            <CardHeader className="pb-3">
                                <div className="flex justify-between items-start mb-2">
                                    <div className={cn(
                                        "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border",
                                        getStatusColor(book.status)
                                    )}>
                                        {book.status}
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 -mt-2 -mr-2 opacity-0 group-hover:opacity-100 transition-opacity"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            if (confirm(`Delete "${book.title}"?`)) {
                                                deleteBook(book.book_id);
                                            }
                                        }}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                                <CardTitle className="text-lg line-clamp-1 group-hover:text-primary transition-colors">
                                    {book.title}
                                </CardTitle>
                                <CardDescription className="flex items-center gap-1.5 mt-1">
                                    <FileText className="h-3 w-3" />
                                    {book.filename}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1 pb-4">
                                {book.status === 'completed' ? (
                                    <p className="text-sm text-muted-foreground">
                                        {book.total_chunks || 0} knowledge chunks generated. Ready for chat.
                                    </p>
                                ) : book.status === 'failed' ? (
                                    <p className="text-sm text-destructive line-clamp-2">
                                        Error: {book.error_message || 'Unknown error'}
                                    </p>
                                ) : (
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                        <Activity className="h-3 w-3 animate-spin text-primary" />
                                        <span>Analyzing PDF structure...</span>
                                    </div>
                                )}
                            </CardContent>
                            <CardFooter className="pt-0 border-t bg-muted/30 group-hover:bg-primary/5 transition-colors">
                                <div className="flex items-center justify-between w-full py-3 text-xs font-medium">
                                    <span className="text-muted-foreground">
                                        {new Date(book.created_at).toLocaleDateString()}
                                    </span>
                                    {book.status === 'completed' && (
                                        <span className="flex items-center gap-1 text-primary group-hover:translate-x-1 transition-transform">
                                            Open Chat <ChevronRight className="h-3 w-3" />
                                        </span>
                                    )}
                                </div>
                            </CardFooter>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
};

export default BooksList;
