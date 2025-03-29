from agents.contacts_agent import ContactsAgent
from agents.docs_agent import DocsAgent
from agents.gmail_agent import GmailAgent
from agents.drive_agent import DriveAgent

class Orchestrator:
    def __init__(self):
        self.contacts_agent = ContactsAgent()
        self.docs_agent = DocsAgent()
        self.gmail_agent = GmailAgent()
        self.drive_agent = DriveAgent()

    def handle_intent(self, intent: str, parameters: dict) -> str:
        print("Обработка intent:", intent, "с параметрами:", parameters)
        if intent == "search_contact":
            return self._handle_search_contact(parameters)
        elif intent == "search_document":
            return self._handle_search_document(parameters)
        elif intent == "send_email":
            return self._handle_send_email(parameters)
        elif intent == "show_messages":
            return self._handle_show_messages(parameters)
        elif intent == "clear_mail":
            return self._handle_clear_mail(parameters)
        elif intent == "save_photo":
            return self._handle_save_photo(parameters)
        elif intent == "show_photos":
            return self._handle_show_photos(parameters)
        elif intent == "add_contact":
            return self._handle_add_contact(parameters)
        else:
            return "Извините, я не понял вашу команду или это пока не реализовано."

    def _handle_search_contact(self, params: dict) -> str:
        # Существующий код поиска контактов...
        name = params.get("contact_name")
        company = params.get("company")
        requested = params.get("requested_field", "phone")
        if isinstance(requested, list):
            requested_fields = [x.lower() for x in requested]
        else:
            requested_fields = [str(requested).lower()]

        contacts = self.contacts_agent.search_contacts(name=name, company=company)
        if contacts:
            lines = []
            for c in contacts:
                base_info = f"Имя: {c['name']}"
                fields_info = []
                if "phone" in requested_fields:
                    if c.get("phones"):
                        fields_info.append(f"Тел: {', '.join(c['phones'])}")
                    else:
                        fields_info.append("Телефон не указан")
                if "email" in requested_fields:
                    if c.get("emails"):
                        fields_info.append(f"Email: {', '.join(c['emails'])}")
                    else:
                        fields_info.append("Email не указан")
                if "birthday" in requested_fields:
                    if c.get("birthdays"):
                        fields_info.append(f"День рождения: {', '.join(c['birthdays'])}")
                    else:
                        fields_info.append("День рождения не указан")
                line_parts = [base_info] + fields_info
                if c.get("companies"):
                    line_parts.append(f"Компания: {', '.join(c['companies'])}")
                lines.append("; ".join(line_parts))
            return "\n".join(lines)
        else:
            return "Контакты не найдены."

    def _handle_search_document(self, params: dict) -> str:
        keywords = params.get("keywords", [])
        docs = self.docs_agent.search_documents(keywords)
        if docs:
            lines = []
            for doc in docs:
                line = f"{doc.get('name')} (ссылка: {doc.get('webViewLink')})"
                lines.append(line)
            return "\n".join(lines)
        else:
            return "Ничего не найдено по заданным ключевым словам."

    def _handle_send_email(self, params: dict) -> str:
        to_address = params.get("to_address")
        message_content = params.get("message_content", "")
        scheduled_day = params.get("scheduled_day")
        subject = params.get("subject", "Письмо от вашего ассистента")

        if to_address:
            if scheduled_day:
                return self.gmail_agent.schedule_email(to_address, subject, message_content, scheduled_day)
            else:
                sent = self.gmail_agent.send_email(to_address, subject, message_content)
                return f"Письмо отправлено: {sent}"
        else:
            name = params.get("contact_name")
            company = params.get("company")
            contacts = self.contacts_agent.search_contacts(name=name, company=company)
            if not contacts:
                return "Контакт не найден."
            elif len(contacts) == 1:
                contact = contacts[0]
                if contact.get("emails"):
                    email_addr = contact["emails"][0]
                    if scheduled_day:
                        return self.gmail_agent.schedule_email(email_addr, subject, message_content, scheduled_day)
                    else:
                        sent = self.gmail_agent.send_email(email_addr, subject, message_content)
                        return f"Письмо отправлено: {sent}"
                else:
                    return f"У контакта {contact['name']} не указан email."
            else:
                lines = []
                for idx, contact in enumerate(contacts, start=1):
                    line = f"{idx}. {contact['name']}"
                    if contact.get("emails"):
                        line += f" (Email: {', '.join(contact['emails'])})"
                    else:
                        line += " (Email не указан)"
                    lines.append(line)
                return "Найдено несколько контактов:\n" + "\n".join(lines) + "\nПожалуйста, уточните номер нужного контакта."

    def _handle_show_messages(self, params: dict) -> str:
        name = params.get("contact_name")
        company = params.get("company")
        contacts = self.contacts_agent.search_contacts(name=name, company=company)
        if not contacts:
            return "Контакт не найден."
        elif len(contacts) == 1:
            contact = contacts[0]
            if contact.get("emails"):
                email_addr = contact["emails"][0]
                messages = self.gmail_agent.list_messages_from_address(email_addr, max_results=10)
                if messages:
                    lines = []
                    for msg in messages:
                        lines.append(
                            f"Тема: {msg.get('subject')}\nДата: {msg.get('date')}\nСодержимое: {msg.get('snippet')}\n")
                    return "\n".join(lines)
                else:
                    return "Сообщения не найдены."
            else:
                return f"У контакта {contact['name']} не указан email."
        else:
            lines = []
            for idx, contact in enumerate(contacts, start=1):
                line = f"{idx}. {contact['name']}"
                if contact.get("emails"):
                    line += f" (Email: {', '.join(contact['emails'])})"
                else:
                    line += " (Email не указан)"
                lines.append(line)
            return "Найдено несколько контактов:\n" + "\n".join(lines) + "\nПожалуйста, уточните номер нужного контакта."

    def _handle_clear_mail(self, params: dict) -> str:
        target = params.get("target", "").lower()
        results = []
        if target in ["spam", "spam_and_trash"]:
            res = self.gmail_agent.empty_spam()
            results.append(res)
        if target in ["trash", "spam_and_trash"]:
            res = self.gmail_agent.empty_trash()
            results.append(res)
        if results:
            return "\n".join(results)
        else:
            return "Не указано, какую папку очищать. Укажите 'spam', 'trash' или 'spam_and_trash'."

    def _handle_save_photo(self, params: dict) -> str:
        file_path = params.get("file_path")
        file_name = params.get("file_name")
        folder_name = params.get("folder_name", "Photos")
        if not file_path or not file_name:
            return "Параметры файла не указаны."
        result = self.drive_agent.save_photo(file_path, file_name, folder_name)
        return f"Фото сохранено: {result.get('name')} (ID: {result.get('id')})"

    def _handle_show_photos(self, params: dict) -> str:
        folder_keyword = params.get("folder_keyword")
        if not folder_keyword:
            return "Не указано название папки для поиска фотографий."
        photos = self.drive_agent.list_photos_in_folder(folder_keyword)
        if photos:
            lines = []
            for photo in photos:
                line = f"{photo.get('name')} (ссылка: {photo.get('webViewLink')})"
                lines.append(line)
            return "\n".join(lines)
        else:
            return "Фотографии не найдены в указанной папке."

    def _handle_add_contact(self, params: dict) -> str:
        contact_name = params.get("contact_name")
        phone = params.get("phone")
        company = params.get("company")
        birthday = params.get("birthday")
        if not contact_name or not phone:
            return "Для добавления контакта необходимы имя и телефон."
        result = self.contacts_agent.add_contact(contact_name, phone, company, birthday)
        # result содержит, например, поле 'resourceName'
        return f"Контакт добавлен: {result.get('resourceName', 'неизвестно')}"