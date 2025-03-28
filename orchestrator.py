from agents.contacts_agent import ContactsAgent
from agents.docs_agent import DocsAgent
# Если реализуете отправку писем, подключите GmailAgent, иначе можно убрать.
# from agents.gmail_agent import GmailAgent

class Orchestrator:
    def __init__(self):
        self.contacts_agent = ContactsAgent()
        self.docs_agent = DocsAgent()
        # self.gmail_agent = GmailAgent()

    def handle_intent(self, intent: str, parameters: dict) -> str:
        # Отладочный вывод
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
        # Новый параметр для уточнения: какое поле возвращать ("phone" по умолчанию)
        requested_field = params.get("requested_field", "phone").lower()

        contacts = self.contacts_agent.search_contacts(name=name, company=company)
        if contacts:
            lines = []
            for c in contacts:
                # Формируем ответ в зависимости от запрошенного поля
                base_info = f"Имя: {c['name']}"
                if requested_field == "birthday":
                    if c.get("birthdays"):
                        field_info = f"День рождения: {', '.join(c['birthdays'])}"
                    else:
                        field_info = "День рождения не указан"
                elif requested_field == "email":
                    if c.get("emails"):
                        field_info = f"Email: {', '.join(c['emails'])}"
                    else:
                        field_info = "Email не указан"
                else:
                    if c.get("phones"):
                        field_info = f"Тел: {', '.join(c['phones'])}"
                    else:
                        field_info = "Телефон не указан"
                if c.get("companies"):
                    comp_info = f"Компания: {', '.join(c['companies'])}"
                    line = "; ".join([base_info, field_info, comp_info])
                else:
                    line = "; ".join([base_info, field_info])
                lines.append(line)
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
