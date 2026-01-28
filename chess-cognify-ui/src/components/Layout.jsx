import React, { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import { LayoutDashboard, BookOpen, Menu, Plus, Trash2, Edit2, Gamepad2, ChevronDown, ChevronRight, Activity, AlertCircle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import useGameStore from '@/store/gameStore';

const Sidebar = () => {
    const { games, fetchGames, deleteGame, updateGame, isLoading } = useGameStore();
    const navigate = useNavigate();
    const location = useLocation();
    const [isGamesExpanded, setIsGamesExpanded] = useState(true);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [renameDialogOpen, setRenameDialogOpen] = useState(false);
    const [selectedGame, setSelectedGame] = useState(null);
    const [newGameName, setNewGameName] = useState('');

    React.useEffect(() => {
        fetchGames();
    }, [fetchGames]);

    // Periodically refresh games list if any game is analyzing
    React.useEffect(() => {
        let interval;
        const needsPolling = games.some(g => g.status === 'pending' || g.status === 'analyzing');

        if (needsPolling) {
            interval = setInterval(() => {
                fetchGames();
            }, 5000); // Check every 5s for the list
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [games, fetchGames]);

    const handleDeleteClick = (game, e) => {
        e.preventDefault();
        e.stopPropagation();
        setSelectedGame(game);
        setDeleteDialogOpen(true);
    };

    const handleRenameClick = (game, e) => {
        e.preventDefault();
        e.stopPropagation();
        setSelectedGame(game);
        setNewGameName(game.metadata?.title || `Game ${game.game_id.slice(0, 6)}`);
        setRenameDialogOpen(true);
    };

    const confirmDelete = async () => {
        if (selectedGame) {
            try {
                // Check if we're currently viewing the game being deleted
                const isViewingDeletedGame = location.pathname.includes(selectedGame.game_id);

                await deleteGame(selectedGame.game_id);

                // Navigate away if we were viewing the deleted game
                if (isViewingDeletedGame) {
                    navigate('/analysis');
                }

                setDeleteDialogOpen(false);
                setSelectedGame(null);
            } catch (error) {
                console.error('Failed to delete game:', error);
                // Keep dialog open to show error
                alert('Failed to delete game. Please try again.');
            }
        }
    };

    const confirmRename = async () => {
        if (selectedGame && newGameName.trim()) {
            await updateGame(selectedGame.game_id, {
                metadata: {
                    ...selectedGame.metadata,
                    title: newGameName.trim()
                }
            });
            setRenameDialogOpen(false);
            setSelectedGame(null);
            setNewGameName('');
        }
    };

    return (
        <>
            <div className="flex h-screen w-64 flex-col border-r bg-card">
                {/* Logo - Clickable */}
                <NavLink to="/" className="p-6 hover:bg-accent/50 transition-colors">
                    <h1 className="text-xl font-bold flex items-center gap-2">
                        <Gamepad2 className="w-6 h-6 text-primary" />
                        Chess Cognify
                    </h1>
                </NavLink>

                <div className="px-4 mb-4">
                    <NavLink to="/analysis">
                        {({ isActive }) => (
                            <Button
                                className={cn("w-full justify-start", isActive ? "bg-accent" : "ghost")}
                                variant={isActive ? "secondary" : "ghost"}
                            >
                                <Plus className="mr-2 h-4 w-4" /> New Analysis
                            </Button>
                        )}
                    </NavLink>
                </div>

                <div className="flex-1 overflow-y-auto px-4 space-y-2">
                    {/* Game Analysis Section - Collapsible */}
                    <div>
                        <button
                            onClick={() => setIsGamesExpanded(!isGamesExpanded)}
                            className="w-full flex items-center justify-between px-2 py-2 text-sm font-semibold hover:bg-accent rounded-md transition-colors"
                        >
                            <div className="flex items-center gap-2">
                                <LayoutDashboard className="h-4 w-4" />
                                <span>Game Analysis</span>
                            </div>
                            {isGamesExpanded ? (
                                <ChevronDown className="h-4 w-4" />
                            ) : (
                                <ChevronRight className="h-4 w-4" />
                            )}
                        </button>

                        {/* Games List - Indented */}
                        {isGamesExpanded && (
                            <div className="ml-6 mt-1 space-y-1">
                                {isLoading && games.length === 0 ? (
                                    <div className="text-sm text-muted-foreground px-2 py-1">Loading...</div>
                                ) : games.length === 0 ? (
                                    <div className="text-sm text-muted-foreground px-2 py-1">No games yet</div>
                                ) : (
                                    games.map((game) => (
                                        <NavLink
                                            key={game.game_id}
                                            to={`/analysis/${game.game_id}`}
                                            className={({ isActive }) =>
                                                cn(
                                                    "group flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-accent",
                                                    isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground"
                                                )
                                            }
                                        >
                                            <div className="flex items-center gap-2 flex-1 min-w-0 pr-2">
                                                {game.status === 'analyzing' || game.status === 'pending' ? (
                                                    <Activity className="h-3 w-3 text-primary animate-spin shrink-0" />
                                                ) : game.status === 'failed' ? (
                                                    <AlertCircle className="h-3 w-3 text-destructive shrink-0" />
                                                ) : (
                                                    <Clock className="h-3 w-3 text-muted-foreground shrink-0 opacity-50" />
                                                )}
                                                <span className="truncate text-xs">
                                                    {game.metadata?.title || `Game ${game.game_id.slice(0, 6)}`}
                                                </span>
                                            </div>
                                            <div
                                                className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                                                onClick={(e) => {
                                                    // Prevent NavLink navigation when clicking buttons
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                }}
                                            >
                                                <button
                                                    onClick={(e) => handleRenameClick(game, e)}
                                                    className="p-1 hover:bg-background rounded"
                                                    title="Rename"
                                                >
                                                    <Edit2 className="h-3 w-3" />
                                                </button>
                                                <button
                                                    onClick={(e) => handleDeleteClick(game, e)}
                                                    className="p-1 hover:bg-destructive/20 rounded"
                                                    title="Delete"
                                                >
                                                    <Trash2 className="h-3 w-3 text-destructive" />
                                                </button>
                                            </div>
                                        </NavLink>
                                    ))
                                )}
                            </div>
                        )}
                    </div>

                    {/* Books Companion Section */}
                    <div>
                        <NavLink
                            to="/books"
                            className={({ isActive }) => cn(
                                "flex items-center gap-2 px-2 py-2 text-sm font-semibold rounded-md hover:bg-accent transition-colors",
                                isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground"
                            )}
                        >
                            <BookOpen className="h-4 w-4" />
                            Book Companion
                        </NavLink>
                    </div>
                </div>
            </div>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Delete Game Analysis</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete "{selectedGame?.metadata?.title || `Game ${selectedGame?.game_id?.slice(0, 6)}`}"?
                            This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button variant="destructive" onClick={confirmDelete}>
                            Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Rename Dialog */}
            <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Rename Game Analysis</DialogTitle>
                        <DialogDescription>
                            Enter a new name for this game analysis.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="game-name">Game Name</Label>
                            <Input
                                id="game-name"
                                value={newGameName}
                                onChange={(e) => setNewGameName(e.target.value)}
                                placeholder="Enter game name"
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        confirmRename();
                                    }
                                }}
                            />
                        </div>
                    </div>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setRenameDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={confirmRename} disabled={!newGameName.trim()}>
                            Rename
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
};

const Layout = () => {
    const location = useLocation();
    const isHomePage = location.pathname === '/';

    return (
        <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans antialiased">
            {/* Only show sidebar if not on homepage */}
            {!isHomePage && <Sidebar />}
            <main className="flex-1 overflow-auto">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
