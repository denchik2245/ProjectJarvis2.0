from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import GOOGLE_CREDENTIALS_PATH


class DocsAgent:
    def __init__(self):
        # Загружаем сохранённые учетные данные Google
        creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)
        # Создаем сервис для работы с Google Drive API
        self.drive_service = build('drive', 'v3', credentials=creds)

    def search_documents(self, keywords):
        """
        Ищет Google Документы по ключевым словам в их содержимом.

        Параметры:
            keywords (list): список ключевых слов для поиска (например, ["цена", "холодильник"]).

        Алгоритм:
          1. Фильтруем файлы, выбирая только Google Документы
             (mimeType = 'application/vnd.google-apps.document') и исключая удалённые (trashed = false).
          2. Формируем запрос, где если хотя бы одно из ключевых слов встречается в тексте документа, он будет найден.
             Для этого условия ключевых слов объединяются оператором OR.
          3. Выполняем запрос через Drive API и возвращаем список файлов с основными полями:
             id, name, webViewLink.
        """
        if not keywords:
            return []

        # Формируем условия для ключевых слов с объединением через OR
        query_conditions = [f"fullText contains '{kw}'" for kw in keywords]
        keywords_query = "(" + " or ".join(query_conditions) + ")"

        # Ограничиваем поиск только Google Документами и исключаем удалённые файлы
        query = "mimeType = 'application/vnd.google-apps.document' and trashed = false and " + keywords_query

        # Отладочный вывод: выводим сформированный запрос
        print("DocsAgent Query:", query)

        try:
            response = self.drive_service.files().list(
                q=query,
                fields="files(id, name, webViewLink)"
            ).execute()
            files = response.get('files', [])
            print(f"Найдено документов: {len(files)}")
            return files
        except Exception as e:
            print("Ошибка при поиске документов:", e)
            return []