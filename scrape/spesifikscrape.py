import requests
import mysql.connector
import json
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Read credentials from environment variables
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Target watch providers as specified
TARGET_PROVIDERS = {
    8: {"name": "Netflix", "subscribe_url": "https://www.netflix.com/id/"},
    9: {
        "name": "Amazon Prime Video",
        "subscribe_url": "https://www.primevideo.com/",
    },
    10: {
        "name": "Amazon Video (Rent/Buy)",
        "subscribe_url": "https://www.amazon.com/video/",
    },
    337: {"name": "Disney Plus", "subscribe_url": "https://www.hotstar.com/id"},
    384: {"name": "HBO Max", "subscribe_url": "https://www.max.com/us/"},
    1899: {"name": "Max", "subscribe_url": "https://www.max.com/us/"},
    350: {"name": "Apple TV+", "subscribe_url": "https://tv.apple.com/id"},
    2: {"name": "Apple TV", "subscribe_url": "https://tv.apple.com/us/"},
}

# --- TMDb API Endpoints ---
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def fetch_from_tmdb(endpoint, params=None):
    """
    Helper function to make requests to the TMDb API.
    """
    if params is None:
        params = {}
    params["api_key"] = TMDB_API_KEY
    url = f"{TMDB_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from TMDb API ({url}): {e}")
        return None


def scrape_movie_data(movie_id):
    """
    Scrapes detailed movie data from TMDb API for a given movie ID.
    """
    print(f"Scraping data for movie ID: {movie_id}...")

    # Fetch main movie details, credits, keywords, and watch providers
    # The 'append_to_response' parameter allows fetching multiple types of data in one go
    movie_data = fetch_from_tmdb(
        f"movie/{movie_id}",
        params={
            "append_to_response": "credits,keywords,watch/providers",
            "language": "en-US",  # Ensure consistent language for providers
        },
    )

    if not movie_data:
        print(f"Could not retrieve data for movie ID {movie_id}.")
        return None

    # --- Extract Movie Details ---
    movie_id = movie_data.get("id")
    original_title = movie_data.get("original_title")
    poster_path = movie_data.get("poster_path")
    if poster_path:
        poster_path = (
            f"https://image.tmdb.org/t/p/original{poster_path}"  # Full URL for poster
        )
    overview = movie_data.get("overview")
    release_date = movie_data.get("release_date")
    # Validate and format release_date for MySQL DATE type if not None
    if release_date:
        try:
            # Ensure date is in YYYY-MM-DD format
            datetime.strptime(release_date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print(
                f"WARNING: Invalid date format for movie ID {movie_id}. Release date: {release_date}"
            )
            release_date = None  # Set to None if invalid, to avoid DB insertion errors

    vote_average = movie_data.get("vote_average")

    # --- Extract Genres ---
    genres_data = movie_data.get("genres", [])
    genres = ", ".join([g.get("name") for g in genres_data if g.get("name")])

    # --- Extract Directors and Main Actors ---
    credits_data = movie_data.get("credits", {})
    crew = credits_data.get("crew", [])
    cast = credits_data.get("cast", [])

    directors = ", ".join([c.get("name") for c in crew if c.get("job") == "Director"])
    main_actors = ", ".join(
        [c.get("name") for c in cast[:5] if c.get("name")]  # Top 5 actors
    )

    # --- Extract Watch Providers ---
    US_providers_raw = (
        movie_data.get("watch/providers", {})
        .get("results", {})
        .get("US", {})  # Check for 'US'
    )

    # --- DEBUGGING PRINT STATEMENT (kept for future reference) ---
    print("\n--- Raw US Watch Providers from TMDb API (for debugging) ---")
    print(json.dumps(US_providers_raw, indent=2))
    print("-----------------------------------------------------------\n")
    # --- END DEBUGGING PRINT STATEMENT ---

    # Temporary list to collect all found providers before making them unique
    found_providers_temp = []

    # Aggregate providers from flatrate, rent, and buy
    for provider_type in ["flatrate", "rent", "buy"]:
        for provider in US_providers_raw.get(provider_type, []):
            if provider["provider_id"] in TARGET_PROVIDERS:
                provider_info = TARGET_PROVIDERS[provider["provider_id"]]
                # Append provider details without the specific 'type'
                found_providers_temp.append(
                    {
                        "id": provider["provider_id"],
                        "name": provider_info["name"],
                        "logo": f"https://image.tmdb.org/t/p/original{provider['logo_path']}",
                        "subscribe_url": provider_info["subscribe_url"],
                    }
                )

    # --- MODIFIED LOGIC: Remove duplicates based ONLY on provider ID ---
    watch_providers = []  # This will be the final unique list
    seen_ids = set()  # Use only provider ID for uniqueness

    for provider in found_providers_temp:
        if provider["id"] not in seen_ids:
            watch_providers.append(provider)
            seen_ids.add(provider["id"])
    # --- END MODIFIED LOGIC ---

    watch_providers_json = json.dumps(watch_providers)

    # --- Extract Keywords ---
    keywords_data = movie_data.get("keywords", {})
    keywords_list = keywords_data.get("keywords", [])  # For movies, it's 'keywords'
    keywords = ", ".join([k.get("name") for k in keywords_list if k.get("name")])

    scraped_data = {
        "movie_id": movie_id,
        "original_title": original_title,
        "poster_path": poster_path,
        "overview": overview,
        "release_date": release_date,
        "vote_average": vote_average,
        "genres": genres,
        "directors": directors,
        "main_actors": main_actors,
        "watch_providers": watch_providers_json,
        "keywords": keywords,
    }
    print(f"Successfully scraped data for '{original_title}' (ID: {movie_id}).")
    return scraped_data


def store_movie_data(movie_data):
    """
    Stores the scraped movie data into the MySQL database.
    """
    if not movie_data:
        print("DEBUG: movie_data is None. Exiting store_movie_data.")
        return

    conn = None
    try:
        print("DEBUG: Attempting to connect to MySQL...")
        conn = mysql.connector.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        print("DEBUG: Successfully connected to MySQL.")
        cur = conn.cursor()

        # SQL query to insert data. ON DUPLICATE KEY UPDATE is MySQL specific.
        insert_query = """
        INSERT INTO movies_all_data (
            movie_id, original_title, poster_path, overview, release_date,
            vote_average, genres, directors, main_actors, watch_providers, keywords
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            original_title = %s,
            poster_path = %s,
            overview = %s,
            release_date = %s,
            vote_average = %s,
            genres = %s,
            directors = %s,
            main_actors = %s,
            watch_providers = %s,
            keywords = %s,
            scraped_at = CURRENT_TIMESTAMP;
        """

        # Prepare parameters for the INSERT and UPDATE parts
        params = (
            movie_data["movie_id"],
            movie_data["original_title"],
            movie_data["poster_path"],
            movie_data["overview"],
            movie_data["release_date"],
            movie_data["vote_average"],
            movie_data["genres"],
            movie_data["directors"],
            movie_data["main_actors"],
            movie_data["watch_providers"],
            movie_data["keywords"],
            # Parameters for the ON DUPLICATE KEY UPDATE clause
            movie_data["original_title"],
            movie_data["poster_path"],
            movie_data["overview"],
            movie_data["release_date"],
            movie_data["vote_average"],
            movie_data["genres"],
            movie_data["directors"],
            movie_data["main_actors"],
            movie_data["watch_providers"],
            movie_data["keywords"],
        )

        print(
            f"DEBUG: Preparing to execute query. Movie ID: {movie_data['movie_id']}, Title: {movie_data['original_title']}"
        )
        print(
            f"DEBUG: Release Date to be inserted: {movie_data['release_date']} (Type: {type(movie_data['release_date'])})"
        )
        print(
            f"DEBUG: Watch Providers JSON to be inserted (truncated): {movie_data['watch_providers'][:100]}... (Type: {type(movie_data['watch_providers'])})"
        )
        print(f"DEBUG: Total parameters for SQL query: {len(params)}")

        cur.execute(insert_query, params)

        # Check affected rows to see if insert or update occurred
        rows_affected = cur.rowcount
        print(f"DEBUG: SQL query executed. Rows affected: {rows_affected}")

        conn.commit()
        print(
            f"Successfully stored/updated movie ID {movie_data['movie_id']} ('{movie_data['original_title']}') in the database."
        )

    except mysql.connector.Error as error:
        print(f"ERROR: MySQL connection or insertion error: {error}")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
    finally:
        if conn and conn.is_connected():
            cur.close()
            conn.close()
            print("DEBUG: MySQL connection closed.")


# --- Main execution block ---
if __name__ == "__main__":
    required_vars = ["TMDB_API_KEY", "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    for var in required_vars:
        if os.getenv(var) is None:
            print(
                f"ERROR: Environment variable '{var}' is not set. Please ensure it's in your .env file or set in your environment."
            )
            exit()

    movie_id_to_scrape = input(
        "Enter the movie ID you want to scrape (e.g., 27205 for Inception, 634649 for Spider-Man: No Way Home): "
    )

    try:
        movie_id_to_scrape = int(movie_id_to_scrape)
    except ValueError:
        print("Invalid movie ID. Please enter a number.")
        exit()

    scraped_movie = scrape_movie_data(movie_id_to_scrape)
    if scraped_movie:
        store_movie_data(scraped_movie)
    else:
        print(f"Failed to scrape data for movie ID {movie_id_to_scrape}.")
