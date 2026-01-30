import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, Book, Bot, User, BookOpen, Upload, FileText, X, ChevronRight, Gamepad2, Loader2, ArrowLeft, AlertCircle, Activity, Quote, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import Chessboard from '@/components/Chessboard';
import api from '@/lib/api';
import useBookStore from '@/store/bookStore';
import { cn } from '@/lib/utils';

const SourceSection = ({ sources }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!sources || sources.length === 0) return null;

    return (
        <div className="mt-3 w-full border-t pt-3">
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70 hover:text-primary transition-colors mb-1"
            >
                <Quote className="w-3 h-3" />
                {sources.length} Sources & Citations
                <ChevronDown className={cn("w-3 h-3 transition-transform", isExpanded && "rotate-180")} />
            </button>

            {isExpanded && (
                <div className="space-y-2 mt-2 animate-in slide-in-from-top-1 duration-200">
                    {sources.map((source, idx) => (
                        <div key={idx} className="p-3 bg-muted/30 rounded-lg border border-border/50 text-[11px] leading-relaxed text-muted-foreground italic relative group overflow-hidden">
                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary/20 group-hover:bg-primary/50 transition-colors" />
                            {source.content}
                            {source.metadata?.source && (
                                <div className="mt-1 font-bold not-italic opacity-50 text-[9px]">
                                    Source: {source.metadata.source}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const BookChat = () => {
    const { bookId } = useParams();
    const navigate = useNavigate();
    const { currentBook, fetchBookDetails, isLoading: isBookLoading } = useBookStore();

    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isSending, setIsSending] = useState(false);

    useEffect(() => {
        if (bookId) {
            fetchBookDetails(bookId);
        }
    }, [bookId, fetchBookDetails]);

    const handleSend = async () => {
        if (!input.trim() || isSending) return;

        const userMsg = input;
        setInput("");
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsSending(true);

        try {
            const response = await api.post(`/api/books/${bookId}/query`, { query: userMsg });
            const data = response.data;
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.answer,
                chess_data: data.chess_data,
                sources: data.sources
            }]);
        } catch (error) {
            console.error("Book chat error", error);
            setMessages(prev => [...prev, { role: 'system', content: "Error: Could not get response from book knowledge base." }]);
        } finally {
            setIsSending(false);
        }
    };

    if (isBookLoading && !currentBook) {
        return (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center">
                <Activity className="h-10 w-10 text-primary animate-spin mb-4" />
                <p className="text-muted-foreground">Loading book knowledge base...</p>
            </div>
        );
    }

    if (!currentBook && !isBookLoading) {
        return (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center space-y-4">
                <div className="p-4 bg-destructive/10 text-destructive rounded-full">
                    <AlertCircle className="w-8 h-8" />
                </div>
                <h2 className="text-xl font-bold">Book Not Found</h2>
                <p className="text-muted-foreground max-w-xs">
                    The book you're looking for doesn't exist or has been removed.
                </p>
                <Button onClick={() => navigate('/books')}>Back to Library</Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-background relative">
            {/* Header */}
            <div className="border-b p-4 flex items-center justify-between shrink-0 bg-card/50 backdrop-blur sticky top-0 z-10">
                <div className="flex items-center gap-3 min-w-0">
                    <Button variant="ghost" size="icon" onClick={() => navigate('/books')} className="h-8 w-8">
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <div className="p-2 bg-primary/10 rounded-lg text-primary shrink-0">
                        <BookOpen className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                        <h1 className="text-lg font-bold flex items-center gap-2 truncate">
                            {currentBook?.title || "Chess Book"}
                            <span className="text-[10px] bg-green-500/10 text-green-600 px-2 py-0.5 rounded-full border border-green-500/20 uppercase tracking-wide shrink-0">Active</span>
                        </h1>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setMessages([])}>
                        Clear Chat
                    </Button>
                </div>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-hidden relative container mx-auto max-w-4xl flex flex-col my-4  rounded-xl shadow-sm">
                <ScrollArea className="flex-1 p-6">
                    <div className="space-y-8 min-h-full pb-4">
                        {messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center p-12 text-center text-muted-foreground space-y-4">
                                <Bot className="w-12 h-12 opacity-20" />
                                <p className="text-lg font-medium">Ready to discuss "{currentBook?.title}"</p>
                                <p className="text-sm max-w-xs mx-auto">
                                    Ask me anything about the strategies, openings, or tactical patterns discussed in this book.
                                </p>
                                <div className="flex gap-2 flex-wrap justify-center mt-2">
                                    {['Explain the main concepts', 'Show me a tactical example', 'Key takeaways from this book'].map(q => (
                                        <Button key={q} variant="outline" size="sm" onClick={() => setInput(q)}>
                                            {q}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div key={i} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-sm ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-white text-primary border'}`}>
                                    {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                                </div>
                                <div className={`flex flex-col gap-2 max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                    <div className={`rounded-xl p-4 text-sm leading-relaxed shadow-sm whitespace-pre-wrap ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-white border'}`}>
                                        {msg.content}

                                        {/* Sources Section for Assistant */}
                                        {msg.role === 'assistant' && <SourceSection sources={msg.sources} />}
                                    </div>

                                    {/* Render Chess Board if chess_data is present */}
                                    {msg.chess_data && (msg.chess_data.fen || msg.chess_data.pgn) && (
                                        <Card className="w-full max-w-sm mt-2 p-3 bg-card border shadow-sm">
                                            <div className="flex items-center gap-2 mb-2 pb-2 border-b">
                                                <Gamepad2 className="w-4 h-4 text-primary" />
                                                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                                    {msg.chess_data.description || "Position Reference"}
                                                </span>
                                            </div>
                                            <div className="aspect-square rounded overflow-hidden bg-muted/20 border">
                                                <Chessboard
                                                    fen={msg.chess_data.fen}
                                                    viewOnly={true}
                                                />
                                            </div>
                                            {(msg.chess_data.moves || msg.chess_data.pgn) && (
                                                <div className="mt-2 text-xs font-mono text-muted-foreground p-2 bg-muted rounded">
                                                    {msg.chess_data.pgn || (msg.chess_data.moves ? msg.chess_data.moves.join(' ') : '')}
                                                </div>
                                            )}
                                        </Card>
                                    )}
                                </div>
                            </div>
                        ))}

                        {isSending && (
                            <div className="flex gap-4">
                                <div className="w-10 h-10 rounded-full bg-white text-primary border flex items-center justify-center shadow-sm">
                                    <Bot className="w-5 h-5" />
                                </div>
                                <div className="bg-white border rounded-xl p-4 flex items-center gap-2 shadow-sm">
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.2s]" />
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.4s]" />
                                </div>
                            </div>
                        )}
                    </div>
                </ScrollArea>

                {/* Input Area */}
                <div className="p-4 bg-muted/30 border-t mt-4 rounded-b-xl">
                    <div className="flex gap-2 relative">
                        <input
                            className="flex-1 bg-background border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary shadow-sm"
                            placeholder="Ask about chess concepts, openings, or strategies..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isSending}
                        />
                        <Button className="absolute right-2 top-1.5" size="icon" onClick={handleSend} disabled={isSending || !input.trim()}>
                            <Send className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BookChat;

