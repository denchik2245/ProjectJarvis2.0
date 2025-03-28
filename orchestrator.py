from agents.contacts_agent import ContactsAgent
from agents.docs_agent import DocsAgent

class Orchestrator:
    def __init__(self):
        self.contacts_agent = ContactsAgent()
        self.docs_agent = DocsAgent()

    def handle_intent(self, intent: str, parameters: dict) -> str:
        # Вывод для отладки: печатаем полученный intent и параметры
        print("Обработка intent:", intent, "с параметрами:", parameters)
        if intent == "search_contact":
            return self._handle_search_contact(parameters)
        elif intent == "search_document":
            return self._handle_search_document(parameters)
        elif intent == "send_email":
            return self._handle_send_email(parameters)
        else:
            return "Извините, я не понял вашу команду или это пока не реализовано."

    def _handle_search_contact(self, params: dict) -> str:
        name = params.get("contact_name")
        company = params.get("company")
        contacts = self.contacts_agent.search_contacts(name=name, company=company)
        if contacts:
            lines = []
            for c in contacts:
                parts = [f"Имя: {c['name']}"]
                if c["phones"]:
                    parts.append(f"Тел: {', '.join(c['phones'])}")
                if c["companies"]:
                    parts.append(f"Компания: {', '.join(c['companies'])}")
                lines.append("; ".join(parts))
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
        # Пример реализации для отправки писем, допишите по необходимости
        to_address = params.get("to_address")
        subject = params.get("subject", "")
        body = params.get("body", "")
        if not to_address:
            return "Не указан адрес получателя."
        result = self.gmail_agent.send_email(to_address, subject, body)
        return f"Письмо успешно отправлено: {result}"
