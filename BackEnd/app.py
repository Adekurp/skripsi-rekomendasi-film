import os
import json
import pickle
import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import requests # Pastikan import ini ada di bagian atas file

# ========================================================================
# SETUP APLIKASI
# ========================================================================

# Muat variabel lingkungan (DB_HOST, DB_USER, dll.) dari file .env
load_dotenv()

app = Flask(__name__)
# Aktifkan CORS agar frontend React (berjalan di port lain) bisa mengakses API ini
CORS(app)

# Konfigurasi koneksi ke database MySQL dari file .env
db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# Fungsi untuk membuat koneksi ke database, digunakan oleh setiap endpoint
def create_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

# ========================================================================
# MEMUAT MODEL (Dijalankan sekali saat server dimulai)
# ========================================================================
# --- KODE DEBUGGING BARU ---


# GANTI URL INI DENGAN URL DARI HUGGING FACE ANDA
MODEL_URLS = {
    "movies_df.pkl": "https://huggingface.co/Adekurp/skripsi-rekomendasi-film-model/resolve/main/movies_df.pkl",
    "similarity.pkl": "https://huggingface.co/Adekurp/skripsi-rekomendasi-film-model/resolve/main/similarity.pkl"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def download_file(url, destination):
    print(f"Mengunduh model dari {url}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"✅ Berhasil mengunduh ke {destination}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengunduh model: {e}")
        return False

try:
    for filename, url in MODEL_URLS.items():
        filepath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(filepath):
            print(f"File {filename} tidak ditemukan. Memulai proses unduh.")
            if not download_file(url, filepath):
                exit(1) # Hentikan aplikasi jika download gagal
        else:
            print(f"File {filename} sudah ada. Melanjutkan.")

    movies_df = pickle.load(open(os.path.join(BASE_DIR, "movies_df.pkl"), 'rb'))
    similarity_matrix = pickle.load(open(os.path.join(BASE_DIR, "similarity.pkl"), 'rb'))
    print("✅ Model machine learning berhasil dimuat.")

except Exception as e:
    print(f"❌ FATAL ERROR: Terjadi kesalahan saat memuat model: {e}")
    exit(1)




# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# MOVIES_PATH = os.path.join(BASE_DIR, 'movies_df.pkl')
# SIMILARITY_PATH = os.path.join(BASE_DIR, 'similarity.pkl')


# try:
#     print(f"Mencoba memuat model dari path: {BASE_DIR}")
#     print(f"Path file movies: {MOVIES_PATH}")
#     print(f"Path file similarity: {SIMILARITY_PATH}")

#     with open(MOVIES_PATH, 'rb') as f:
#         movies_df = pickle.load(f)

#     with open(SIMILARITY_PATH, 'rb') as f:
#         similarity_matrix = pickle.load(f)

#     print("✅ Model machine learning berhasil dimuat.")

# except FileNotFoundError as e:
#     print(f"❌ FATAL ERROR: File model tidak ditemukan.")
#     print(f"Error detail: {e}")
#     # Di lingkungan produksi, sebaiknya aplikasi berhenti jika model gagal dimuat.
#     # exit() akan menghentikan proses, dan Railway akan tahu ada yang salah.
#     exit(1)
# except Exception as e:
#     print(f"❌ FATAL ERROR: Terjadi kesalahan saat memuat model: {e}")
#     exit(1)



# ========================================================================
# ENDPOINT API
# ========================================================================

@app.route('/api/movies', methods=['GET'])
def get_all_movies():
    """Endpoint untuk mendapatkan daftar semua film (id dan judul) untuk dropdown pencarian."""
    conn = create_db_connection()
    if not conn:
        return jsonify({"error": "Koneksi database gagal"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        # Ambil hanya kolom yang dibutuhkan untuk efisiensi
        query = "SELECT movie_id, original_title FROM movies_all_data ORDER BY original_title ASC"
        cursor.execute(query)
        movies = cursor.fetchall()
        return jsonify(movies)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/movies/<int:movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    """Endpoint untuk mendapatkan detail lengkap satu film untuk halaman detail."""
    conn = create_db_connection()
    if not conn:
        return jsonify({"error": "Koneksi database gagal"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM movies_all_data WHERE movie_id = %s"
        cursor.execute(query, (movie_id,))
        movie = cursor.fetchone()
        
        if movie:
            # Kolom 'watch_providers' disimpan sebagai string JSON, jadi perlu di-parse
            if movie.get('watch_providers'):
                try:
                    movie['watch_providers'] = json.loads(movie['watch_providers'])
                except (json.JSONDecodeError, TypeError):
                    movie['watch_providers'] = [] # Jika data JSON tidak valid, kembalikan list kosong
            return jsonify(movie)
        else:
            return jsonify({"error": "Film tidak ditemukan"}), 404
            
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/recommendations/<int:movie_id>', methods=['GET'])
def get_recommendations_for_movie(movie_id):
    """Endpoint utama untuk mendapatkan rekomendasi film."""
    try:
        # 1. Temukan index dari film yang dipilih dari dataframe yang kita muat
        if movie_id not in movies_df['movie_id'].values:
            return jsonify({"error": "Film tidak ditemukan dalam model rekomendasi"}), 404
            
        movie_index = movies_df[movies_df['movie_id'] == movie_id].index[0]

        # 2. Ambil skor similarity dan urutkan
        distances = similarity_matrix[movie_index]
        # Ambil 15 rekomendasi teratas untuk memastikan cukup data setelah filtering
        movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:16]
        
        # 3. Dapatkan ID dari film-film yang direkomendasikan
        recommended_movie_ids = [int(movies_df.iloc[i[0]].movie_id) for i in movies_list]
        
        if not recommended_movie_ids:
            return jsonify({"error": "Tidak ada rekomendasi yang dapat dibuat"}), 404

        # 4. Ambil detail film rekomendasi dari database (terutama untuk provider)
        conn = create_db_connection()
        if not conn:
            return jsonify({"error": "Koneksi database gagal"}), 500
        
        cursor = conn.cursor(dictionary=True)
        # Gunakan 'IN' untuk query yang efisien
        format_strings = ','.join(['%s'] * len(recommended_movie_ids))
        query = f"SELECT movie_id, original_title, poster_path, watch_providers FROM movies_all_data WHERE movie_id IN ({format_strings})"
        cursor.execute(query, tuple(recommended_movie_ids))
        recommended_details = cursor.fetchall()
        
        # 5. Proses untuk menemukan platform dominan
        platform_counts = {}
        for movie in recommended_details:
            try:
                providers = json.loads(movie.get('watch_providers', '[]'))
                for provider in providers:
                    platform_name = provider.get('name')
                    if platform_name:
                        platform_counts[platform_name] = platform_counts.get(platform_name, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue
        
        dominant_platform = max(platform_counts, key=platform_counts.get) if platform_counts else None
        
        # 6. Bagi film menjadi dua kategori
        dominant_movies = []
        other_movies = []
        
        if dominant_platform:
            for movie in recommended_details:
                try:
                    providers = json.loads(movie.get('watch_providers', '[]'))
                    provider_names = [p.get('name') for p in providers]
                    if dominant_platform in provider_names:
                        dominant_movies.append(movie)
                    else:
                        other_movies.append(movie)
                except (json.JSONDecodeError, TypeError):
                    other_movies.append(movie) # Jika ada error, anggap sebagai platform lain
        else:
            # Jika tidak ada platform dominan, semua masuk ke 'lainnya'
            other_movies = recommended_details
            dominant_platform = "Tidak Terdeteksi"
            
        # 7. Format respons sesuai kontrak API
        response_data = {
            "dominant_platform": {
                "name": dominant_platform,
                "movies": dominant_movies
            },
            "other_platforms": {
                "movies": other_movies
            }
        }
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Error dalam logika rekomendasi: {e}")
        return jsonify({"error": "Terjadi kesalahan internal saat membuat rekomendasi"}), 500
    finally:
        # Pastikan koneksi ditutup jika dibuka
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


# ========================================================================
# MENJALANKAN SERVER
# ========================================================================
if __name__ == '__main__':
    # port=5000 adalah standar untuk pengembangan Flask
    app.run(debug=True, port=5000)
