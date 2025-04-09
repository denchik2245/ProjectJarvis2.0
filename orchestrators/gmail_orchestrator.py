from agents.gmail_agent import GmailAgent
from agents.contacts_agent import ContactsAgent
from agents.format_date import format_date
from google_auth_manager import get_user_google_credentials


def handle_gmail_intent(intent, parameters, telegram_user_id):
    creds = get_user_google_credentials(str(telegram_user_id))
    if not creds:
        return "Для использования этой функции необходимо авторизоваться через Google."
    gmail_agent = GmailAgent(credentials_info=creds)
    contacts_agent = ContactsAgent(credentials_info=creds)

    if intent == "send_email":
        to_address = parameters.get("to_address")
        message_content = parameters.get("message_content", "")
        scheduled_day = parameters.get("scheduled_day")
        subject = parameters.get("subject", "Письмо от вашего ассистента")

        # Если адрес получателя явно указан
        if to_address:
            if scheduled_day:
                gmail_agent.schedule_email(to_address, subject, message_content, scheduled_day)
                return f"Письмо запланировано для отправки на электронную почту: {to_address}"
            else:
                gmail_agent.send_email(to_address, subject, message_content)
                return f"Письмо отправлено на электронную почту: {to_address}"

        # Если адрес получателя НЕ указан, пытаемся взять его из контактов
        else:
            name = parameters.get("contact_name")
            company = parameters.get("company")
            contacts = contacts_agent.search_contacts(name=name, company=company)
            if not contacts:
                return "Контакт не найден."
            elif len(contacts) == 1:
                # Единственный контакт
                contact = contacts[0]
                if contact.get("emails"):
                    email_addr = contact["emails"][0]
                    if scheduled_day:
                        gmail_agent.schedule_email(email_addr, subject, message_content, scheduled_day)
                        return f"Письмо запланировано для отправки на электронную почту: {email_addr}"
                    else:
                        gmail_agent.send_email(email_addr, subject, message_content)
                        return f"Письмо отправлено на электронную почту: {email_addr}"
                else:
                    return f"У контакта {contact['name']} не указан email."
            else:
                # Фильтруем контакты – оставляем только те, у которых есть email
                contacts_with_email = [c for c in contacts if c.get("emails")]
                lines = []
                for idx, contact in enumerate(contacts_with_email, start=1):
                    line = f"{idx}. {contact['name']} (Email: {', '.join(contact['emails'])})"
                    lines.append(line)
                return {
                    "action": "multiple_contacts",
                    "text": (
                            "Найдено несколько контактов:\n"
                            + "\n".join(lines)
                            + "\nПожалуйста, укажите номер нужного контакта."
                    ),
                    "contacts": contacts_with_email,
                    "message_content": message_content,
                    "subject": subject,
                    "scheduled_day": scheduled_day
                }

    elif intent == "show_messages":
        name = parameters.get("contact_name")
        company = parameters.get("company")
        contacts = contacts_agent.search_contacts(name=name, company=company)
        if not contacts:
            return "Контакт не найден."
        elif len(contacts) == 1:
            contact = contacts[0]
            if contact.get("emails"):
                email_addr = contact["emails"][0]
                messages = gmail_agent.list_messages_from_address(email_addr, max_results=10)
                if messages:
                    lines = []
                    for msg in messages:
                        subject = msg.get("subject", "(без темы)")
                        raw_date = msg.get("date", "")
                        formatted_date = format_date(raw_date)
                        snippet = msg.get("snippet", "")
                        lines.append(f"Тема: {subject}\nДата: {formatted_date}\nСодержимое: {snippet}")
                    return {"text": "\n\n".join(lines), "attachments": [], "links": []}
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

    elif intent == "clear_mail":
        target = parameters.get("target", "").lower()
        results = []
        if "spam" in target:
            results.append(gmail_agent.empty_spam())
        if "trash" in target:
            results.append(gmail_agent.empty_trash())
        if "promotions" in target:
            results.append(gmail_agent.empty_promotions())
        if results:
            return "\n".join(results)
        else:
            return ("Не указано, какую папку очищать. "
                    "Укажите 'spam', 'trash', 'promotions' или их комбинацию.")

    elif intent == "clear_promotions":
        return gmail_agent.empty_promotions()

    elif intent == "list_starred":
        messages = gmail_agent.list_starred_messages_with_attachments(max_results=10)
        if not messages:
            return {"text": "Сообщения со звёздочкой не найдены.", "attachments": [], "links": []}
        all_lines = []
        all_attachments = []
        for msg in messages:
            subject = msg.get("subject", "(без темы)")
            raw_date = msg.get("date", "")
            formatted_date = format_date(raw_date)
            snippet = msg.get("snippet", "")
            line = f"Тема: {subject}\nДата: {formatted_date}\nСодержимое: {snippet}"
            all_lines.append(line)
            for attach in msg.get("attachments", []):
                filename = attach.get("filename")
                attachment_id = attach.get("attachmentId")
                # Используем messageId из объекта attach
                all_attachments.append((attach.get("messageId"), attachment_id, filename))
        return {"text": "\n\n".join(all_lines), "attachments": all_attachments, "links": []}

    elif intent == "list_unread":

        messages = gmail_agent.list_unread_messages_with_attachments(max_results=10)
        if not messages:
            return {"text": "Непрочитанные сообщения не найдены.", "attachments": [], "links": []}
        all_lines = []
        all_attachments = []
        for msg in messages:
            subject = msg.get("subject", "(без темы)")
            raw_date = msg.get("date", "")
            formatted_date = format_date(raw_date)
            snippet = msg.get("snippet", "")
            line = f"Тема: {subject}\nДата: {formatted_date}\nСодержимое: {snippet}"
            all_lines.append(line)
            for attach in msg.get("attachments", []):
                filename = attach.get("filename")
                attachment_id = attach.get("attachmentId")
                # Используем messageId из объекта attach
                all_attachments.append((attach.get("messageId"), attachment_id, filename))
        return {"text": "\n\n".join(all_lines), "attachments": all_attachments, "links": []}

    else:
        return "Неподдерживаемый intent для почты."
