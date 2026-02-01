import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import EngineAnalysisPanel from './EngineAnalysisPanel';
import MoveList from '@/components/MoveList'; // Reuse existing MoveList

const SelfAnalysisSidebar = ({
    activeTab,
    setActiveTab,
    // Analysis Props
    engineLines,
    engineDepth,
    isAnalysisLoading,
    isAnalysisActive,
    onToggleAnalysis,
    // Move List Props
    moves,
    currentPly,
    onMoveSelect,
    multipv = 3,
    onMultipvChange
}) => {
    return (
        <div className="flex flex-col h-full bg-background border-l">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col h-full">
                <div className="p-2 border-b">
                    <TabsList className="grid w-full grid-cols-1">
                        <TabsTrigger value="analysis">Analysis</TabsTrigger>
                    </TabsList>
                </div>

                <div className="flex-1 overflow-hidden relative">
                    <TabsContent value="analysis" className="h-full m-0 flex flex-col">
                        {/* Top: Engine Analysis */}
                        <div className="h-1/3 min-h-[200px] border-b p-2">
                            <EngineAnalysisPanel
                                topLines={engineLines}
                                depth={engineDepth}
                                isLoading={isAnalysisLoading}
                                isAnalysisActive={isAnalysisActive}
                                onToggleAnalysis={onToggleAnalysis}
                                multipv={multipv}
                                onMultipvChange={onMultipvChange}
                            />
                        </div>

                        {/* Bottom: Move List */}
                        <div className="flex-1 overflow-auto bg-muted/10 p-2">
                            <div className="text-xs font-semibold uppercase text-muted-foreground mb-2 px-2">Moves</div>
                            <MoveList
                                moves={moves}
                                currentPly={currentPly}
                                onMoveSelect={onMoveSelect}
                            />
                        </div>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
};

export default SelfAnalysisSidebar;
