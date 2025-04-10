#add_stab_gif.py

import sqlite3

DB_PATH = 'users.db'

def add_stab_gif(url: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO stab_gifs (url) VALUES (?)', (url,))
    conn.commit()
    conn.close()
    print("✅ GIF URL added successfully!")

if __name__ == "__main__":
    url = input("Paste the GIF URL to add: ").strip()
    if url:
        add_stab_gif(url)
    else:
        print("⚠️ No URL provided.")
