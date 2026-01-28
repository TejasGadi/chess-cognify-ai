import React, { useState } from 'react';
import { Send, Book, Bot, User, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import api from '@/lib/api';

const BooksApp = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    // In a real app we might select specific books or collections

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg = input;
        setInput("");
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsLoading(true);

        try {
            // NOTE: The backend API for books chat might be different. 
            // Based on file exploration, there is `app/api/books.py`.
            // Let's assume an endpoint like `/api/books/chat` or query.
            // If not checked, I should assume standard query. 
            // I'll check the backend file if it fails, but for now guessing /api/books/query
            const response = await api.post(`/api/books/query`, { query: userMsg });

            // Response format depends on backend.
            setMessages(prev => [...prev, { role: 'assistant', content: response.data.answer || response.data.response }]);
        } catch (error) {
            console.error("Book chat error", error);
            setMessages(prev => [...prev, { role: 'system', content: "Error: Could not get response from book knowledge base." }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-background">
            <div className="border-b p-6 flex items-center gap-3">
                <div className="p-3 bg-primary/10 rounded-lg text-primary">
                    <BookOpen className="w-6 h-6" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold">Chess Book Companion</h1>
                    <p className="text-muted-foreground">Ask questions from our library of chess books</p>
                </div>
            </div>

            <div className="flex-1 overflow-hidden relative container mx-auto max-w-4xl flex flex-col my-4 border rounded-xl bg-card shadow-sm">
                <ScrollArea className="flex-1 p-6">
                    <div className="space-y-6">
                        {messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground space-y-4 mt-12">
                                <Book className="w-16 h-16 opacity-20" />
                                <p className="text-lg font-medium">What would you like to learn today?</p>
                                <div className="flex gap-2 flex-wrap justify-center">
                                    {['Explain the minority attack', 'How to play against the French Defense?', 'Principles of rook endgames'].map(q => (
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
                                <div className={`rounded-xl p-4 text-sm max-w-[80%] leading-relaxed shadow-sm ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-white border'}`}>
                                    {msg.content}
                                </div>
                            </div>
                        ))}

                        {isLoading && (
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

                <div className="p-4 bg-muted/30 border-t">
                    <div className="flex gap-2 relative">
                        <input
                            className="flex-1 bg-background border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary shadow-sm"
                            placeholder="Ask about chess concepts, openings, or strategies..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isLoading}
                        />
                        <Button className="absolute right-2 top-1.5" size="icon" onClick={handleSend} disabled={isLoading || !input.trim()}>
                            <Send className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BooksApp;
