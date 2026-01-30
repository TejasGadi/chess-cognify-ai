import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Loader2, ArrowLeft, BookOpen, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import useBookStore from '@/store/bookStore';

const BooksUpload = () => {
    const [file, setFile] = useState(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const { uploadBook, isLoading } = useBookStore();
    const navigate = useNavigate();
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    const handleUpload = async () => {
        if (!file) return;
        setError(null);
        try {
            const data = await uploadBook(file);
            // Navigate back to the list where they can see the processing status
            navigate('/books');
        } catch (err) {
            console.error("Upload failed:", err);
            setError(err.response?.data?.detail || "Upload failed. Please try again with a valid PDF.");
        }
    };

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile && selectedFile.type === 'application/pdf') {
            setFile(selectedFile);
            setError(null);
        } else if (selectedFile) {
            setError("Please select a valid PDF file.");
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragOver(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type === 'application/pdf') {
            setFile(droppedFile);
            setError(null);
        } else if (droppedFile) {
            setError("Please drop a valid PDF file.");
        }
    };

    return (
        <div className="container mx-auto max-w-2xl p-6 space-y-6">
            <Button variant="ghost" onClick={() => navigate('/books')} className="gap-2 -ml-4">
                <ArrowLeft className="h-4 w-4" /> Back to Library
            </Button>

            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Add to Library</h1>
                <p className="text-muted-foreground">Upload a chess PDF to expand your AI's knowledge base.</p>
            </div>

            <Card className="border-2 border-dashed bg-card/50">
                <CardHeader>
                    <CardTitle className="text-xl flex items-center gap-2">
                        <Upload className="h-5 w-5 text-primary" />
                        Upload PDF
                    </CardTitle>
                    <CardDescription>
                        Maximize layout recognition by using high-quality digital PDFs.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div
                        className={`flex flex-col items-center justify-center py-12 px-6 rounded-xl transition-all duration-200 cursor-pointer
                            ${isDragOver ? 'bg-primary/10 border-primary shadow-inner' : 'bg-muted/50 hover:bg-muted border-transparent'}
                        `}
                        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                        onDragLeave={() => setIsDragOver(false)}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        {file ? (
                            <div className="flex flex-col items-center text-center animate-in zoom-in duration-300">
                                <div className="h-16 w-16 bg-primary/20 rounded-2xl flex items-center justify-center mb-4">
                                    <FileText className="h-8 w-8 text-primary" />
                                </div>
                                <h4 className="font-semibold text-lg line-clamp-1">{file.name}</h4>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {(file.size / (1024 * 1024)).toFixed(2)} MB • PDF Document
                                </p>
                                <Button
                                    variant="link"
                                    size="sm"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setFile(null);
                                    }}
                                    className="text-destructive mt-2"
                                >
                                    Change File
                                </Button>
                            </div>
                        ) : (
                            <>
                                <div className="h-16 w-16 bg-muted rounded-2xl flex items-center justify-center mb-6 text-muted-foreground">
                                    <BookOpen className="h-8 w-8" />
                                </div>
                                <h3 className="text-lg font-semibold mb-2 text-foreground">Click or Drag to Upload</h3>
                                <p className="text-sm text-muted-foreground text-center max-w-xs">
                                    Your file will be processed using high-precision layout analysis (Docling) for the best chat experience.
                                </p>
                            </>
                        )}
                        <input
                            type="file"
                            ref={fileInputRef}
                            className="hidden"
                            accept=".pdf"
                            onChange={handleFileChange}
                        />
                    </div>

                    {error && (
                        <div className="mt-6 p-4 rounded-lg bg-destructive/10 border border-destructive/20 flex items-start gap-3 text-sm text-destructive animate-in slide-in-from-top-2">
                            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                            <p className="font-medium">{error}</p>
                        </div>
                    )}

                    <Button
                        className="w-full h-12 mt-8 text-lg font-semibold shadow-lg shadow-primary/20 transition-all active:scale-[0.98]"
                        disabled={!file || isLoading}
                        onClick={(e) => {
                            e.stopPropagation();
                            handleUpload();
                        }}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                                Uploading & Processing...
                            </>
                        ) : (
                            "Start Import"
                        )}
                    </Button>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
                <div className="p-4 rounded-xl border bg-card/50 space-y-2">
                    <h5 className="font-semibold flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-primary" />
                        High Precision
                    </h5>
                    <p className="text-xs text-muted-foreground">
                        Our engine analyzes tables, diagrams, and formatting to understand the book's context perfectly.
                    </p>
                </div>
                <div className="p-4 rounded-xl border bg-card/50 space-y-2">
                    <h5 className="font-semibold flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-primary" />
                        Instant Query
                    </h5>
                    <p className="text-xs text-muted-foreground">
                        Once uploaded, you can ask about any variation or concept mentioned in the book.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default BooksUpload;
