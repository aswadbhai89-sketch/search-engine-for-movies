import sqlite3

# Database banao aur table banao
conn = sqlite3.connect('movies.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS movies (
        id TEXT PRIMARY KEY,
        title TEXT,
        year TEXT,
        genre TEXT,
        rating REAL,
        plot TEXT,
        poster TEXT
    )
''')

conn.commit()
conn.close()

print("✅ Database aur table ready!")