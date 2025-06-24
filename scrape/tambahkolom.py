import requests
import mysql.connector  # Or your preferred database connector

# --- Configuration ---
TMDB_API_KEY = "107843b489e2299f9393cf6ac9cf7b55"
DATABASE_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "film_database",
}


def get_movie_language_from_tmdb(movie_id):
    """Fetches the original language of a movie from TMDB API."""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data.get("original_language")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for movie_id {movie_id}: {e}")
        return None


def update_movie_language_in_db():
    """Fetches movie IDs from the database, scrapes language from TMDB, and updates the database."""
    db_connection = None
    try:
        db_connection = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = db_connection.cursor()

        # Get all movie_ids that don't have an original_language yet (or you can process all)
        # For first-time population, you might just select all movie_ids
        cursor.execute(
            "SELECT movie_id FROM movies_all_data WHERE original_language IS NULL"
        )
        movie_ids_to_update = cursor.fetchall()

        print(f"Found {len(movie_ids_to_update)} movies to update language for.")

        for (movie_id,) in movie_ids_to_update:
            language = get_movie_language_from_tmdb(movie_id)
            if language:
                try:
                    update_query = "UPDATE movies_all_data SET original_language = %s WHERE movie_id = %s"
                    cursor.execute(update_query, (language, movie_id))
                    db_connection.commit()
                    print(f"Updated movie_id {movie_id} with language: {language}")
                except mysql.connector.Error as err:
                    print(f"Error updating movie_id {movie_id} in DB: {err}")
                    db_connection.rollback()  # Rollback on error
            else:
                print(f"Could not retrieve language for movie_id {movie_id}. Skipping.")

    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
    finally:
        if db_connection:
            cursor.close()
            db_connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    update_movie_language_in_db()
