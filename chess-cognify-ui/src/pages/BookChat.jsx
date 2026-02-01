import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Book, Bot, User, BookOpen, X, ChevronRight, Gamepad2, Loader2, ArrowLeft, AlertCircle, Activity, Quote, ChevronDown, ListTree } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import Chessboard from '@/components/Chessboard';
import api from '@/lib/api';
import useBookStore from '@/store/bookStore';
import { cn } from '@/lib/utils';

const BRANCH_COLORS = [
    'rgb(234 88 12)',    // orange-600
    'rgb(5 150 105)',    // emerald-600
    'rgb(225 29 72)',    // rose-600
    'rgb(124 58 237)',   // violet-600
    'rgb(37 99 235)',    // blue-600
];

const DocumentStructureTree = ({ mindmap }) => {
    const [rootExpanded, setRootExpanded] = useState(true);
    const children = mindmap?.children ?? [];
    const hasChildren = children.length > 0;
    const rootLabel = mindmap?.label || 'Document';

    return (
        <div className="select-none font-sans antialiased">
            {/* Tree: Document as root node on the trunk, one level above chapters */}
            {hasChildren ? (
                <div className="relative pl-0">
                    {/* Document node – root level: no circle, bolder text, subtle container (no outer trunk line) */}
                    <div className="relative flex min-h-0">
                        <div className="flex flex-col items-center shrink-0 pt-2" style={{ width: 24 }}>
                            {rootExpanded && (
                                <div className="w-1 flex-1 mt-0 rounded-full min-h-[4px] bg-primary/70" aria-hidden />
                            )}
                        </div>
                        <div className="flex-1 min-w-0 pl-3 pr-2 py-2 rounded-lg bg-primary/5 border-b border-primary/10 mb-1">
                            <button
                                type="button"
                                onClick={() => setRootExpanded((e) => !e)}
                                className={cn(
                                    "group flex items-center gap-2 w-full text-left py-2 pr-2 rounded-md transition-all duration-150",
                                    "hover:bg-primary/10 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-1",
                                    "cursor-pointer text-base font-bold text-foreground tracking-tight"
                                )}
                            >
                                <ChevronRight
                                    className={cn("w-5 h-5 shrink-0 text-primary/80 transition-transform duration-200", rootExpanded && "rotate-90")}
                                    aria-label={rootExpanded ? "Collapse" : "Expand"}
                                />
                                <span className="truncate flex-1 uppercase tracking-wide">{rootLabel}</span>
                            </button>
                        </div>
                    </div>
                    {/* Chapter nodes – visually nested under Document (indented); single trunk line only */}
                    {rootExpanded && (
                        <div className="relative space-y-0 ml-3 pl-1">
                            {children.map((child, i) => (
                                <MindmapNode
                                    key={i}
                                    node={child}
                                    depth={0}
                                    branchColor={BRANCH_COLORS[i % BRANCH_COLORS.length]}
                                    isFirst={i === 0}
                                    isLast={i === children.length - 1}
                                />
                            ))}
                        </div>
                    )}
                </div>
            ) : (
                <MindmapNode node={mindmap} depth={0} branchColor={BRANCH_COLORS[0]} />
            )}
        </div>
    );
};

const MindmapNode = ({ node, depth = 0, branchColor, isFirst, isLast }) => {
    const [expanded, setExpanded] = useState(depth < 1);
    const hasChildren = node?.children?.length > 0;
    const label = node?.label || '';
    const page = node?.page;
    const color = branchColor || 'rgb(148 163 184)';

    if (!node) return null;

    const isTopLevel = depth === 0;

    return (
        <div className="relative flex min-h-0">
            {/* Tree connector: visible circle + vertical line */}
            <div className="flex flex-col items-center shrink-0 pt-1.5" style={{ width: 20 }}>
                <div
                    className="w-3 h-3 rounded-full border-2 shrink-0 bg-background"
                    style={{ borderColor: color }}
                    aria-hidden
                />
                {hasChildren && expanded && (
                    <div
                        className="w-1 flex-1 mt-1 rounded-full min-h-[4px]"
                        style={{ backgroundColor: color }}
                        aria-hidden
                    />
                )}
            </div>
            <div className={cn("flex-1 min-w-0 pl-3 pb-1", isTopLevel && "pb-2.5")}>
                <button
                    type="button"
                    onClick={() => hasChildren && setExpanded((e) => !e)}
                    className={cn(
                        "group flex items-center gap-2 w-full text-left py-1.5 pr-2 rounded-md transition-all duration-150",
                        "hover:bg-muted/30 focus:outline-none focus:ring-1 focus:ring-primary/25 focus:ring-offset-0",
                        hasChildren && "cursor-pointer",
                        isTopLevel ? "text-sm font-medium text-foreground" : "text-xs text-muted-foreground leading-relaxed"
                    )}
                >
                    {hasChildren ? (
                        <ChevronRight
                            className={cn("w-4 h-4 shrink-0 text-muted-foreground/70 transition-transform duration-200", expanded && "rotate-90")}
                            aria-label={expanded ? "Collapse" : "Expand"}
                        />
                    ) : null}
                    <span className="truncate flex-1">{label}</span>
                    {page != null && (
                        <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground/60 font-medium">p.{page}</span>
                    )}
                </button>
                {hasChildren && expanded && (
                    <div
                        className="relative pl-4 ml-1 mt-0.5 space-y-0 min-h-[2px]"
                        style={{
                            borderLeft: `2px solid ${color}`,
                        }}
                    >
                        {node.children.map((child, i) => (
                            <MindmapNode
                                key={i}
                                node={child}
                                depth={depth + 1}
                                branchColor={color}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

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
    const [sessionId, setSessionId] = useState(null);  // Backend handles chat history; we send this for last 3 msgs.
    const [input, setInput] = useState("");
    const [isSending, setIsSending] = useState(false);
    const [mindmapOpen, setMindmapOpen] = useState(false);
    const [mindmap, setMindmap] = useState(null);
    const [mindmapLoading, setMindmapLoading] = useState(false);

    useEffect(() => {
        if (bookId) {
            fetchBookDetails(bookId);
        }
    }, [bookId, fetchBookDetails]);

    useEffect(() => {
        if (!mindmapOpen || !bookId) return;
        setMindmapLoading(true);
        api.get(`/api/books/${bookId}/mindmap`)
            .then((res) => {
                setMindmap(res.data.mindmap ?? null);
            })
            .catch(() => {
                setMindmap(null);
            })
            .finally(() => setMindmapLoading(false));
    }, [mindmapOpen, bookId]);

    const handleSend = async () => {
        if (!input.trim() || isSending) return;

        const userMsg = input;
        setInput("");
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsSending(true);

        try {
            const response = await api.post(`/api/books/${bookId}/query`, {
                query: userMsg,
                session_id: sessionId ?? undefined,
            });
            const data = response.data;
            if (data.session_id) setSessionId(data.session_id);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.answer,
                chess_data: data.chess_data,
                sources: data.sources,
                images: data.images,
                vlm_summaries: data.vlm_summaries,
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
                    <Button variant="outline" size="sm" onClick={() => setMindmapOpen(true)} title="Document structure & suggested questions">
                        <ListTree className="w-4 h-4 mr-1" />
                        Mindmap
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => { setMessages([]); setSessionId(null); }}>
                        Clear Chat
                    </Button>
                </div>
            </div>

            <div className="flex flex-1 overflow-hidden min-h-0">
            {/* Chat Body */}
            <div className={cn("flex-1 overflow-hidden relative container mx-auto max-w-4xl flex flex-col my-4 rounded-xl shadow-sm min-w-0", mindmapOpen && "mr-0")}>
                <>
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
                                    <div className={cn(
                                        'rounded-xl p-4 text-sm leading-relaxed shadow-sm',
                                        msg.role === 'user' ? 'bg-primary text-primary-foreground whitespace-pre-wrap' : 'bg-white border'
                                    )}>
                                        {msg.role === 'user' ? (
                                            msg.content
                                        ) : (
                                            <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:mt-4 prose-headings:mb-2 prose-pre:my-2 prose-pre:bg-muted prose-pre:rounded-lg prose-pre:p-3 prose-code:bg-muted prose-code:px-1 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {String(msg.content ?? '')}
                                                </ReactMarkdown>
                                            </div>
                                        )}

                                        {/* Sources Section for Assistant */}
                                        {msg.role === 'assistant' && <SourceSection sources={msg.sources} />}

                                        {/* Single section: Retrieved Book Diagrams & Vision Analysis (images + FEN-only positions, all with titles) */}
                                        {msg.role === 'assistant' && (() => {
                                            const hasImages = msg.images && msg.images.length > 0;
                                            const imageUrls = new Set(msg.images || []);
                                            const fenOnlyCards = (msg.chess_data && Array.isArray(msg.chess_data))
                                                ? msg.chess_data.filter(chess => !chess.image_url || !imageUrls.has(chess.image_url))
                                                : [];
                                            const hasFenOnly = fenOnlyCards.length > 0;
                                            if (!hasImages && !hasFenOnly) return null;
                                            return (
                                            <div className="mt-4 pt-4 border-t space-y-4">
                                                <p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground/60 flex items-center gap-2">
                                                    <BookOpen className="w-3 h-3" />
                                                    Retrieved Book Diagrams & Vision Analysis
                                                </p>
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                    {msg.images?.map((imgUrl, idx) => {
                                                        const matchingChess = msg.chess_data?.find(c => c.image_url === imgUrl);
                                                        const title = matchingChess?.description || `Diagram ${idx + 1}`;
                                                        const notation = matchingChess?.pgn || (matchingChess?.moves ? matchingChess.moves.join(' ') : null);
                                                        return (
                                                            <div key={`img-${idx}`} className="flex flex-col gap-3 bg-muted/20 rounded-xl border p-3 group">
                                                                <h4 className="text-sm font-bold uppercase tracking-wide text-foreground">
                                                                    {title}
                                                                </h4>
                                                                <div className="aspect-square bg-white rounded-lg border overflow-hidden relative cursor-zoom-in">
                                                                    <img
                                                                        src={imgUrl}
                                                                        alt={title}
                                                                        className="w-full h-full object-contain transition-transform group-hover:scale-105"
                                                                        onClick={() => window.open(imgUrl, '_blank')}
                                                                    />
                                                                    <div className="absolute top-2 right-2">
                                                                        <div className="bg-black/50 backdrop-blur-sm text-white text-[8px] px-1.5 py-0.5 rounded font-bold">
                                                                            Page {msg.sources?.find(s => s.metadata.image_urls?.includes(imgUrl) || s.metadata.image_url === imgUrl)?.metadata.page || '?'}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                                {notation && (
                                                                    <div className="space-y-1.5">
                                                                        <p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground/60">Sequence / Notation</p>
                                                                        <div className="text-xs font-mono text-foreground p-3 bg-muted rounded-lg border leading-relaxed break-all">
                                                                            {notation}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                                {msg.vlm_summaries?.[imgUrl] && (
                                                                    <div className="space-y-2">
                                                                        <div className="flex items-center gap-2">
                                                                            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                                                                            <p className="text-[8px] font-black uppercase tracking-widest text-primary/70">Technical Summary (VLM)</p>
                                                                        </div>
                                                                        <p className="text-[11px] leading-relaxed text-muted-foreground font-medium italic">
                                                                            "{msg.vlm_summaries[imgUrl]}"
                                                                        </p>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        );
                                                    })}
                                                    {fenOnlyCards.map((chess, idx) => {
                                                        const notation = chess.pgn || (chess.moves ? chess.moves.join(' ') : null);
                                                        const title = chess.description || `Position ${idx + 1}`;
                                                        return (
                                                            <div key={`fen-${idx}`} className="flex flex-col gap-3 bg-muted/20 rounded-xl border p-3 group">
                                                                <h4 className="text-sm font-bold uppercase tracking-wide text-foreground">
                                                                    {title}
                                                                </h4>
                                                                <div className="aspect-square bg-white rounded-lg border overflow-hidden">
                                                                    <Chessboard
                                                                        fen={chess.fen}
                                                                        viewOnly={true}
                                                                    />
                                                                </div>
                                                                {notation && (
                                                                    <div className="space-y-1.5">
                                                                        <p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground/60">Sequence / Notation</p>
                                                                        <div className="text-xs font-mono text-foreground p-3 bg-muted rounded-lg border leading-relaxed break-all">
                                                                            {notation}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                            );
                                        })()}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {isSending && (
                            <div className="flex gap-4">
                                <div className="w-10 h-10 rounded-full bg-white text-primary border flex items-center justify-center shadow-sm">
                                    <Bot className="w-5 h-5" />
                                </div>
                                <div className="bg-white border rounded-xl p-4 flex items-center gap-2 shadow-sm">
                                    <span className="text-xs text-muted-foreground animate-pulse flex items-center gap-2">
                                        <Activity className="w-3 h-3 animate-spin" />
                                        Analyzing diagrams & context...
                                    </span>
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
                </>
            </div>

            {/* Right sidebar: Mindmap / Document structure – 75% width, scrollable */}
            {mindmapOpen && (
                <div className="w-[75vw] max-w-[75vw] min-w-0 shrink-0 h-full flex flex-col overflow-hidden animate-in slide-in-from-right-5 duration-200 shadow-2xl border-l bg-card/95 backdrop-blur">
                    <div className="flex items-center justify-between p-4 border-b shrink-0">
                        <h2 className="text-base font-bold flex items-center gap-2">
                            <ListTree className="w-5 h-5 text-primary" />
                            Document structure
                        </h2>
                        <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => setMindmapOpen(false)} title="Close">
                            <X className="w-5 h-5" />
                        </Button>
                    </div>
                    <ScrollArea className="flex-1 min-h-0 p-6">
                        {mindmapLoading ? (
                            <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
                                <Loader2 className="w-6 h-6 animate-spin mr-2" />
                                Loading...
                            </div>
                        ) : mindmap ? (
                            <div className="rounded-xl overflow-hidden bg-muted/20 dark:bg-muted/10 border border-border/50 p-6 min-h-[200px] pb-8 shadow-sm">
                                <DocumentStructureTree mindmap={mindmap} />
                            </div>
                        ) : (
                            <p className="text-sm text-muted-foreground py-8">No document structure available for this book.</p>
                        )}
                    </ScrollArea>
                </div>
            )}
            </div>
        </div>
    );
};

export default BookChat;

