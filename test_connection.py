from database.connection import get_connection

conn = get_connection()
print("✅ Database Connected Successfully")
conn.close()
