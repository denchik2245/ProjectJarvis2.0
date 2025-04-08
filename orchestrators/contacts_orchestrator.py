from agents.contacts_agent import ContactsAgent
from google_auth_manager import get_user_google_credentials

def handle_contacts_intent(intent, parameters, telegram_user_id):
    creds = get_user_google_credentials(str(telegram_user_id))
    if not creds:
        return "Для использования этой функции необходимо авторизоваться через Google."
    contacts_agent = ContactsAgent(credentials_info=creds)

    if intent == "search_contact":
        name = parameters.get("contact_name")
        company = parameters.get("company")
        if "requested_field" in parameters:
            requested = parameters.get("requested_field")
            if isinstance(requested, list):
                requested_fields = [x.lower() for x in requested]
            else:
                requested_fields = [str(requested).lower()]
        else:
            requested_fields = ["phone", "email", "birthday"]

        contacts = contacts_agent.search_contacts(name=name, company=company)
        if not contacts:
            return "Контакты не найдены."

        output_lines = []
        for idx, c in enumerate(contacts, start=1):
            lines = []
            lines.append(f"{idx}.")
            lines.append(f"Имя: {c['name']}")
            if c.get("companies"):
                lines.append(f"Компания: {', '.join(c['companies'])}")
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
                    lines.append(f"День рождения: {', '.join(c['birthdays'])}")
                else:
                    lines.append("День рождения: Не указан")
            output_lines.append("\n".join(lines))
        return "\n\n".join(output_lines)

    elif intent == "add_contact":
        contact_name = parameters.get("contact_name")
        phone = parameters.get("phone")
        company = parameters.get("company")
        birthday = parameters.get("birthday")
        if not contact_name or not phone:
            return "Для добавления контакта необходимы имя и телефон."
        result = contacts_agent.add_contact(contact_name, phone, company, birthday)
        return f"Контакт добавлен: {result.get('resourceName', 'неизвестно')}"

    else:
        return "Неподдерживаемый intent для контактов."
