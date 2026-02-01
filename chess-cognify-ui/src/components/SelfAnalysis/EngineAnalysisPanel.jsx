import React from 'react';
import { Loader2, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

// Helper to format evaluation
const formatEval = (cp, mate) => {
    if (mate !== null && mate !== undefined) {
        return `M${Math.abs(mate)}`;
    }
    const evalVal = (cp / 100).toFixed(2);
    return cp > 0 ? `+${evalVal}` : evalVal;

};

const EngineAnalysisPanel = ({
    isLoading,
    topLines = [],
    depth,
    onToggleAnalysis,
    isAnalysisActive,
    multipv,
    onMultipvChange
}) => {
    return (
        <div className="flex flex-col h-full bg-card rounded-lg border shadow-sm overflow-hidden">
            {/* Header / Controls */}
            <div className="p-3 border-b flex items-center justify-between bg-muted/30">
                <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">Engine</span>
                    {isLoading && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground font-mono">depth={depth}</span>

                    <Popover>
                        <PopoverTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-6 w-6">
                                <Settings className="w-3 h-3" />
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-60">
                            <div className="grid gap-4">
                                <div className="space-y-2">
                                    <h4 className="font-medium leading-none">Engine Settings</h4>
                                    <p className="text-sm text-muted-foreground">
                                        Configure analysis parameters.
                                    </p>
                                </div>
                                <div className="grid gap-2">
                                    <div className="grid grid-cols-3 items-center gap-4">
                                        <Label htmlFor="multipv">Lines</Label>
                                        <Input
                                            id="multipv"
                                            type="number"
                                            min={1}
                                            max={10}
                                            className="col-span-2 h-8"
                                            value={multipv}
                                            onChange={(e) => {
                                                const val = parseInt(e.target.value);
                                                if (!isNaN(val) && val >= 1 && val <= 10) {
                                                    onMultipvChange(val);
                                                }
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </PopoverContent>
                    </Popover>

                    <div className="flex items-center space-x-2">
                        <input
                            type="checkbox"
                            checked={isAnalysisActive}
                            onChange={(e) => onToggleAnalysis(e.target.checked)}
                            className="toggle toggle-xs"
                        />
                    </div>
                </div>
            </div>

            {/* Lines List */}
            <div className="flex-1 overflow-y-auto p-0">
                {topLines.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-muted-foreground text-sm">
                        {isAnalysisActive ? (
                            isLoading ? (
                                <span>Calculating...</span>
                            ) : (
                                <span>No analysis available</span>
                            )
                        ) : (
                            <span>Analysis Paused</span>
                        )}
                    </div>
                ) : (
                    <div className="divide-y">
                        {topLines.map((line, idx) => {
                            const evalCp = line.eval ?? line.eval_cp ?? 0;
                            const isWhiteAdvantage = evalCp > 0 || (line.mate && line.mate > 0);
                            const bgClass = idx === 0 ? 'bg-primary/5' : '';

                            return (
                                <div key={idx} className={`p-2 hover:bg-muted/50 transition-colors flex items-start gap-3 text-sm ${bgClass}`}>
                                    {/* Eval Badge */}
                                    <div className={`
                                        flex-shrink-0 w-12 text-center py-1 rounded font-mono font-bold text-xs
                                        ${isWhiteAdvantage ? 'bg-white text-black border border-gray-200' : 'bg-zinc-800 text-white'}
                                    `}>
                                        {formatEval(evalCp, line.mate)}
                                    </div>

                                    {/* Moves */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex flex-wrap gap-x-1 font-mono text-xs leading-5">
                                            {/* PV SAN is usually a list of strings */}
                                            {line.pv_san && line.pv_san.map((move, mIdx) => (
                                                <span key={mIdx} className={mIdx === 0 ? "font-bold text-foreground" : "text-muted-foreground"}>
                                                    {move}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default EngineAnalysisPanel;
