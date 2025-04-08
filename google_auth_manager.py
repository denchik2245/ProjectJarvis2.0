import sqlite3
import json

def get_user_google_credentials(telegram_user_id: str):
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("SELECT credentials FROM google_credentials WHERE telegram_user_id = ?", (telegram_user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None
