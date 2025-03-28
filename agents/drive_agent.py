# agents/drive_agent.py
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from config import GOOGLE_CREDENTIALS_PATH

class DriveAgent:
    def __init__(self):
        creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)
        self.service = build('drive', 'v3', credentials=creds)

    def _get_or_create_folder(self, folder_name: str) -> str:
        """
        Ищет папку с заданным именем (точное совпадение или по Contains).
        Если не найдена – создаёт её.
        Возвращает идентификатор папки.
        """
        query = (
            f"mimeType = 'application/vnd.google-apps.folder' "
            f"and name = '{folder_name}' and trashed = false"
        )
        response = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get('files', [])
        if files:
            return files[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')

    def save_photo(self, file_path: str, file_name: str, folder_name: str = "Photos") -> dict:
        """
        Сохраняет изображение, расположенное по file_path, в папку folder_name на Google Drive.
        Если папка не существует – создаёт её.
        Возвращает словарь с информацией о сохранённом файле (например, его ID).
        """
        folder_id = self._get_or_create_folder(folder_name)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        # Определяем mimetype по расширению, можно улучшить эту логику.
        _, ext = os.path.splitext(file_name)
        if ext.lower() in ['.jpg', '.jpeg']:
            mimetype = 'image/jpeg'
        elif ext.lower() == '.png':
            mimetype = 'image/png'
        else:
            mimetype = 'application/octet-stream'
        media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
        saved_file = self.service.files().create(
            body=file_metadata, media_body=media, fields='id, name'
        ).execute()
        return saved_file

    def list_photos_in_folder(self, folder_keyword: str) -> list:
        """
        Ищет папку, имя которой содержит folder_keyword (например, "домашка").
        Если папка найдена, возвращает список файлов в этой папке,
        у которых mimetype начинается с "image/".
        Каждый файл возвращается как словарь с ключами: id, name, webViewLink.
        Если папка не найдена, возвращает пустой список.
        """
        # Ищем папку по ключевому слову
        folder_query = (
            f"mimeType = 'application/vnd.google-apps.folder' "
            f"and name contains '{folder_keyword}' and trashed = false"
        )
        folder_resp = self.service.files().list(q=folder_query, fields="files(id, name)").execute()
        folders = folder_resp.get('files', [])
        if not folders:
            return []
        folder_id = folders[0]['id']
        # Ищем файлы в найденной папке, где mimetype начинается с "image/"
        file_query = (
            f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        )
        files_resp = self.service.files().list(
            q=file_query,
            fields="files(id, name, webViewLink)"
        ).execute()
        return files_resp.get('files', [])
