import requests
import mysql.connector
import json
from mysql.connector import Error
import time
from datetime import datetime

# Configuration
TMDB_API_KEY = (
    "0c258c3dc04cce7817fe3bc9c7b1eef9"  # Replace with your actual TMDB API key
)
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Replace with your MySQL password if you have one
    "database": "film_database",
}

# Define target watch providers and their subscription URLs
TARGET_PROVIDERS = {
    8: {"name": "Netflix", "subscribe_url": "https://www.netflix.com/id/"},
    9: {
        "name": "Amazon Prime Video",
        "subscribe_url": "https://www.primevideo.com/",
    },
    337: {"name": "Disney Plus", "subscribe_url": "https://www.hotstar.com/id"},
    384: {"name": "HBO Max", "subscribe_url": "https://www.max.com/id"},
    350: {"name": "Apple TV+", "subscribe_url": "https://tv.apple.com/id"},
}


def create_tables():
    """
    Connects to the MySQL database and creates the 'movies_all_data' table
    """
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # SQL to create the table
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
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.commit()
        print("✅ Table Berhasil Dibuat")

    except Error as e:
        print(f"❌ Database error saat pembuatan table: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def insert_movie_data(cursor, conn, movie_data, watch_providers, movie_keywords):
    """
    Inserts or updates movie data into the 'movies_all_data' table.
    Now includes the 'keywords' data.
    """
    try:
        cursor.execute(
            """
        INSERT INTO movies_all_data (
            movie_id, original_title, poster_path, overview, release_date,
            vote_average, genres, directors, main_actors, watch_providers, keywords
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            keywords = VALUES(keywords), -- Update keywords on duplicate
            scraped_at = VALUES(scraped_at)
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
                movie_keywords,  # Pass the keywords here
            ),
        )
        conn.commit()
        return True
    except Error as e:
        print(f"❌ Gagal untuk insert movie {movie_data.get('original_title')}: {e}")
        conn.rollback()
        return False


def scrape_movies(total_movies=10000):
    """
    Scrapes movie data from TMDB, including details, credits, watch providers,
    and now keywords, then inserts/updates them into the database.
    """
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        movies_collected = 0
        current_year = datetime.now().year
        start_year = 2013  # Adjust as needed

        for year in range(start_year, current_year + 1):
            print(f"🚀 Processing year: {year}")
            page = 1

            while True:
                if movies_collected >= total_movies:
                    break  # Break outer loop if target reached

                try:
                    # Fetch movies for specific year with filters
                    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&page={page}&year={year}"
                    url += "&sort_by=popularity.desc"  # Get popular first
                    url += "&vote_count.gte=100"  # Minimum 100 votes
                    url += (
                        "&with_watch_providers=8|9|337|350|384"  # Only target providers
                    )
                    url += "&region=US"  # Added region for watch providers consistency as per TMDB API

                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    if not data.get("results") or page > data.get(
                        "total_pages", 500
                    ):  # Use total_pages from API
                        break

                    for movie in data["results"]:
                        if movies_collected >= total_movies:
                            break

                        try:
                            movie_id = movie["id"]
                            # Fetch detailed movie data including credits and watch/providers
                            details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,watch/providers,keywords"
                            movie_data = requests.get(details_url, timeout=10).json()

                            # Extract keywords
                            keywords_list = [
                                k["name"]
                                for k in movie_data.get("keywords", {}).get(
                                    "keywords", []
                                )
                            ]
                            movie_keywords = ", ".join(keywords_list)

                            # Process watch providers
                            # Changed 'US' to 'ID' for Indonesia, or keep 'US' if that's the desired region
                            US_providers = (
                                movie_data.get("watch/providers", {})
                                .get("results", {})
                                .get("US", {})  # Check for 'US'
                            )
                            watch_providers = []

                            # Aggregate providers from flatrate, rent, and buy
                            for provider_type in ["flatrate", "rent", "buy"]:
                                for provider in US_providers.get(provider_type, []):
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

                            if not watch_providers:
                                continue  # Skip if no target watch providers are found

                            # Insert data, now passing movie_keywords
                            if insert_movie_data(
                                cursor,
                                conn,
                                movie_data,
                                watch_providers,
                                movie_keywords,
                            ):
                                movies_collected += 1
                                print(
                                    f"✅ [{movies_collected}/{total_movies}] {movie_data.get('original_title')} ({year})"
                                )

                        except requests.exceptions.RequestException as e:
                            print(
                                f"⚠️ API error for movie {movie.get('id')}: {str(e)[:100]}"
                            )
                        except Exception as e:
                            print(
                                f"⚠️ Error processing movie {movie.get('id')}: {str(e)[:100]}"
                            )

                        time.sleep(0.35)  # Rate limiting to avoid hitting API limits

                    page += 1

                except requests.exceptions.RequestException as e:
                    print(
                        f"⚠️ Gagal Fetch Movie Batch for year {year}, page {page}: {str(e)[:100]}"
                    )
                    time.sleep(5)  # Wait before retrying on batch fetch error

            if movies_collected >= total_movies:
                break  # Break outer loop if target reached

    except Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    # create_tables()
    scrape_movies(total_movies=10000)
