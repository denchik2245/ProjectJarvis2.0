from agents.contacts_agent import ContactsAgent
from agents.docs_agent import DocsAgent
from agents.gmail_agent import GmailAgent


class Orchestrator:
    def __init__(self):
        self.contacts_agent = ContactsAgent()
        self.docs_agent = DocsAgent()
        self.gmail_agent = GmailAgent()

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
        else:
            return "Извините, я не понял вашу команду или это пока не реализовано."

    def _handle_search_contact(self, params: dict) -> str:
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
        # Если прямой адрес указан
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
            # Поиск контакта по имени и/или компании
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
                return "Найдено несколько контактов:\n" + "\n".join(
                    lines) + "\nПожалуйста, уточните номер нужного контакта."

    def _handle_show_messages(self, params: dict) -> str:
        """
        Обрабатывает запрос "Покажи последние сообщения от <контакт>".
        Находит контакт по имени (и, опционально, компании), затем извлекает email и запрашивает последние сообщения.
        Выводит тему, дату и краткий фрагмент содержимого каждого письма.
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
            return "Найдено несколько контактов:\n" + "\n".join(
                lines) + "\nПожалуйста, уточните номер нужного контакта."

    def _handle_clear_mail(self, params: dict) -> str:
        """
        Обрабатывает запросы на очистку почтовых папок.
        Ожидается, что параметр "target" может принимать значения:
         - "spam" – очистить папку спам,
         - "trash" – очистить корзину,
         - "spam_and_trash" – сначала очистить спам, затем корзину.
        """
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