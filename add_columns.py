import sqlite3
db_path = "estimates.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check current columns
cur.execute("PRAGMA table_info(users)")
columns = [row[1] for row in cur.fetchall()]
print(f"Current columns: {columns}")

# Add missing columns
if 'email' not in columns:
    cur.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT 'admin@example.com'")
    print("Added email column")

if 'receive_notifications' not in columns:
    cur.execute("ALTER TABLE users ADD COLUMN receive_notifications INTEGER NOT NULL DEFAULT 1")
    print("Added receive_notifications column")

if 'updated_at' not in columns:
    cur.execute("ALTER TABLE users ADD COLUMN updated_at DATETIME")
    print("Added updated_at column")

conn.commit()
conn.close()
print("Database updated successfully")
