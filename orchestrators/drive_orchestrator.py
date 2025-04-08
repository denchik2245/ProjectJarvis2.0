from agents.drive_agent import DriveAgent
from google_auth_manager import get_user_google_credentials


def handle_drive_intent(intent, parameters, telegram_user_id):
    creds = get_user_google_credentials(str(telegram_user_id))
    if not creds:
        return {"attachments": [], "links": []}
    drive_agent = DriveAgent(credentials_info=creds)

    if intent == "save_photo":
        file_path = parameters.get("file_path")
        file_name = parameters.get("file_name")
        folder_name = parameters.get("folder_name", "Photos")
        if not file_path or not file_name:
            return "Параметры файла не указаны."
        result = drive_agent.save_photo(file_path, file_name, folder_name)
        return f"Фото сохранено: {result.get('name')} (ID: {result.get('id')})"

    elif intent == "show_photos":
        folder_keyword = parameters.get("folder_keyword")
        if not folder_keyword:
            return {"attachments": [], "links": []}
        photos = drive_agent.list_photos_in_folder(folder_keyword)
        if not photos:
            return {"attachments": [], "links": []}
        attachments = photos[:5]
        links = photos[5:]
        att_list = [(p.get("id"), p.get("name")) for p in attachments]
        link_list = [f"{p.get('name')}: {p.get('webViewLink')}" for p in links]
        return {"attachments": att_list, "links": link_list}

    elif intent == "show_files":
        folder_keyword = parameters.get("folder_keyword")
        include_photos = parameters.get("include_photos", False)
        if isinstance(include_photos, str):
            include_photos = include_photos.lower() == "true"
        if not folder_keyword:
            return {"attachments": [], "links": []}
        files = drive_agent.list_files_in_folder(folder_keyword, include_photos)
        if not files:
            return {"attachments": [], "links": []}
        attachments = files[:10]
        links = files[10:]
        att_list = [(f.get("id"), f.get("name")) for f in attachments]
        link_list = [f"{f.get('name')}: {f.get('webViewLink')}" for f in links]
        return {"attachments": att_list, "links": link_list}

    else:
        return {"attachments": [], "links": []}
