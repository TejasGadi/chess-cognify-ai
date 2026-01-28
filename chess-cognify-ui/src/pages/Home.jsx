import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowRight, Brain, BookOpen } from 'lucide-react';

const Home = () => {
    return (
        <div className="flex flex-col items-center justify-center min-h-full p-8 md:p-24 text-center space-y-12">
            <div className="space-y-6 max-w-3xl">
                <h1 className="text-4xl md:text-6xl font-extrabold tracking-tighter bg-gradient-to-r from-white to-gray-500 bg-clip-text text-transparent">
                    Master Your Chess Game with AI
                </h1>
                <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
                    Analyze your games with Stockfish engine and get natural language explanations for every move.
                    Identify your weaknesses and learn from your mistakes.
                </p>
                <div className="flex items-center justify-center gap-4">
                    <Link to="/analysis">
                        <Button size="lg" className="h-12 px-8 text-lg">
                            Analyze Game <ArrowRight className="ml-2 h-5 w-5" />
                        </Button>
                    </Link>
                    <Link to="/books">
                        <Button variant="outline" size="lg" className="h-12 px-8 text-lg">
                            Explore Books
                        </Button>
                    </Link>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl w-full mt-12">
                <div className="rounded-xl border bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
                    <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Brain className="h-6 w-6" />
                    </div>
                    <h3 className="mb-2 text-xl font-bold">Deep Analysis</h3>
                    <p className="text-muted-foreground">
                        Get move-by-move explanations, brilliant move detection, and accuracy scoring powered by advanced engines.
                    </p>
                </div>
                <div className="rounded-xl border bg-card p-6 shadow-sm hover:shadow-md transition-shadow">
                    <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <BookOpen className="h-6 w-6" />
                    </div>
                    <h3 className="mb-2 text-xl font-bold">Book Knowledge</h3>
                    <p className="text-muted-foreground">
                        Chat with our AI about classic chess books and strategies to improve your theoretical understanding.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Home;
