import React from 'react';
import { Link } from 'react-router-dom';
import MovieSearch from './MovieSearch.jsx';

function Navbar() {
    return (
        <header className="bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50 shadow-lg">
            <nav className="container mx-auto px-4 py-3 flex justify-between items-center">
                <Link to="/" className="text-2xl font-bold text-white cursor-pointer">
                    Cari<span className="text-blue-500">Flix</span>
                </Link>
                <MovieSearch />
            </nav>
        </header>
    );
}

export default Navbar;
