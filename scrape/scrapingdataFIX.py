import requests
import mysql.connector
import json
from mysql.connector import Error
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env
load_dotenv()

# --- Konfigurasi ---
# Kunci API TMDB - dimuat dari variabel lingkungan
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Konfigurasi Database MySQL - dimuat dari variabel lingkungan
MYSQL_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# Definisikan penyedia tontonan target dan URL langganan mereka berdasarkan provider_id TMDb
TARGET_PROVIDERS = {
    8: {"name": "Netflix", "subscribe_url": "https://www.netflix.com/id/"},
    9: {
        "name": "Amazon Prime Video",
        "subscribe_url": "https://www.primevideo.com/",
    },
    10: {"name": "Amazon Video", "subscribe_url": "https://www.amazon.com/video/"},
    337: {"name": "Disney Plus", "subscribe_url": "https://www.hotstar.com/id"},
    384: {"name": "HBO Max", "subscribe_url": "https://www.max.com/us/"},
    1899: {"name": "Max", "subscribe_url": "https://www.max.com/us/"},
    350: {"name": "Apple TV+", "subscribe_url": "https://tv.apple.com/id"},
    2: {"name": "Apple TV", "subscribe_url": "https://tv.apple.com/us/"},
}

# URL Dasar untuk API TMDb
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def create_tables():
    """
    Menghubungkan ke database MySQL dan membuat tabel 'movies_all_data'
    jika belum ada.
    """
    conn = None
    cursor = None
    try:
        # Buat koneksi ke database MySQL
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # SQL untuk membuat tabel
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS movies_all_data (
            movie_id INT PRIMARY KEY,
            original_title VARCHAR(255),
            poster_path VARCHAR(255),
            overview TEXT,
            release_date DATE,
            vote_average FLOAT,
            genres VARCHAR(255),
            directors VARCHAR(255),
            main_actors VARCHAR(255),
            watch_providers JSON,
            keywords TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            original_language VARCHAR(50) # Kolom baru untuk bahasa asli
        )
        """
        )
        conn.commit() # Commit perubahan ke database
        print("✅ Tabel 'movies_all_data' berhasil dibuat atau sudah ada.")

    except Error as e:
        print(f"❌ Kesalahan database saat pembuatan tabel: {e}")
    finally:
        # Tutup kursor dan koneksi
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def insert_movie_data(cursor, conn, movie_details, processed_watch_providers, movie_keywords, original_language):
    """
    Memasukkan atau memperbarui data film ke dalam tabel 'movies_all_data'.
    Menggunakan ON DUPLICATE KEY UPDATE untuk menangani rekaman yang sudah ada.
    """
    try:
        # Menambahkan 'original_language' ke daftar kolom INSERT dan UPDATE
        insert_query = """
        INSERT INTO movies_all_data (
            movie_id, original_title, poster_path, overview, release_date,
            vote_average, genres, directors, main_actors, watch_providers, keywords,
            original_language
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            original_title = VALUES(original_title),
            poster_path = VALUES(poster_path),
            overview = VALUES(overview),
            release_date = VALUES(release_date),
            vote_average = VALUES(vote_average),
            genres = VALUES(genres),
            directors = VALUES(directors),
            main_actors = VALUES(main_actors),
            watch_providers = VALUES(watch_providers),
            keywords = VALUES(keywords),
            scraped_at = CURRENT_TIMESTAMP,
            original_language = VALUES(original_language)
        """
        
        # Siapkan tuple nilai untuk query SQL
        # Menambahkan 'original_language' ke daftar nilai
        values = (
            movie_details.get("id"),
            movie_details.get("original_title"),
            movie_details.get("poster_path"), # Ini seharusnya sudah menjadi URL lengkap
            movie_details.get("overview"),
            movie_details.get("release_date"), # Seharusnya string YYYY-MM-DD atau None
            movie_details.get("vote_average"),
            ", ".join([g["name"] for g in movie_details.get("genres", []) if g.get("name")]),
            ", ".join(
                [p["name"] for p in movie_details.get("credits", {}).get("crew", []) if p.get("job") == "Director"][:2]
            ), # 2 sutradara teratas
            ", ".join(
                [p["name"] for p in movie_details.get("credits", {}).get("cast", []) if p.get("name")][:3]
            ), # 3 aktor utama teratas
            json.dumps(processed_watch_providers), # Simpan daftar konsolidasi sebagai string JSON
            movie_keywords, # Sudah berupa string yang dipisahkan koma
            original_language, # Nilai untuk kolom bahasa asli
        )

        cursor.execute(insert_query, values)
        conn.commit() # Commit setiap penyisipan/pembaruan
        return True
    except Error as e:
        print(f"❌ Gagal untuk memasukkan/memperbarui film '{movie_details.get('original_title')}' (ID: {movie_details.get('id')}): {e}")
        conn.rollback() # Rollback jika terjadi kesalahan untuk mencegah komit parsial
        return False


def scrape_movies(total_movies=20000):
    """
    Mengikis data film dari TMDB dalam batch, memprosesnya, dan menyisipkan/memperbarui
    mereka ke dalam database. Iterasi melalui tahun dan halaman.
    """
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        movies_collected = 0
        current_year = datetime.now().year
        start_year = 2024  # Mulai mengikis dari tahun ini

        # Konversi kunci TARGET_PROVIDERS ke string yang dipisahkan pipa untuk query API
        provider_ids_str = "|".join(map(str, TARGET_PROVIDERS.keys()))

        for year in range(start_year, current_year + 1):
            print(f"\n🚀 Memproses tahun: {year}")
            page = 1
            max_pages_per_year = 500 # TMDb membatasi hingga 500 halaman per query

            while True:
                if movies_collected >= total_movies:
                    print(f"Target {total_movies} film tercapai. Menghentikan scraping.")
                    break  # Keluar dari loop luar (loop tahun) jika target total tercapai

                try:
                    # Buat URL untuk endpoint penemuan TMDb
                    discover_url = (
                        f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}"
                        f"&page={page}&year={year}"
                        f"&sort_by=popularity.desc"  # Urutkan berdasarkan popularitas menurun
                        f"&vote_count.gte=100"       # Minimal 100 suara
                        f"&with_watch_providers={provider_ids_str}" # Hanya penyedia target
                        f"&watch_region=US"          # Wilayah konsisten untuk penyedia tontonan
                    )

                    response = requests.get(discover_url, timeout=15)
                    response.raise_for_status() # Lemparkan HTTPError untuk respons buruk
                    data = response.json()

                    # Periksa apakah tidak ada hasil atau jika kita telah melewati halaman terakhir untuk tahun ini
                    if not data.get("results") or page > data.get("total_pages", 1) or page > max_pages_per_year:
                        print(f"Selesai untuk tahun {year} atau tidak ada lagi hasil. Total halaman yang diproses: {page-1}")
                        break # Keluar dari loop dalam (loop halaman)

                    for movie_summary in data["results"]:
                        if movies_collected >= total_movies:
                            break # Keluar dari loop dalam jika target total tercapai

                        try:
                            movie_id = movie_summary["id"]
                            
                            # Ambil data detail film termasuk kredit, penyedia tontonan, dan kata kunci
                            details_url = (
                                f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}"
                                f"&append_to_response=credits,watch/providers,keywords"
                                f"&language=en-US" # Pastikan bahasa yang konsisten untuk detail
                            )
                            movie_details = requests.get(details_url, timeout=10).json()

                            if not movie_details:
                                print(f"⚠️ Gagal mendapatkan detail untuk film ID {movie_id}. Melanjutkan...")
                                continue # Lewati ke film berikutnya jika detail tidak ditemukan

                            # Buat jalur poster lengkap
                            if movie_details.get("poster_path"):
                                movie_details["poster_path"] = f"https://image.tmdb.org/t/p/original{movie_details['poster_path']}"
                            
                            # Proses penyedia tontonan: Konsolidasi berdasarkan ID penyedia
                            US_providers_raw = (
                                movie_details.get("watch/providers", {})
                                .get("results", {})
                                .get("US", {})
                            )
                            
                            found_providers_temp = []
                            for provider_type in ["flatrate", "rent", "buy"]:
                                for provider_entry in US_providers_raw.get(provider_type, []):
                                    if provider_entry["provider_id"] in TARGET_PROVIDERS:
                                        provider_info = TARGET_PROVIDERS[provider_entry["provider_id"]]
                                        found_providers_temp.append(
                                            {
                                                "id": provider_entry["provider_id"],
                                                "name": provider_info["name"],
                                                "logo": f"https://image.tmdb.org/t/p/original{provider_entry['logo_path']}",
                                                "subscribe_url": provider_info["subscribe_url"],
                                            }
                                        )
                            
                            # Hapus duplikat HANYA berdasarkan ID penyedia
                            processed_watch_providers = []
                            seen_ids = set() # Gunakan hanya ID penyedia untuk keunikan
                            for p in found_providers_temp:
                                if p["id"] not in seen_ids:
                                    processed_watch_providers.append(p)
                                    seen_ids.add(p["id"])

                            # Ekstrak kata kunci sebagai string yang dipisahkan koma
                            keywords_list = [
                                k["name"]
                                for k in movie_details.get("keywords", {}).get("keywords", [])
                                if k.get("name")
                            ]
                            movie_keywords_str = ", ".join(keywords_list)

                            # Ambil bahasa asli
                            movie_original_language = movie_details.get("original_language")

                            # Tangani None untuk release_date jika kosong dari API atau format tidak valid
                            if not movie_details.get("release_date"):
                                movie_details["release_date"] = None
                            else: # Pastikan format tanggal adalah YYYY-MM-DD untuk tipe DATE MySQL
                                try:
                                    datetime.strptime(movie_details["release_date"], '%Y-%m-%d')
                                except ValueError:
                                    print(f"WARNING: Format tanggal tidak valid untuk film ID {movie_id}. Mengatur release_date ke None.")
                                    movie_details["release_date"] = None

                            # Coba untuk memasukkan atau memperbarui data film
                            if insert_movie_data(
                                cursor,
                                conn,
                                movie_details,
                                processed_watch_providers,
                                movie_keywords_str,
                                movie_original_language, # Teruskan bahasa asli
                            ):
                                movies_collected += 1
                                print(f"✅ [{movies_collected}/{total_movies}] Memproses: {movie_details.get('original_title')} ({year})")

                        except requests.exceptions.RequestException as e:
                            print(f"⚠️ Kesalahan API untuk film ID {movie_summary.get('id')}: {str(e)}")
                        except Exception as e:
                            print(f"⚠️ Kesalahan saat memproses film ID {movie_summary.get('id')}: {str(e)}")
                        
                        time.sleep(0.1) # Penundaan kecil untuk pengambilan film individual

                    page += 1
                    time.sleep(0.5) # Penundaan antar halaman untuk menghormati batas API

                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Gagal Mengambil Batch Film untuk tahun {year}, halaman {page}: {str(e)}")
                    time.sleep(5)  # Tunggu lebih lama sebelum mencoba lagi pada kesalahan pengambilan batch

            if movies_collected >= total_movies:
                break # Keluar dari loop tahun jika target total tercapai

    except Error as e:
        print(f"❌ Kesalahan database utama: {e}")
    finally:
        # Pastikan kursor dan koneksi ditutup dalam fungsi scraping utama
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    # Periksa apakah variabel lingkungan diatur

    create_tables()
    scrape_movies(total_movies=20000)
    print("✅ Proses scraping selesai.")
