import sqlite3
import os

DB_NAME = "data/posledger.db"


def create_tables():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # ==============================
    # USERS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        pin TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # CUSTOMERS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        phone TEXT UNIQUE,
        email TEXT,
        address TEXT,
        next_of_kin TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # PRODUCTS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        sku TEXT UNIQUE,
        barcode TEXT UNIQUE,
        category TEXT,
        buying_price REAL NOT NULL,
        selling_price REAL NOT NULL,
        current_stock REAL DEFAULT 0,
        minimum_stock REAL DEFAULT 0,
        unit TEXT DEFAULT 'EA',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # INVENTORY MOVEMENTS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory_movements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        movement_type TEXT NOT NULL,
        quantity REAL NOT NULL,
        reason TEXT,
        movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    # ==============================
    # PRICE HISTORY
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS price_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        old_price REAL,
        new_price REAL,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    # ==============================
    # TRANSACTIONS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        charge REAL DEFAULT 0,
        profit REAL DEFAULT 0,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """)

    # ==============================
    # EXPENSES
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_name TEXT NOT NULL,
        amount REAL NOT NULL,
        expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # CREDITORS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS creditors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        phone TEXT,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'UNPAID',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # DEBTORS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS debtors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        phone TEXT,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'UNPAID',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # BALANCE
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS balance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cash_balance REAL DEFAULT 0,
        wallet_balance REAL DEFAULT 0,
        opening_balance REAL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ==============================
    # AUDIT LOGS
    # ==============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    print("Database created successfully.")


if __name__ == "__main__":
    create_tables()
