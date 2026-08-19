import sqlite3

DB_NAME = "data/posledger.db"


def create_credit_table():

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customer_credit (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        customer_id INTEGER NOT NULL,

        sale_id INTEGER,

        total_amount REAL NOT NULL,

        amount_paid REAL DEFAULT 0,

        balance REAL NOT NULL,

        status TEXT DEFAULT 'UNPAID',

        staff_name TEXT,

        created_date TEXT,

        FOREIGN KEY(customer_id) REFERENCES customers(id)

    )
    """)

    conn.commit()
    conn.close()

    print("Customer Credit table created successfully.")


if __name__ == "__main__":
    create_credit_table()
