import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
    ArrowRight, Brain, BookOpen, Search,
    Zap, Target, ShieldCheck, ChevronRight,
    Play, Gamepad2, Quote, Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

// Feature Card Component
const FeatureCard = ({ icon: Icon, title, description, delay }) => (
    <Card
        className={cn(
            "p-8 border-border/50 bg-card/50 backdrop-blur-sm hover:shadow-2xl hover:-translate-y-2 transition-all duration-500",
            "group relative overflow-hidden"
        )}
        style={{ animationDelay: `${delay}ms` }}
    >
        <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-bl-full -mr-12 -mt-12 group-hover:scale-150 transition-transform duration-700" />
        <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors duration-500 shadow-inner">
            <Icon className="h-7 w-7" />
        </div>
        <h3 className="mb-3 text-2xl font-bold tracking-tight">{title}</h3>
        <p className="text-muted-foreground leading-relaxed">
            {description}
        </p>
    </Card>
);

// Step Component
const Step = ({ number, title, description }) => (
    <div className="flex flex-col items-center text-center space-y-4 group">
        <div className="w-16 h-16 rounded-full border-4 border-muted bg-background flex items-center justify-center text-2xl font-black text-muted-foreground group-hover:border-primary group-hover:text-primary transition-all duration-500 shadow-xl group-hover:scale-110">
            {number}
        </div>
        <h4 className="text-xl font-bold">{title}</h4>
        <p className="text-sm text-muted-foreground max-w-[250px]">{description}</p>
    </div>
);

const Home = () => {
    const [heroImage, setHeroImage] = useState('');

    useEffect(() => {
        // In a real app, this would be a static asset
        // For this demo, we'll try to find the generated one or use a placeholder
        setHeroImage('/brain/93e59e69-8f6c-4a6e-862c-7dce43b6cc11/chess_ai_hero_background_1769814081798.png');
    }, []);

    return (
        <div className="relative w-full">
            {/* --- HERO SECTION --- */}
            <section className="relative min-h-[90vh] flex flex-col items-center justify-center px-6 overflow-hidden">
                {/* Background Decor */}
                <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
                    <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[120px] animate-pulse" />
                    <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
                    <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-[0.03]" />
                </div>

                {/* Hero Content */}
                <div className="container relative z-10 mx-auto text-center space-y-10 py-24">
                    <div className="space-y-4 animate-in fade-in slide-in-from-top-12 duration-1000">
                        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-bold uppercase tracking-widest mb-4 backdrop-blur-sm shadow-sm">
                            <Zap className="w-3 h-3 fill-primary" /> The Future of Chess Mastery
                        </div>
                        <h1 className="text-5xl md:text-8xl font-black tracking-tighter leading-[1] pb-2">
                            Transform Your Game with <br />
                            <span className="bg-gradient-to-r from-blue-600 via-primary to-purple-600 bg-clip-text text-transparent animate-gradient-x px-2">
                                Artificial Intelligence
                            </span>
                        </h1>
                        <p className="text-lg md:text-2xl text-muted-foreground max-w-3xl mx-auto font-medium leading-relaxed">
                            Analyze every move with grandmaster precision. Get deep natural language explanations
                            for why moves work, identify tactical patterns, and learn from 500+ year chess history.
                        </p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-6 animate-in fade-in slide-in-from-bottom-12 duration-1000 delay-300">
                        <Link to="/analysis">
                            <Button size="lg" className="h-16 px-10 text-xl font-bold rounded-2xl shadow-xl hover:shadow-primary/20 transition-all hover:-translate-y-1 active:scale-95 group">
                                Start Deep Analysis <ArrowRight className="ml-3 h-6 w-6 group-hover:translate-x-2 transition-transform" />
                            </Button>
                        </Link>
                        <Link to="/books">
                            <Button variant="outline" size="lg" className="h-16 px-10 text-xl font-bold rounded-2xl border-2 backdrop-blur-sm hover:bg-muted/50 transition-all hover:-translate-y-1 active:scale-95">
                                Browse Library
                            </Button>
                        </Link>
                    </div>

                    {/* Stats/Social Proof */}
                    <div className="pt-20 grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto animate-in fade-in duration-1000 delay-500 text-muted-foreground/60">
                        <div className="space-y-1">
                            <p className="text-3xl font-black text-foreground">Stockfish 16</p>
                            <p className="text-sm uppercase font-bold tracking-widest">Core Engine</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-3xl font-black text-foreground">GPT-4o</p>
                            <p className="text-sm uppercase font-bold tracking-widest">Reasoning Model</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-3xl font-black text-foreground">50k+</p>
                            <p className="text-sm uppercase font-bold tracking-widest">Game Database</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-3xl font-black text-foreground">0.1s</p>
                            <p className="text-sm uppercase font-bold tracking-widest">Low Latency</p>
                        </div>
                    </div>
                </div>

                {/* Hero Visual */}
                <div className="w-full max-w-6xl mx-auto px-6 mt-12 mb-[-100px] animate-in fade-in zoom-in-95 duration-1000 delay-700">
                    <div className="relative rounded-3xl overflow-hidden border-8 border-background shadow-[0_0_80px_rgba(0,0,0,0.3)] bg-muted/20 aspect-video">
                        <img
                            src={heroImage}
                            alt="Chess Cognify Dashboard"
                            className="w-full h-full object-cover"
                            onError={(e) => {
                                e.target.src = 'https://images.unsplash.com/photo-1528819622765-d6bcf132f793?q=80&w=2070&auto=format&fit=crop';
                            }}
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-background/40 to-transparent" />
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-24 h-24 rounded-full bg-primary/90 text-primary-foreground flex items-center justify-center shadow-2xl cursor-pointer hover:scale-110 transition-transform pulse-animation">
                                <Play className="w-10 h-10 fill-current ml-2" />
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* --- FEATURES SECTION --- */}
            <section id="features" className="py-32 relative bg-accent/30">
                <div className="container mx-auto px-6">
                    <div className="text-center max-w-3xl mx-auto mb-20 space-y-4">
                        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-primary">Advanced Capabilities</h2>
                        <h3 className="text-4xl md:text-5xl font-black tracking-tight">Level Up Your Chess Skill</h3>
                        <p className="text-muted-foreground text-lg">
                            We combine the raw power of Stockfish 16 with the intelligent reasoning of GPT-4o to provide an analysis experience unlike any other.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={Brain}
                            title="Semantic Analysis"
                            description="Don't just see numbers. Understand 'why' a move is a mistake or a brilliant choice with natural language explanations."
                            delay={100}
                        />
                        <FeatureCard
                            icon={BookOpen}
                            title="Book Companion"
                            description="Upload your chess library and chat with an AI grandmaster who knows every page, diagram, and concept in your collection."
                            delay={200}
                        />
                        <FeatureCard
                            icon={Activity}
                            title="Real-time Engine"
                            description="Experience lightning-fast analysis powered by Stockfish 16.1, providing depth and precision for every single position."
                            delay={300}
                        />
                    </div>
                </div>
            </section>

            {/* --- HOW IT WORKS --- */}
            <section id="how-it-works" className="py-32 bg-background border-y border-border/40">
                <div className="container mx-auto px-6">
                    <div className="flex flex-col md:flex-row items-center gap-16">
                        <div className="w-full md:w-1/2 space-y-8 text-center md:text-left">
                            <h2 className="text-xs font-black uppercase tracking-[0.2em] text-primary">Simple Workflow</h2>
                            <h3 className="text-4xl md:text-5xl font-black tracking-tight">How It Works</h3>
                            <p className="text-muted-foreground text-lg">
                                Mastering chess shouldn't be complicated. Our three-step process is designed to get you from beginner to expert efficiently.
                            </p>
                            <Link to="/analysis" className="inline-block">
                                <Button size="lg" className="rounded-xl px-8 group">
                                    Get Started Now <ChevronRight className="ml-2 group-hover:translate-x-1 transition-transform" />
                                </Button>
                            </Link>
                        </div>
                        <div className="w-full md:w-1/2 grid grid-cols-1 md:grid-cols-2 gap-12">
                            <Step
                                number="01"
                                title="Upload PGN"
                                description="Import your games from LiChess, Chess.com or paste a manual PGN string."
                            />
                            <Step
                                number="02"
                                title="Run Engine"
                                description="Our dedicated Stockfish servers crunch the numbers in milliseconds."
                            />
                            <Step
                                number="03"
                                title="Get Insights"
                                description="Read AI-generated commentary that actually speaks your language."
                            />
                            <Step
                                number="04"
                                title="Improve"
                                description="Study your mistakes and track your accuracy growth over time."
                            />
                        </div>
                    </div>
                </div>
            </section>

            {/* --- CALL TO ACTION --- */}
            <section className="py-32 relative overflow-hidden">
                <div className="container mx-auto px-6 relative z-10">
                    <div className="bg-primary rounded-[3rem] p-12 md:p-24 text-center text-primary-foreground shadow-2xl relative overflow-hidden border-8 border-primary/20">
                        {/* Background Decor */}
                        <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full -mr-48 -mt-48 blur-3xl animate-pulse" />
                        <div className="absolute bottom-0 left-0 w-96 h-96 bg-black/10 rounded-full -ml-48 -mb-48 blur-3xl animate-pulse" />

                        <div className="max-w-3xl mx-auto space-y-10 relative z-10">
                            <h2 className="text-4xl md:text-7xl font-black tracking-tighter leading-tight">
                                Ready to Play <br /> Better Chess?
                            </h2>
                            <p className="text-xl md:text-2xl opacity-90 font-medium">
                                Join thousands of players who are already using Chess Cognify to unlock their true potential. Start your journey today.
                            </p>
                            <div className="flex flex-col sm:flex-row items-center justify-center gap-6 pt-4">
                                <Link to="/analysis">
                                    <Button size="lg" variant="secondary" className="h-16 px-12 text-xl font-bold rounded-2xl shadow-xl hover:scale-105 transition-transform group">
                                        Analyze Your First Game <ArrowRight className="ml-2" />
                                    </Button>
                                </Link>
                                <Link to="/books/upload">
                                    <Button size="lg" variant="outline" className="h-16 px-12 text-xl font-bold rounded-2xl bg-white/5 border-white/20 hover:bg-white/10 shadow-lg hover:scale-105 transition-transform">
                                        Upload a Book
                                    </Button>
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes gradient-x {
                    0%, 100% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                }
                .animate-gradient-x {
                    background-size: 200% 200%;
                    animation: gradient-x 15s ease infinite;
                }
                .pulse-animation {
                    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
                }
                @keyframes pulse {
                    0%, 100% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.05); opacity: 0.8; }
                }
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: rgba(0,0,0,0.1);
                    border-radius: 10px;
                }
            `}} />
        </div>
    );
};

export default Home;
