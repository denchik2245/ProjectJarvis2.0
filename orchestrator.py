from agents.contacts_agent import ContactsAgent
from agents.docs_agent import DocsAgent
from agents.format_date import format_date
from agents.gmail_agent import GmailAgent
from agents.drive_agent import DriveAgent

class Orchestrator:
    def __init__(self):
        self.contacts_agent = ContactsAgent()
        self.docs_agent = DocsAgent()
        self.gmail_agent = GmailAgent()
        self.drive_agent = DriveAgent()

    def handle_intent(self, intent: str, parameters: dict):
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
        elif intent == "show_files":
            return self._handle_show_files(parameters)
        else:
            return "Извините, я не понял вашу команду или это пока не реализовано."

    def _handle_search_contact(self, params: dict) -> str:
        name = params.get("contact_name")
        company = params.get("company")
        # Если пользователь явно указал, что хочет видеть только определённые данные,
        # используем их, иначе выводим все (phone, email, birthday).
        if "requested_field" in params:
            requested = params.get("requested_field")
            if isinstance(requested, list):
                requested_fields = [x.lower() for x in requested]
            else:
                requested_fields = [str(requested).lower()]
        else:
            requested_fields = ["phone", "email", "birthday"]

        contacts = self.contacts_agent.search_contacts(name=name, company=company)
        if not contacts:
            return "Контакты не найдены."

        def format_birthday(bday_str):
            # Ожидается формат "DD.MM" или "DD.MM.YYYY"
            parts = bday_str.split('.')
            if len(parts) < 2:
                return bday_str
            day = parts[0]
            month = parts[1].zfill(2)
            month_names = {
                "01": "января", "02": "февраля", "03": "марта", "04": "апреля",
                "05": "мая", "06": "июня", "07": "июля", "08": "августа",
                "09": "сентября", "10": "октября", "11": "ноября", "12": "декабря"
            }
            return f"{day} {month_names.get(month, month)}"

        output_lines = []
        for idx, c in enumerate(contacts, start=1):
            lines = []
            lines.append(f"{idx}.")
            lines.append(f"Имя: {c['name']}")
            # Если задана компания (по фильтру), выводим её всегда
            if c.get("companies"):
                lines.append(f"Компания: {', '.join(c['companies'])}")
            # Выводим только те поля, которые запрошены
            if "phone" in requested_fields:
                if c.get("phones"):
                    lines.append(f"Номер телефона: {', '.join(c['phones'])}")
                else:
                    lines.append("Номер телефона: Не указан")
            if "email" in requested_fields:
                if c.get("emails"):
                    lines.append(f"Электронная почта: {', '.join(c['emails'])}")
                else:
                    lines.append("Электронная почта: Не указана")
            if "birthday" in requested_fields:
                if c.get("birthdays"):
                    # Форматируем каждый день рождения
                    formatted_bdays = [format_birthday(b) for b in c["birthdays"]]
                    lines.append(f"День рождения: {', '.join(formatted_bdays)}")
                else:
                    lines.append("День рождения: Не указан")
            output_lines.append("\n".join(lines))
        return "\n\n".join(output_lines)

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
                self.gmail_agent.schedule_email(to_address, subject, message_content, scheduled_day)
                return f"Письмо запланировано для отправки на электронную почту: {to_address}"
            else:
                self.gmail_agent.send_email(to_address, subject, message_content)
                return f"Письмо отправлено на электронную почту: {to_address}"
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
                        self.gmail_agent.schedule_email(email_addr, subject, message_content, scheduled_day)
                        return f"Письмо запланировано для отправки на электронную почту: {email_addr}"
                    else:
                        self.gmail_agent.send_email(email_addr, subject, message_content)
                        return f"Письмо отправлено на электронную почту: {email_addr}"
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
                return "Найдено несколько контактов:\n" + "\n".join(
                    lines) + "\nПожалуйста, уточните номер нужного контакта."

    def _handle_show_messages(self, params: dict) -> str:
        """
        Обрабатывает запрос "Покажи последние сообщения от <контакт>".
        Находит контакт по имени (и, опционально, компании), затем извлекает email и запрашивает последние сообщения.
        Выводит данные в следующем формате:
        Тема: Тестовое письмо
        Дата: 28 марта 2025 год, 22:59
        Содержимое: Привет, как дела, что делаешь
        """
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
                        subject = msg.get('subject', '(без темы)')
                        raw_date = msg.get('date', '')
                        formatted_date = format_date(raw_date)
                        snippet = msg.get('snippet', '')
                        lines.append(f"Тема: {subject}\nДата: {formatted_date}\nСодержимое: {snippet}")
                    return "\n\n".join(lines)
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
            return "Найдено несколько контактов:\n" + "\n".join(
                lines) + "\nПожалуйста, уточните номер нужного контакта."

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

    def _handle_show_photos(self, params: dict) -> dict:
        """
        Возвращает словарь с двумя ключами:
         - "attachments": список кортежей (file_id, file_name) для первых 10 фотографий.
         - "links": список строк вида "Имя файла: ссылка" для оставшихся фотографий.
        """
        folder_keyword = params.get("folder_keyword")
        if not folder_keyword:
            return {"attachments": [], "links": []}
        photos = self.drive_agent.list_photos_in_folder(folder_keyword)
        if not photos:
            return {"attachments": [], "links": []}
        attachments = photos[:5]
        links = photos[5:]
        att_list = [(p.get("id"), p.get("name")) for p in attachments]
        link_list = [f"{p.get('name')}: {p.get('webViewLink')}" for p in links]
        return {"attachments": att_list, "links": link_list}

    def _handle_show_files(self, params: dict) -> dict:
        """
        Возвращает словарь с двумя ключами:
         - "attachments": список кортежей (file_id, file_name) для первых 10 файлов (не фотографий),
         - "links": список строк вида "Имя файла: ссылка" для остальных файлов.
        Если параметр include_photos равен true, возвращаются все файлы.
        """
        folder_keyword = params.get("folder_keyword")
        include_photos = params.get("include_photos", False)
        if isinstance(include_photos, str):
            include_photos = include_photos.lower() == "true"
        if not folder_keyword:
            return {"attachments": [], "links": []}
        files = self.drive_agent.list_files_in_folder(folder_keyword, include_photos)
        if not files:
            return {"attachments": [], "links": []}
        attachments = files[:10]
        links = files[10:]
        att_list = [(f.get("id"), f.get("name")) for f in attachments]
        link_list = [f"{f.get('name')}: {f.get('webViewLink')}" for f in links]
        return {"attachments": att_list, "links": link_list}
