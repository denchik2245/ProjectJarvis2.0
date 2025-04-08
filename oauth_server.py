import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Разрешаем HTTP для разработки

import sqlite3
import json
import requests
from flask import Flask, request, redirect
from google_auth_oauthlib.flow import InstalledAppFlow
from config import CLIENT_SECRETS_FILE, SCOPES, TELEGRAM_BOT_TOKEN

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_FILE = "auth.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS google_credentials (
            telegram_user_id TEXT PRIMARY KEY,
            credentials TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()

pending_auth = {}
REDIRECT_URI = "http://localhost:5000/oauth2callback"


def send_telegram_message(user_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": user_id, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Ошибка отправки сообщения в Telegram:", e)


@app.route("/authorize")
def authorize():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Missing user_id parameter", 400

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    pending_auth[state] = user_id
    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = request.args.get("state")
    if state not in pending_auth:
        return "Invalid state parameter", 400

    user_id = pending_auth.pop(state)

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = REDIRECT_URI
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        error_message = f"Ошибка получения токена: {str(e)}"
        send_telegram_message(user_id, f"Авторизация не прошла. {error_message}")
        return error_message, 400

    credentials = flow.credentials
    credentials_json = credentials.to_json()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO google_credentials (telegram_user_id, credentials)
        VALUES (?, ?)
    """, (user_id, credentials_json))
    conn.commit()
    conn.close()

    # Отправляем уведомление в Telegram о успешной авторизации.
    send_telegram_message(user_id,
                          "Авторизация прошла успешно! Теперь вы можете использовать Google-сервисы через бота.")

    return (
        f"Авторизация прошла успешно для пользователя {user_id}.<br>"
        "Теперь вы можете использовать Google-сервисы через Telegram-бота.<br>"
        "Вы можете закрыть это окно и вернуться в Telegram."
    )


@app.route("/get_credentials/<telegram_user_id>")
def get_credentials(telegram_user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT credentials FROM google_credentials WHERE telegram_user_id = ?", (telegram_user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.dumps(json.loads(row[0]), indent=2, ensure_ascii=False)
    else:
        return "Credentials not found", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)