import requests
import mysql.connector
import json
from mysql.connector import Error
import time
from datetime import datetime

# Configuration
TMDB_API_KEY = "107843b489e2299f9393cf6ac9cf7b55"
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "movie_database",
}

# Only Disney+ Hotstar provider
TARGET_PROVIDERS = {
    337: {"name": "Disney Plus Hotstar", "subscribe_url": "https://www.hotstar.com/id"}
}


def create_tables():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

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
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.commit()
        print("✅ Table Berhasil Dibuat")

    except Error as e:
        print(f"❌ Database error saat pembuatan table: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def insert_movie_data(cursor, conn, movie_data, watch_providers):
    try:
        cursor.execute(
            """
        INSERT INTO movies_all_data (
            movie_id, original_title, poster_path, overview, release_date,
            vote_average, genres, directors, main_actors, watch_providers
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            watch_providers = VALUES(watch_providers)
        """,
            (
                movie_data["id"],
                movie_data.get("original_title"),
                movie_data.get("poster_path"),
                movie_data.get("overview"),
                movie_data.get("release_date"),
                movie_data.get("vote_average"),
                ", ".join([g["name"] for g in movie_data.get("genres", [])]),
                ", ".join(
                    [
                        p["name"]
                        for p in movie_data.get("credits", {}).get("crew", [])
                        if p.get("job") == "Director"
                    ][:2]
                ),
                ", ".join(
                    [p["name"] for p in movie_data.get("credits", {}).get("cast", [])][
                        :3
                    ]
                ),
                json.dumps({"watch_providers": watch_providers}),
            ),
        )
        conn.commit()
        return True
    except Error as e:
        print(f"❌ Gagal untuk insert movie {movie_data.get('original_title')}: {e}")
        conn.rollback()
        return False


def scrape_movies(total_movies=10000):
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        movies_collected = 0
        current_year = datetime.now().year
        start_year = 2000  # Adjust as needed

        for year in range(start_year, current_year + 1):
            print(f"🚀 Processing year: {year}")
            page = 1

            while True:
                try:
                    # Fetch movies for specific year with filters - only Disney+ Hotstar
                    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&page={page}&year={year}"
                    url += "&sort_by=popularity.desc"  # Get popular first
                    url += "&with_watch_providers=337"  # Only Disney+ Hotstar
                    url += "&watch_region=US"  # Indonesia region

                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    if not data.get("results") or page > 500:  # Safety limit
                        break

                    for movie in data["results"]:
                        if movies_collected >= total_movies:
                            break

                        try:
                            # Fetch detailed data
                            movie_id = movie["id"]
                            details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,watch/providers"
                            movie_data = requests.get(details_url, timeout=10).json()

                            # Process providers (Indonesia-specific)
                            id_providers = (
                                movie_data.get("watch/providers", {})
                                .get("results", {})
                                .get("US", {})
                            )
                            watch_providers = []

                            # Check all provider types (flatrate, rent, buy) for Disney+ Hotstar
                            for provider_type in ["flatrate", "rent", "buy"]:
                                for provider in id_providers.get(provider_type, []):
                                    if provider["provider_id"] in TARGET_PROVIDERS:
                                        provider_info = TARGET_PROVIDERS[
                                            provider["provider_id"]
                                        ]
                                        watch_providers.append(
                                            {
                                                "id": provider["provider_id"],
                                                "name": provider_info["name"],
                                                "logo": f"https://image.tmdb.org/t/p/original{provider['logo_path']}",
                                                "subscribe_url": provider_info[
                                                    "subscribe_url"
                                                ],
                                            }
                                        )

                            # Only insert if available on Disney+ Hotstar
                            if watch_providers:
                                # Insert data
                                if insert_movie_data(
                                    cursor, conn, movie_data, watch_providers
                                ):
                                    movies_collected += 1
                                    print(
                                        f"✅ [{movies_collected}/{total_movies}] {movie_data.get('original_title')} ({year})"
                                    )

                        except Exception as e:
                            print(
                                f"⚠️ Error processing movie {movie.get('id')}: {str(e)[:100]}"
                            )

                        time.sleep(0.35)  # Rate limiting

                    page += 1

                except requests.exceptions.RequestException as e:
                    print(f"⚠️ API error: {str(e)[:100]}")
                    time.sleep(5)

            if movies_collected >= total_movies:
                break

    except Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    # create_tables()
    scrape_movies(total_movies=10000)
