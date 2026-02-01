
import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Import, Upload } from 'lucide-react';

const PGNImportDialog = ({ onImport }) => {
    const [pgnText, setPgnText] = useState('');
    const [isOpen, setIsOpen] = useState(false);

    const handleImport = () => {
        onImport(pgnText);
        setIsOpen(false);
        setPgnText('');
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            setPgnText(event.target.result);
        };
        reader.readAsText(file);
    };

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" className="gap-2">
                    <Import className="w-4 h-4" />
                    Load PGN
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Import Game (PGN)</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                        <Textarea
                            placeholder="Paste PGN here..."
                            value={pgnText}
                            onChange={(e) => setPgnText(e.target.value)}
                            className="h-[200px] font-mono text-sm"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Or upload file:</span>
                        <input
                            type="file"
                            accept=".pgn"
                            onChange={handleFileUpload}
                            className="text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                        />
                    </div>
                </div>
                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
                    <Button onClick={handleImport} disabled={!pgnText.trim()}>Import</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default PGNImportDialog;
