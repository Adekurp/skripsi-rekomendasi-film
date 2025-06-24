import React from 'react';
import { Link } from 'react-router-dom';

function MovieCard({ movie, onDislike }) {
    const handleDislikeClick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        onDislike(movie.movie_id);
    };

    return (
        <div className="flex-shrink-0 w-48 mr-6 group relative">
            <Link to={`/film/${movie.movie_id}`}>
                <div className="cursor-pointer">
                    <img 
                        src={movie.poster_path} 
                        alt={movie.original_title} 
                        className="w-full h-64 object-cover rounded-lg shadow-lg transition-transform duration-300 group-hover:scale-105 bg-gray-700" 
                        onError={(e) => { e.target.onerror = null; e.target.src='https://placehold.co/200x300/1A202C/E2E8F0?text=Not+Found'; }}
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-60 transition-all duration-300 rounded-lg"></div>
                    <h3 className="mt-2 text-sm font-semibold text-gray-200 truncate group-hover:text-white">{movie.original_title}</h3>
                </div>
            </Link>
            <button 
                onClick={handleDislikeClick}
                className="absolute top-2 right-2 bg-black bg-opacity-50 text-white rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 hover:bg-red-600 focus:outline-none"
                title="Dislike"
            >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
    );
}

export default MovieCard;
