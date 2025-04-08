# from googleapiclient.discovery import build
# from google.oauth2.credentials import Credentials
# from config import GOOGLE_CREDENTIALS_PATH


# class DocsAgent:
#     def __init__(self):
#         # Загружаем сохранённые учетные данные Google
#         creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)
#         # Создаем сервис для работы с Google Drive API
#         self.drive_service = build('drive', 'v3', credentials=creds)

#     def search_documents(self, keywords):
#         """
#         Ищет Google Документы по ключевым словам в их содержимом.

#         Параметры:
#             keywords (list): список ключевых слов для поиска (например, ["цена", "холодильник"]).

#         Алгоритм:
#           1. Фильтруем файлы, выбирая только Google Документы
#              (mimeType = 'application/vnd.google-apps.document') и исключая удалённые (trashed = false).
#           2. Формируем запрос, где если хотя бы одно из ключевых слов встречается в тексте документа, он будет найден.
#              Для этого условия ключевых слов объединяются оператором OR.
#           3. Выполняем запрос через Drive API и возвращаем список файлов с основными полями:
#              id, name, webViewLink.
#         """
#         if not keywords:
#             return []

#         # Формируем условия для ключевых слов с объединением через OR
#         query_conditions = [f"fullText contains '{kw}'" for kw in keywords]
#         keywords_query = "(" + " or ".join(query_conditions) + ")"

#         # Ограничиваем поиск только Google Документами и исключаем удалённые файлы
#         query = "mimeType = 'application/vnd.google-apps.document' and trashed = false and " + keywords_query

#         # Отладочный вывод: выводим сформированный запрос
#         print("DocsAgent Query:", query)

#         try:
#             response = self.drive_service.files().list(
#                 q=query,
#                 fields="files(id, name, webViewLink)"
#             ).execute()
#             files = response.get('files', [])
#             print(f"Найдено документов: {len(files)}")
#             return files
#         except Exception as e:
#             print("Ошибка при поиске документов:", e)
#             return []

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from config import GOOGLE_CREDENTIALS_PATH


class DocsAgent:
    def __init__(self):
        # Загружаем сохранённые учетные данные Google
        self.creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)
        # Создаём сервис для работы с Google Drive API (версия v3)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def search_documents(self, keywords, mode='or', search_in='both'):
        """
        Ищет Google Документы по ключевым словам в тексте, названии или обоих.

        Параметры:
            keywords (list): Ключевые слова (например, ["бюджет", "финансовый"])
            mode (str): 'or' (по умолчанию) — хотя бы одно слово;
                        'and' — все слова должны присутствовать
            search_in (str): 'text' — искать только в тексте документа
                             'title' — искать только в названии
                             'both' — искать и там, и там

        Возвращает:
            Список найденных документов с id, name, webViewLink
        """
        if not keywords:
            return []

        mode = mode.lower()
        if mode not in ['and', 'or']:
            mode = 'or'  # защита от неправильного ввода

        search_in = search_in.lower()
        if search_in not in ['text', 'title', 'both']:
            search_in = 'both'  # защита от неправильного ввода

        # Условия для поиска по содержимому
        text_conditions = [f"fullText contains '{kw}'" for kw in keywords]
        # Условия для поиска по названию
        name_conditions = [f"name contains '{kw}'" for kw in keywords]

        # Объединение условий в зависимости от режима и области поиска
        if search_in == 'text':
            query_parts = text_conditions
        elif search_in == 'title':
            query_parts = name_conditions
        else:  # both
            query_parts = text_conditions + name_conditions

        joined_query = f"({' {} '.format(mode).join(query_parts)})"

        # Финальный запрос: только документы и не удалённые
        query = f"mimeType = 'application/vnd.google-apps.document' and trashed = false and {joined_query}"

        print("DocsAgent Query:", query)

        try:
            response = self.drive_service.files().list(
                q=query,
                fields="files(id, name, webViewLink)"
            ).execute()
            files = response.get('files', [])
            print(f"Найдено документов: {len(files)}")
            return files

        except HttpError as e:
            if e.resp.status == 401:
                print("⚠️ Ошибка авторизации: токен истёк или недействителен. Проверь credentials.json.")
            else:
                print("Ошибка при поиске документов:", e)
            return []
