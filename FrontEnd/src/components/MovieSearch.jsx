import React, { useState, useEffect } from 'react';
import Select from 'react-select';
import { useNavigate } from 'react-router-dom';
import { fetchAllMovies } from '../api/apiService';

function MovieSearch() {
    const [selected, setSelected] = useState(null);
    const [movieOptions, setMovieOptions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        setIsLoading(true);
        fetchAllMovies()
            .then(data => {
                const options = data.map(m => ({ value: m.movie_id, label: m.original_title }));
                setMovieOptions(options);
            })
            .catch(err => console.error("Gagal memuat daftar film untuk pencarian:", err))
            .finally(() => setIsLoading(false));
    }, []);
    
    const customStyles = {
      control: (base) => ({ ...base, backgroundColor: '#2D3748', borderColor: '#4A5568', borderRadius: '0.5rem', minHeight: '42px', boxShadow: 'none', '&:hover': { borderColor: '#4A5568' } }),
      singleValue: (base) => ({ ...base, color: '#E2E8F0' }),
      placeholder: (base) => ({ ...base, color: '#A0AEC0' }),
      input: (base) => ({ ...base, color: '#E2E8F0' }),
      menu: (base) => ({ ...base, backgroundColor: '#2D3748', zIndex: 9999 }),
      option: (base, state) => ({ ...base, backgroundColor: state.isFocused ? '#4A5568' : '#2D3748', '&:active': { backgroundColor: '#3182CE' } }),
    };
    
    const handleSearchClick = () => {
        if(selected) {
            navigate(`/film/${selected.value}`);
            setSelected(null); // Reset setelah pencarian
        }
    }

    return (
        <div className="flex items-center gap-2 w-full md:w-96">
            <div className="flex-grow">
                <Select
                    value={selected}
                    options={movieOptions}
                    onChange={setSelected}
                    placeholder="Cari film..."
                    styles={customStyles}
                    isClearable
                    isLoading={isLoading}
                />
            </div>
            <button 
                onClick={handleSearchClick}
                className="bg-blue-600 hover:bg-blue-700 text-white p-2.5 rounded-md transition-colors disabled:bg-gray-500"
                title="Cari Film"
                disabled={!selected}
            >
                 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                   <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                 </svg>
            </button>
        </div>
    );
};

export default MovieSearch;
