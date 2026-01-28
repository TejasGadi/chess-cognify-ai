import React from 'react';
import { Star, CheckCircle2, HelpCircle, AlertTriangle, AlertCircle } from 'lucide-react';

const ClassificationRow = ({ label, icon: Icon, color, whiteCount, blackCount }) => (
    <div className="grid grid-cols-[1fr_3rem_1fr] items-center py-2 border-b border-muted last:border-0 hover:bg-muted/30 transition-colors">
        <div className={`text-right font-bold pr-4 ${whiteCount > 0 ? 'text-foreground' : 'text-muted-foreground/30'}`}>
            {whiteCount}
        </div>
        <div className="flex flex-col items-center gap-1 group relative">
            <div className={`p-1.5 rounded-full ${color} bg-opacity-20 flex items-center justify-center`}>
                <Icon className={`w-4 h-4 ${color.replace('bg-', 'text-')}`} />
            </div>
            <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-tighter opacity-0 group-hover:opacity-100 absolute -bottom-4 bg-background px-1 rounded shadow-sm z-10 whitespace-nowrap transition-opacity">
                {label}
            </span>
        </div>
        <div className={`text-left font-bold pl-4 ${blackCount > 0 ? 'text-foreground' : 'text-muted-foreground/30'}`}>
            {blackCount}
        </div>
    </div>
);

const GameDetailedStats = ({ summary, metadata }) => {
    if (!summary || !summary.details) return null;

    const { details } = summary;
    const whiteName = metadata?.White || "White";
    const blackName = metadata?.Black || "Black";

    const classifications = [
        { label: 'Best', icon: Star, color: 'bg-green-500', key: 'Best' },
        { label: 'Good', icon: CheckCircle2, color: 'bg-green-600', key: 'Good' },
        { label: 'Inaccuracy', icon: HelpCircle, color: 'bg-yellow-500', key: 'Inaccuracy' },
        { label: 'Mistake', icon: AlertTriangle, color: 'bg-orange-500', key: 'Mistake' },
        { label: 'Blunder', icon: AlertCircle, color: 'bg-red-600', key: 'Blunder' },
    ];

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            {/* Accuracy & Rating Comparison */}
            <div className="bg-card rounded-xl border p-4 shadow-sm">
                <div className="flex justify-between items-center mb-4">
                    <div className="flex-1 text-center">
                        <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">White</p>
                        <p className="font-bold truncate text-sm mb-2">{whiteName}</p>
                        <div className="inline-flex flex-col items-center">
                            <span className="text-2xl font-black">{details.white_accuracy}%</span>
                            <span className="text-[10px] bg-secondary px-2 py-0.5 rounded font-bold">{details.white_rating}</span>
                        </div>
                    </div>

                    <div className="px-4 pb-2">
                        <div className="h-12 w-[1px] bg-muted mx-auto" />
                        <span className="text-[10px] font-bold text-muted-foreground uppercase py-2 block">VS</span>
                        <div className="h-12 w-[1px] bg-muted mx-auto" />
                    </div>

                    <div className="flex-1 text-center">
                        <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Black</p>
                        <p className="font-bold truncate text-sm mb-2">{blackName}</p>
                        <div className="inline-flex flex-col items-center">
                            <span className="text-2xl font-black">{details.black_accuracy}%</span>
                            <span className="text-[10px] bg-secondary px-2 py-0.5 rounded font-bold">{details.black_rating}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Move Breakdown Table */}
            <div className="bg-card rounded-xl border overflow-hidden shadow-sm">
                <div className="bg-muted/50 px-4 py-2 border-b flex justify-between items-center">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Move Breakdown</span>
                </div>
                <div className="p-2">
                    {classifications.map((item) => (
                        <ClassificationRow
                            key={item.label}
                            label={item.label}
                            icon={item.icon}
                            color={item.color}
                            whiteCount={details.move_counts?.white?.[item.key] || 0}
                            blackCount={details.move_counts?.black?.[item.key] || 0}
                        />
                    ))}
                </div>
            </div>

            {/* Phase Accuracy */}
            <div className="bg-card rounded-xl border overflow-hidden shadow-sm">
                <div className="bg-muted/50 px-4 py-2 border-b flex justify-between items-center">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Phase Performance</span>
                </div>
                <div className="p-4 space-y-4">
                    {['opening', 'middlegame', 'endgame'].map((phase) => {
                        const whitePhase = details.phase_stats?.white?.[phase]?.accuracy || 0;
                        const blackPhase = details.phase_stats?.black?.[phase]?.accuracy || 0;
                        const hasData = details.phase_stats?.white?.[phase] || details.phase_stats?.black?.[phase];

                        if (!hasData) return null;

                        return (
                            <div key={phase} className="space-y-1.5">
                                <div className="flex justify-between text-[10px] font-bold uppercase tracking-tighter text-muted-foreground">
                                    <span>White: {whitePhase}%</span>
                                    <span className="text-foreground">{phase}</span>
                                    <span>Black: {blackPhase}%</span>
                                </div>
                                <div className="h-2 rounded-full bg-muted flex overflow-hidden">
                                    <div
                                        className="h-full bg-zinc-400 transition-all duration-1000"
                                        style={{ width: `${whitePhase / 2}%`, borderRight: '1px solid white' }}
                                    />
                                    <div className="h-full bg-muted flex-1" />
                                    <div
                                        className="h-full bg-zinc-800 transition-all duration-1000"
                                        style={{ width: `${blackPhase / 2}%`, borderLeft: '1px solid white' }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default GameDetailedStats;
