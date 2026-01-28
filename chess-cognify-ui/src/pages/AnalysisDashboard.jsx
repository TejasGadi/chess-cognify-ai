import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import useGameStore from '@/store/gameStore';

const AnalysisDashboard = () => {
    const [pgn, setPgn] = useState('');
    const [isDragOver, setIsDragOver] = useState(false);
    const { uploadGame, isLoading, analyzeGame } = useGameStore();
    const navigate = useNavigate();
    const [error, setError] = useState(null);

    const handleAnalyze = async () => {
        if (!pgn.trim()) return;
        setError(null);
        try {
            // Trigger Analysis (now handles upload and background analysis in one shot)
            const gameData = await analyzeGame(pgn);

            // Navigate immediately to the game view where polling takes over
            if (gameData && gameData.game_id) {
                navigate(`/analysis/${gameData.game_id}`);
            } else {
                setError("Failed to start analysis. No game ID returned.");
            }
        } catch (err) {
            console.error("Analysis trigger failed:", err);
            setError(err.response?.data?.detail || "Analysis failed to start. Please check your PGN format.");
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => setPgn(e.target.result);
            reader.readAsText(file);
        }
    };

    return (
        <div className="container mx-auto max-w-4xl p-8">
            <h1 className="text-3xl font-bold mb-8">New Analysis</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                    <div
                        className={`border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center text-center transition-colors
                    ${isDragOver ? 'border-primary bg-primary/10' : 'border-border bg-card hover:bg-accent/50'}
                `}
                        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                        onDragLeave={() => setIsDragOver(false)}
                        onDrop={handleDrop}
                    >
                        <Upload className="w-12 h-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-semibold mb-2">Upload PGN File</h3>
                        <p className="text-sm text-muted-foreground mb-4">Drag and drop your game file here</p>
                        <input
                            type="file"
                            id="pgn-upload"
                            className="hidden"
                            accept=".pgn"
                            onChange={(e) => {
                                const file = e.target.files[0];
                                if (file) {
                                    const reader = new FileReader();
                                    reader.onload = (e) => setPgn(e.target.result);
                                    reader.readAsText(file);
                                }
                            }}
                        />
                        <Button variant="outline" onClick={() => document.getElementById('pgn-upload').click()}>
                            Browse Files
                        </Button>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="bg-card border rounded-xl p-6 h-full flex flex-col">
                        <div className="flex items-center gap-2 mb-4">
                            <FileText className="w-5 h-5 text-primary" />
                            <h3 className="text-lg font-semibold">Paste PGN Text</h3>
                        </div>
                        <textarea
                            className="flex-1 w-full min-h-[200px] p-4 rounded-md bg-secondary/50 border resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                            placeholder="[Event &quot;...&quot;]&#10;[Site &quot;...&quot;]&#10;1. e4 e5 2. Nf3 ..."
                            value={pgn}
                            onChange={(e) => setPgn(e.target.value)}
                        />
                    </div>
                </div>
            </div>

            <div className="mt-8 flex flex-col items-center gap-4">
                {error && <div className="text-destructive font-medium">{error}</div>}
                <Button
                    size="lg"
                    className="w-full md:w-auto px-12 h-12 text-lg"
                    disabled={!pgn.trim() || isLoading}
                    onClick={handleAnalyze}
                >
                    {isLoading ? (
                        <>
                            <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                            Analyzing Game...
                        </>
                    ) : (
                        "Start Analysis"
                    )}
                </Button>
            </div>
        </div>
    );
};

export default AnalysisDashboard;
