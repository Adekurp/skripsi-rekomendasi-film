import mysql.connector
from mysql.connector import Error
import pandas as pd
import os
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env
load_dotenv()


def koneksi_db():
    """Membuka koneksi ke database MySQL menggunakan env."""
    koneksi = None
    try:
        koneksi = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            passwd=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        if koneksi.is_connected():
            print("Berhasil terhubung ke database MySQL!")
        return koneksi
    except Error as err:
        print(f"Error saat menghubungkan ke MySQL: '{err}'")
        return None


def ambil_data_tabel(koneksi, nama_tabel):
    """Mengambil semua data dari tabel"""
    try:
        query = f"SELECT * FROM {nama_tabel}"
        df = pd.read_sql(query, koneksi)
        print(f"Berhasil mengambil data dari tabel: {nama_tabel}")
        return df
    except Error as err:
        print(f"Error saat mengambil data dari tabel '{nama_tabel}': '{err}'")
        return pd.DataFrame()  # Kembalikan DataFrame kosong jika ada error


def ekspor_ke_csv(dataframe, nama_file):
    """Mengekspor DataFrame ke file CSV."""
    try:
        dataframe.to_csv(nama_file, index=False, encoding="utf-8")
        print(f"Data berhasil diekspor ke '{nama_file}'")
    except Exception as e:
        print(f"Error saat mengekspor data ke CSV: '{e}'")


if __name__ == "__main__":

    # Buat koneksi database
    koneksi_db = koneksi_db()

    if koneksi_db:
        nama_tabel = "movies_all_data"
        nama_file_csv = "movies_data_fix.csv"

        # Ambil data ke dalam DataFrame
        df_film = ambil_data_tabel(koneksi_db, nama_tabel)

        if not df_film.empty:
            # Ekspor DataFrame ke CSV
            ekspor_ke_csv(df_film, nama_file_csv)
        else:
            print("Tidak ada data yang diambil untuk diekspor.")

        # Tutup koneksi
        koneksi_db.close()
        print("Koneksi MySQL ditutup.")
    else:
        print("Gagal membuat koneksi database. Ekspor CSV dibatalkan.")
