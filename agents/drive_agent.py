import os
import io
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from config import GOOGLE_CREDENTIALS_PATH

class DriveAgent:
    def __init__(self, credentials_info=None):
        if credentials_info is not None:
            creds = Credentials.from_authorized_user_info(credentials_info)
        else:
            creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)

        self.service = build('drive', 'v3', credentials=creds)

    def _get_or_create_folder(self, folder_name: str) -> str:
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
        folder_id = self._get_or_create_folder(folder_name)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
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
        folder_query = (
            f"mimeType = 'application/vnd.google-apps.folder' "
            f"and name contains '{folder_keyword}' and trashed = false"
        )
        folder_resp = self.service.files().list(q=folder_query, fields="files(id, name)").execute()
        folders = folder_resp.get('files', [])
        print("Найденные папки для ключевого слова:", folder_keyword, folders)
        if not folders:
            return []
        folder_id = folders[0]['id']
        file_query = (
            f"'{folder_id}' in parents and trashed = false and mimeType contains 'image/'"
        )
        files_resp = self.service.files().list(q=file_query, fields="files(id, name, mimeType, webViewLink)").execute()
        photos = files_resp.get('files', [])
        print("Найденные фотографии:", photos)
        return photos

    def list_files_in_folder(self, folder_keyword: str, include_photos: bool = False) -> list:
        """
        Возвращает список файлов из папки, имя которой содержит folder_keyword.
        Если include_photos == True, возвращаются все файлы,
        иначе – только файлы, не являющиеся изображениями.
        """
        folder_query = (
            f"mimeType = 'application/vnd.google-apps.folder' "
            f"and name contains '{folder_keyword}' and trashed = false"
        )
        folder_resp = self.service.files().list(q=folder_query, fields="files(id, name)").execute()
        folders = folder_resp.get("files", [])
        if not folders:
            return []
        folder_id = folders[0]["id"]
        if include_photos:
            file_query = f"'{folder_id}' in parents and trashed = false"
        else:
            file_query = f"'{folder_id}' in parents and not mimeType contains 'image/' and trashed = false"
        files_resp = self.service.files().list(q=file_query, fields="files(id, name, webViewLink)").execute()
        files = files_resp.get("files", [])
        return files

    def download_file(self, file_id: str, destination_path: str) -> None:
        """
        Скачивает файл с Google Drive по file_id и сохраняет его в destination_path.
        """
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        with open(destination_path, "wb") as f:
            f.write(fh.getvalue())