// const API_BASE_URL = 'http://127.0.0.1:5000/api'; // link port Flask yang berjalan lokal

const API_BASE_URL = `${import.meta.env.VITE_API_URL}/api`;
async function fetchFromApi(endpoint) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Gagal mengambil data dari ${endpoint}:`, error);
        throw error;
    }
}

export const fetchAllMovies = () => {
    return fetchFromApi('/movies');
};

export const fetchMovieDetails = (movieId) => {
    return fetchFromApi(`/movies/${movieId}`);
};

export const fetchRecommendations = (movieId) => {
    return fetchFromApi(`/recommendations/${movieId}`);
};
