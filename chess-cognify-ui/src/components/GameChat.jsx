import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import api from '@/lib/api';

const GameChat = ({ gameId }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef(null);
    const bottomRef = useRef(null);

    // Initial load? maybe not, history is fetched on demand usually. 
    // We can fetch history if needed.

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg = input;
        setInput("");
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsLoading(true);

        try {
            const response = await api.post(`/api/games/${gameId}/chat`, { message: userMsg });
            setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
        } catch (error) {
            console.error("Chat error", error);
            setMessages(prev => [...prev, { role: 'system', content: "Error: Could not get response." }]);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="flex flex-col h-full">
            <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                    {messages.length === 0 && (
                        <div className="text-center text-muted-foreground p-4">
                            Ask me anything about the game!
                        </div>
                    )}
                    {messages.map((msg, i) => (
                        <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary'}`}>
                                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                            </div>
                            <div className={`rounded-lg p-3 text-sm max-w-[80%] ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                                {msg.content}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex gap-3">
                            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                                <Bot className="w-4 h-4" />
                            </div>
                            <div className="bg-muted rounded-lg p-3 text-sm flex items-center gap-1">
                                <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>
            </ScrollArea>
            <div className="p-4 border-t flex gap-2">
                <input
                    className="flex-1 bg-background border rounded-md px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Ask a question..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    disabled={isLoading}
                />
                <Button size="icon" onClick={handleSend} disabled={isLoading || !input.trim()}>
                    <Send className="w-4 h-4" />
                </Button>
            </div>
        </div>
    );
};

export default GameChat;
