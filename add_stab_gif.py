# replace_stab_gifs.py

import sqlite3

DB_PATH = 'users.db'
URL_FILE = 'stabGifUrls.txt'

def clear_stab_gifs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM stab_gifs')
    conn.commit()
    conn.close()
    print("🗑️ Existing stab GIFs cleared.")

def add_stab_gif(url: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO stab_gifs (url) VALUES (?)', (url,))
    conn.commit()
    conn.close()

def load_urls_from_file():
    urls = []
    with open(URL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("http") and "gif" in line:
                urls.append(line)
    return urls

if __name__ == "__main__":
    clear_stab_gifs()
    urls = load_urls_from_file()

    for url in urls:
        add_stab_gif(url)
        print(f"✅ Added: {url}")

    print(f"\n🎉 Done! {len(urls)} GIFs added from {URL_FILE}.")
