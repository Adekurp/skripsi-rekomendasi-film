import React, { useRef } from 'react';
import MovieCard from './MovieCard.jsx';

function MovieSlider({ title, subtitle, movies, setMovies }) {
    const sliderRef = useRef(null);

    const handleDislike = (movieId) => {
        const movieIndex = movies.findIndex(m => m.movie_id === movieId);
        if (movieIndex > -1) {
            const newMovies = [...movies];
            const [dislikedMovie] = newMovies.splice(movieIndex, 1);
            newMovies.push(dislikedMovie);
            setMovies(newMovies);
        }
    };
    
    const scroll = (direction) => {
        if (sliderRef.current) {
            const scrollAmount = sliderRef.current.clientWidth * 0.8;
            sliderRef.current.scrollBy({
                left: direction === 'left' ? -scrollAmount : scrollAmount,
                behavior: 'smooth'
            });
        }
    };
    
    if (!movies || movies.length === 0) return null;

    return (
        <div className="mb-12">
            <div className="flex justify-between items-center mb-4">
                <div>
                     <h2 className="text-2xl font-bold text-white">{title}</h2>
                     {subtitle && <p className="text-gray-400 text-sm">{subtitle}</p>}
                </div>
                <div className="flex space-x-2">
                     <button onClick={() => scroll('left')} className="bg-gray-800/80 hover:bg-gray-700/80 p-2 rounded-full text-white transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                        </svg>
                     </button>
                      <button onClick={() => scroll('right')} className="bg-gray-800/80 hover:bg-gray-700/80 p-2 rounded-full text-white transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                        </svg>
                     </button>
                </div>
            </div>
            <div ref={sliderRef} className="slider-container flex overflow-x-auto pb-4 -mx-4 px-4">
                {movies.map(movie => (
                    <MovieCard 
                        key={movie.movie_id} 
                        movie={movie} 
                        onDislike={handleDislike}
                    />
                ))}
            </div>
        </div>
    );
}

export default MovieSlider;
