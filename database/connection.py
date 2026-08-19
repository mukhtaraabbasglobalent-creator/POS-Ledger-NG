import sqlite3
import os

DB_FOLDER = "data"
DB_NAME = os.path.join(DB_FOLDER, "posledger.db")


def get_connection():
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
