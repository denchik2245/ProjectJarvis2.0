import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from config import SCOPES, CLIENT_SECRETS_FILE, GOOGLE_CREDENTIALS_PATH


def main():
    # Создаем flow для OAuth2
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        SCOPES
    )
    creds = flow.run_local_server(port=0)

    # Сохраняем токены в файл
    os.makedirs(os.path.dirname(GOOGLE_CREDENTIALS_PATH), exist_ok=True)
    with open(GOOGLE_CREDENTIALS_PATH, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())

    print(f"Авторизация прошла успешно. Данные сохранены в {GOOGLE_CREDENTIALS_PATH}")


if __name__ == '__main__':
    main()
