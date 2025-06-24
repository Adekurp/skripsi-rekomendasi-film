import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchMovieDetails } from '../api/apiService';

function DetailPage() {
    const { movie_id } = useParams();
    const navigate = useNavigate();
    const [movie, setMovie] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        window.scrollTo(0, 0);
        setIsLoading(true);
        setError(null);
        fetchMovieDetails(movie_id)
            .then(data => setMovie(data))
            .catch(err => setError(err.message || "Gagal mengambil detail film."))
            .finally(() => setIsLoading(false));
    }, [movie_id]);

    if (isLoading) return <div className="text-center py-20 text-xl font-semibold">Memuat Detail Film...</div>;
    if (error) return (
        <div className="text-center py-20">
            <h1 className="text-2xl font-bold text-red-400">{error}</h1>
            <button onClick={() => navigate('/')} className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg">
                Kembali ke Beranda
            </button>
        </div>
    );
    if (!movie) return null;

    return (
        <div className="container mx-auto px-4 py-8 animate-fade-in">
            <button onClick={() => navigate(-1)} className="mb-8 bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded-lg inline-flex items-center transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5 mr-2">
                   <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
                Kembali
            </button>
            <div className="flex flex-col md:flex-row gap-8">
                <img 
                   src={movie.poster_path} 
                   alt={movie.original_title}
                   className="w-full md:w-1/3 h-auto object-cover rounded-lg shadow-2xl bg-gray-700"
                />
                <div className="md:w-2/3">
                    <h1 className="text-5xl font-black text-white mb-4">{movie.original_title}</h1>
                    <div className="flex items-center flex-wrap gap-x-4 gap-y-2 mb-6">
                       <span className="font-bold text-xl text-yellow-400">Rating: {movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'}/10</span>
                       <span className="text-gray-400">|</span>
                       <span className="font-semibold text-gray-300">Rilis: {movie.release_date || 'Tidak diketahui'}</span>
                       <span className="text-gray-400">|</span>
                       <span className="font-semibold text-gray-300">Bahasa: {movie.original_language ? movie.original_language.toUpperCase() : 'N/A'}</span>
                    </div>
                    <p className="text-lg text-gray-300 mb-6">{movie.overview}</p>
                    <div className="mt-6">
                        <h3 className="text-xl font-bold mb-3">Tersedia di:</h3>
                        <div className="flex flex-wrap items-center gap-4">
                            {movie.watch_providers && movie.watch_providers.length > 0 ? movie.watch_providers.map(p => (
                                <a key={p.id} href={p.subscribe_url} target="_blank" rel="noopener noreferrer" title={p.name}>
                                    <img src={p.logo} alt={p.name} className="h-12 w-12 object-contain bg-white/10 rounded-lg p-1 hover:scale-110 transition-transform"/>
                                </a>
                            )) : <p className="text-gray-400">Tidak tersedia di layanan langganan yang kami lacak.</p>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default DetailPage;
