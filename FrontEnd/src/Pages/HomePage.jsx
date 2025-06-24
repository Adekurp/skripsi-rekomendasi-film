import React, { useState, useEffect } from 'react';
import Select from 'react-select';
import { fetchAllMovies, fetchRecommendations } from '../api/apiService';
import MovieSlider from '../components/MovieSlider.jsx';

function HomePage() {
    const [selectedMovie, setSelectedMovie] = useState(null);
    const [allMovieOptions, setAllMovieOptions] = useState([]);
    const [recommendations, setRecommendations] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isLoadingMovies, setIsLoadingMovies] = useState(true);
    const [error, setError] = useState(null);
    
    // --- PERUBAHAN BARU ---
    // State untuk mengelola timer cooldown dalam detik
    const [cooldown, setCooldown] = useState(0);

    // useEffect untuk menjalankan countdown timer
    useEffect(() => {
        // Jika tidak ada cooldown, jangan lakukan apa-apa
        if (cooldown <= 0) return;

        // Atur timer untuk mengurangi waktu cooldown setiap 1 detik
        const timerId = setTimeout(() => {
            setCooldown(cooldown - 1);
        }, 1000);

        // Bersihkan timer jika komponen di-unmount atau cooldown berubah
        return () => clearTimeout(timerId);
    }, [cooldown]); // Hook ini akan berjalan setiap kali nilai cooldown berubah

    useEffect(() => {
        setIsLoadingMovies(true);
        fetchAllMovies()
            .then(data => {
                const options = data.map(m => ({ value: m.movie_id, label: m.original_title }));
                setAllMovieOptions(options);
            })
            .catch(err => setError("Gagal memuat daftar film. Coba muat ulang halaman."))
            .finally(() => setIsLoadingMovies(false));
    }, []);
    
    const customStyles = {
      control: (base) => ({ ...base, backgroundColor: '#2D3748', borderColor: '#4A5568', borderRadius: '0.5rem', minHeight: '42px', boxShadow: 'none', '&:hover': { borderColor: '#4A5568' } }),
      singleValue: (base) => ({ ...base, color: '#E2E8F0' }),
      placeholder: (base) => ({ ...base, color: '#A0AEC0' }),
      input: (base) => ({ ...base, color: '#E2E8F0' }),
      menu: (base) => ({ ...base, backgroundColor: '#2D3748', zIndex: 9998 }),
      option: (base, state) => ({ ...base, backgroundColor: state.isFocused ? '#4A5568' : '#2D3748', '&:active': { backgroundColor: '#3182CE' } }),
    };

    const handleCreateRecommendation = async () => {
        // Jangan jalankan jika tidak ada film yang dipilih, sedang loading, atau dalam masa cooldown
        if (!selectedMovie || isLoading || cooldown > 0) return;

        setIsLoading(true);
        setError(null);
        setRecommendations(null);

        try {
            const processedData = await fetchRecommendations(selectedMovie.value);
            setRecommendations(processedData);
        } catch (err) {
            setError(err.message || "Gagal mendapatkan rekomendasi. Silakan coba lagi.");
        } finally {
            setIsLoading(false);
            // Atur cooldown selama 0.5 detik setelah permintaan selesai
            setCooldown(0.5); 
        }
    };
    
    const setDominantMovies = (newMovies) => {
        setRecommendations(prev => ({ ...prev, dominant_platform: { ...prev.dominant_platform, movies: newMovies } }));
    };
    
    const setOtherMovies = (newMovies) => {
         setRecommendations(prev => ({ ...prev, other_platforms: { ...prev.other_platforms, movies: newMovies } }));
    };

    // Logika untuk menentukan teks dan status tombol
    const getButtonState = () => {
        if (isLoading) {
            return { text: 'Mencari...', disabled: true };
        }
        if (cooldown > 0) {
            return { text: `Tunggu ${cooldown} detik...`, disabled: true };
        }
        return { text: 'Buat Rekomendasi', disabled: !selectedMovie };
    };

    const buttonState = getButtonState();

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="text-center max-w-2xl mx-auto">
                <h1 className="text-5xl md:text-6xl font-black text-white leading-tight">Buat Rekomendasi</h1>
                <p className="text-gray-400 mt-4 mb-8">Pilih film favorit Anda, dan biarkan kami menemukan film-film serupa beserta platform streaming yang paling cocok untuk Anda.</p>
                
                <div className="flex flex-col sm:flex-row items-center gap-4 justify-center">
                    <div className="w-full sm:w-80">
                       <Select
                            options={allMovieOptions}
                            onChange={setSelectedMovie}
                            placeholder="Pilih Film Favorit Anda"
                            styles={customStyles}
                            isLoading={isLoadingMovies}
                            isDisabled={isLoading || cooldown > 0} // Nonaktifkan dropdown saat loading/cooldown
                        />
                    </div>
                    <button 
                        onClick={handleCreateRecommendation}
                        disabled={buttonState.disabled}
                        className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white font-bold py-2.5 px-6 rounded-lg transition-all duration-300"
                    >
                        {buttonState.text}
                    </button>
                </div>
            </div>
            
            <div className="mt-16">
                {error && <div className="text-center text-red-400 bg-red-900/20 p-4 rounded-lg">{error}</div>}
                
                {recommendations && (
                     <div className="animate-fade-in">
                         <div className="text-center mb-12 p-6 bg-gray-800/50 rounded-lg max-w-3xl mx-auto">
                            <p className="text-gray-300">Platform streaming film yang cocok untuk Anda adalah</p>
                            <h2 className="text-4xl font-bold text-blue-400 mt-2">{recommendations.dominant_platform.name}</h2>
                         </div>
                         <MovieSlider 
                             title={`Rekomendasi di ${recommendations.dominant_platform.name}`}
                             subtitle={`Berikut rekomendasi film yang serupa di ${recommendations.dominant_platform.name}`}
                             movies={recommendations.dominant_platform.movies}
                             setMovies={setDominantMovies}
                         />
                         <MovieSlider 
                             title="Rekomendasi Film di Platform Lainnya"
                             movies={recommendations.other_platforms.movies}
                             setMovies={setOtherMovies}
                         />
                     </div>
                )}
            </div>
        </div>
    );
}

export default HomePage;
