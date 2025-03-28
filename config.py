import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Настройки для Deepseek (локальной модели)
DEEPSEEKS_BASE_URL = os.getenv("DEEPSEEKS_BASE_URL", "http://127.0.0.1:11434/v1/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-r1:14b")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))

# Google OAuth
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/documents',
]

# Пути к файлам с учётными данными:
CLIENT_SECRETS_FILE = "credentials/Gmail_credential.json"
GOOGLE_CREDENTIALS_PATH = "credentials/google_credentials.json"
