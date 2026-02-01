import React from 'react';
import { Link } from 'react-router-dom';
import { Gamepad2, Heart } from 'lucide-react';

const Footer = () => {
    return (
        <footer className="bg-card border-t border-border mt-auto">
            <div className="container mx-auto px-6 py-12">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
                    {/* Brand Section */}
                    <div className="col-span-1 md:col-span-2 space-y-4">
                        <Link to="/" className="flex items-center gap-2 group">
                            <Gamepad2 className="w-6 h-6 text-primary" />
                            <span className="text-xl font-bold">Chess Cognify</span>
                        </Link>
                        <p className="text-muted-foreground text-sm max-w-sm">
                            The ultimate AI-powered companion for chess players. Analyze your games, study from books, and master the art of chess with natural language explanations.
                        </p>
                    </div>

                    {/* Product Links */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-bold uppercase tracking-wider text-foreground">Product</h4>
                        <ul className="space-y-2">
                            <li><NavLink to="/analysis" className="text-sm text-muted-foreground hover:text-primary transition-colors">Game Analysis</NavLink></li>
                            <li><NavLink to="/books" className="text-sm text-muted-foreground hover:text-primary transition-colors">Book Companion</NavLink></li>
                            <li><a href="#features" className="text-sm text-muted-foreground hover:text-primary transition-colors">Features</a></li>
                            <li><a href="#how-it-works" className="text-sm text-muted-foreground hover:text-primary transition-colors">How It Works</a></li>
                        </ul>
                    </div>

                </div>

                {/* Bottom Bar */}
                <div className="pt-8 border-t border-border flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
                    <p>© {new Date().getFullYear()} Chess Cognify AI. All rights reserved.</p>
                    <div className="flex items-center gap-1">
                        Made with <Heart className="w-3 h-3 text-red-500 fill-red-500" /> for the chess community.
                    </div>
                </div>
            </div>
        </footer>
    );
};

const NavLink = ({ to, children, className }) => (
    <Link to={to} className={className}>{children}</Link>
);

export default Footer;
