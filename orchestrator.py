import datetime
import dateparser
from agents.YandexWeather_agent import YandexWeatherAgent
from agents.calendar_agent import CalendarAgent
from agents.contacts_agent import ContactsAgent
from agents.docs_agent import DocsAgent
from agents.format_date import format_date
from agents.gmail_agent import GmailAgent
from agents.drive_agent import DriveAgent
from google_auth_manager import get_user_google_credentials


def parse_datetime(datetime_str: str) -> datetime.datetime:
    """
    Преобразует строку вида "завтра в 15:00" или "15:00 01.04.2025" в объект datetime.
    Используем dateparser для гибкого парсинга.
    """
    dt = dateparser.parse(datetime_str, languages=['ru'])
    return dt


def safe_init(agent_class, creds):
    """
    Пытается создать экземпляр агента, передавая credentials_info.
    Если агент не поддерживает этот параметр, создаёт его без него.
    """
    try:
        return agent_class(credentials_info=creds)
    except TypeError:
        return agent_class()


class Orchestrator:
    def __init__(self):
        # Агент для погоды не требует Google-кредитов, поэтому создаем его напрямую
        self.weather_agent = YandexWeatherAgent()

    def handle_intent(self, intent: str, parameters: dict, telegram_user_id=None):
        print("Обработка intent:", intent, "с параметрами:", parameters)

        # Для intent, не требующих Google-авторизации
        if intent in ["current_weather", "current_temperature", "week_forecast"]:
            if intent == "current_weather":
                return self._handle_current_weather(parameters)
            elif intent == "current_temperature":
                return self._handle_current_temperature(parameters)
            elif intent == "week_forecast":
                return self._handle_week_forecast(parameters)

        if telegram_user_id is None:
            return "Не передан Telegram ID для авторизации."

        # Получаем учётные данные пользователя из базы данных
        creds = get_user_google_credentials(str(telegram_user_id))
        if not creds:
            return "Для использования этой функции необходимо авторизоваться через Google."

        # Создаем агентов, используя safe_init для тех, кто поддерживает injection credentials
        contacts_agent = safe_init(ContactsAgent, creds)
        docs_agent = safe_init(DocsAgent, creds)
        gmail_agent = safe_init(GmailAgent, creds)
        drive_agent = safe_init(DriveAgent, creds)
        calendar_agent = safe_init(CalendarAgent, creds)

        if intent == "search_contact":
            return self._handle_search_contact(parameters, contacts_agent)
        elif intent == "add_contact":
            return self._handle_add_contact(parameters, contacts_agent)
        elif intent == "search_document":
            return self._handle_search_document(parameters, docs_agent)
        elif intent == "send_email":
            return self._handle_send_email(parameters, gmail_agent, contacts_agent)
        elif intent == "show_messages":
            return self._handle_show_messages(parameters, gmail_agent, contacts_agent)
        elif intent == "clear_mail":
            return self._handle_clear_mail(parameters, gmail_agent)
        elif intent == "clear_promotions":
            return self._handle_clear_promotions(parameters, gmail_agent)
        elif intent == "list_starred":
            return self._handle_list_starred(parameters, gmail_agent)
        elif intent == "list_unread":
            return self._handle_list_unread(parameters, gmail_agent)
        elif intent == "save_photo":
            return self._handle_save_photo(parameters, drive_agent)
        elif intent == "show_photos":
            return self._handle_show_photos(parameters, drive_agent)
        elif intent == "show_files":
            return self._handle_show_files(parameters, drive_agent)
        elif intent == "create_event":
            return self._handle_create_event(parameters, calendar_agent)
        elif intent == "list_events_date":
            return self._handle_list_events_date(parameters, calendar_agent)
        elif intent == "list_events_period":
            return self._handle_list_events_period(parameters, calendar_agent)
        elif intent == "create_meeting":
            return self._handle_create_meeting(parameters, calendar_agent, contacts_agent)
        elif intent == "cancel_meeting":
            return self._handle_cancel_meeting(parameters, calendar_agent, contacts_agent)
        else:
            return "Извините, я не понял вашу команду или это пока не реализовано."

    # -------------------- Контакты --------------------
    def _handle_search_contact(self, params: dict, contacts_agent: ContactsAgent) -> str:
        name = params.get("contact_name")
        company = params.get("company")
        if "requested_field" in params:
            requested = params.get("requested_field")
            if isinstance(requested, list):
                requested_fields = [x.lower() for x in requested]
            else:
                requested_fields = [str(requested).lower()]
        else:
            requested_fields = ["phone", "email", "birthday"]

        contacts = contacts_agent.search_contacts(name=name, company=company)
        if not contacts:
            return "Контакты не найдены."

        def format_birthday(bday_str):
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
                    formatted_bdays = [format_birthday(b) for b in c["birthdays"]]
                    lines.append(f"День рождения: {', '.join(formatted_bdays)}")
                else:
                    lines.append("День рождения: Не указан")
            output_lines.append("\n".join(lines))
        return "\n\n".join(output_lines)

    def _handle_add_contact(self, params: dict, contacts_agent: ContactsAgent) -> str:
        contact_name = params.get("contact_name")
        phone = params.get("phone")
        company = params.get("company")
        birthday = params.get("birthday")
        if not contact_name or not phone:
            return "Для добавления контакта необходимы имя и телефон."
        result = contacts_agent.add_contact(contact_name, phone, company, birthday)
        return f"Контакт добавлен: {result.get('resourceName', 'неизвестно')}"

    # -------------------- Документы --------------------
    def _handle_search_document(self, params: dict, docs_agent: DocsAgent) -> str:
        keywords = params.get("keywords", [])
        docs = docs_agent.search_documents(keywords)
        if docs:
            lines = []
            for doc in docs:
                line = f"{doc.get('name')} (ссылка: {doc.get('webViewLink')})"
                lines.append(line)
            return "\n".join(lines)
        else:
            return "Ничего не найдено по заданным ключевым словам."

    # -------------------- Почта --------------------
    def _handle_send_email(self, params: dict, gmail_agent: GmailAgent, contacts_agent: ContactsAgent) -> str:
        to_address = params.get("to_address")
        message_content = params.get("message_content", "")
        scheduled_day = params.get("scheduled_day")
        subject = params.get("subject", "Письмо от вашего ассистента")
        if to_address:
            if scheduled_day:
                gmail_agent.schedule_email(to_address, subject, message_content, scheduled_day)
                return f"Письмо запланировано для отправки на электронную почту: {to_address}"
            else:
                gmail_agent.send_email(to_address, subject, message_content)
                return f"Письмо отправлено на электронную почту: {to_address}"
        else:
            name = params.get("contact_name")
            company = params.get("company")
            contacts = contacts_agent.search_contacts(name=name, company=company)
            if not contacts:
                return "Контакт не найден."
            elif len(contacts) == 1:
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

    def _handle_show_messages(self, params: dict, gmail_agent: GmailAgent, contacts_agent: ContactsAgent) -> str:
        name = params.get("contact_name")
        company = params.get("company")
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

    def _handle_clear_mail(self, params: dict, gmail_agent: GmailAgent) -> str:
        target = params.get("target", "").lower()
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
            return (
                "Не указано, какую папку очищать. "
                "Укажите 'spam', 'trash', 'promotions' или их комбинацию."
            )

    def _handle_clear_promotions(self, params: dict, gmail_agent: GmailAgent) -> str:
        return gmail_agent.empty_promotions()

    def _handle_list_starred(self, params: dict, gmail_agent: GmailAgent) -> dict:
        messages = gmail_agent.list_starred_messages_with_attachments(max_results=10)
        if not messages:
            return {"text": "Сообщения со звёздочкой не найдены.", "attachments": [], "links": []}
        all_lines = []
        all_attachments = []
        for msg in messages:
            subject = msg.get("subject", "(без темы)")
            raw_date = msg.get("date", "")
            snippet = msg.get("snippet", "")
            formatted_date = format_date(raw_date)
            line = f"Тема: {subject}\nДата: {formatted_date}\nСодержимое: {snippet}"
            all_lines.append(line)
            for attach in msg.get("attachments", []):
                filename = attach["filename"]
                attachment_id = attach["attachmentId"]
                message_id = attach["messageId"]
                saved_path = gmail_agent.download_attachment(
                    message_id, attachment_id, filename, save_dir="./downloads"
                )
                if saved_path:
                    all_attachments.append((saved_path, filename))
        text_result = "\n\n".join(all_lines)
        return {"text": text_result, "attachments": all_attachments, "links": []}

    def _handle_list_unread(self, params: dict, gmail_agent: GmailAgent) -> dict:
        messages = gmail_agent.list_unread_messages_with_attachments(max_results=10)
        if not messages:
            return {"text": "Непрочитанные сообщения не найдены.", "attachments": [], "links": []}
        all_lines = []
        all_attachments = []
        for msg in messages:
            subject = msg.get("subject", "(без темы)")
            raw_date = msg.get("date", "")
            snippet = msg.get("snippet", "")
            formatted_date = format_date(raw_date)
            line = f"Тема: {subject}\nДата: {formatted_date}\nСодержимое: {snippet}"
            all_lines.append(line)
            for attach in msg.get("attachments", []):
                filename = attach["filename"]
                attachment_id = attach["attachmentId"]
                message_id = attach["messageId"]
                saved_path = gmail_agent.download_attachment(
                    message_id, attachment_id, filename, save_dir="./downloads"
                )
                if saved_path:
                    all_attachments.append((saved_path, filename))
        text_result = "\n\n".join(all_lines)
        return {"text": text_result, "attachments": all_attachments, "links": []}

    # -------------------- Диск --------------------
    def _handle_save_photo(self, params: dict, drive_agent: DriveAgent) -> str:
        file_path = params.get("file_path")
        file_name = params.get("file_name")
        folder_name = params.get("folder_name", "Photos")
        if not file_path or not file_name:
            return "Параметры файла не указаны."
        result = drive_agent.save_photo(file_path, file_name, folder_name)
        return f"Фото сохранено: {result.get('name')} (ID: {result.get('id')})"

    def _handle_show_photos(self, params: dict, drive_agent: DriveAgent) -> dict:
        folder_keyword = params.get("folder_keyword")
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

    def _handle_show_files(self, params: dict, drive_agent: DriveAgent) -> dict:
        folder_keyword = params.get("folder_keyword")
        include_photos = params.get("include_photos", False)
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

    # -------------------- Календарь --------------------
    def _handle_create_event(self, params: dict, calendar_agent: CalendarAgent) -> str:
        title = params.get("title", "Событие")
        date_str = params.get("date")
        time_str = params.get("time")
        reminder = params.get("reminder")
        if not date_str or not time_str:
            return "Не указана дата или время события."
        try:
            day, month, year = date_str.split(".")
            hour, minute = time_str.split(":")
            event_dt = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
        except Exception:
            return "Неверный формат даты или времени."
        try:
            reminder_minutes = int(reminder) if reminder is not None else None
        except:
            reminder_minutes = None
        created_event = calendar_agent.create_event(title, event_dt, reminder_minutes)
        return f"Событие '{title}' создано на {event_dt.strftime('%d.%m.%Y %H:%M')}" + (
            f" с напоминанием за {reminder_minutes} минут." if reminder_minutes else "."
        )

    def _handle_list_events_date(self, params: dict, calendar_agent: CalendarAgent) -> dict:
        date_query = params.get("date", "завтра").lower()
        if date_query == "завтра":
            event_date = datetime.date.today() + datetime.timedelta(days=1)
        elif date_query == "сегодня":
            event_date = datetime.date.today()
        else:
            try:
                day, month, year = date_query.split(".")
                event_date = datetime.date(int(year), int(month), int(day))
            except:
                event_date = datetime.date.today() + datetime.timedelta(days=1)
        events = calendar_agent.list_events_for_date(event_date)
        if not events:
            text = f"На {event_date.strftime('%d.%m.%Y')} событий не найдено."
        else:
            lines = []
            for idx, event in enumerate(events, start=1):
                summary = event.get("summary", "Без названия")
                start_time_str = event.get("start", {}).get("dateTime")
                end_time_str = event.get("end", {}).get("dateTime")
                if start_time_str and end_time_str:
                    try:
                        start_dt = datetime.datetime.fromisoformat(start_time_str)
                        end_dt = datetime.datetime.fromisoformat(end_time_str)
                        start_formatted = start_dt.strftime("%H:%M")
                        end_formatted = end_dt.strftime("%H:%M")
                    except Exception:
                        start_formatted = start_time_str
                        end_formatted = end_time_str
                    time_str = f"({start_formatted} - {end_formatted})"
                else:
                    time_str = ""
                line = f"{idx}. {summary} {time_str}".strip()
                if event.get("location"):
                    line += f", Место - {event.get('location')}"
                if event.get("description"):
                    line += f", Описание - {event.get('description')}"
                lines.append(line)
            text = f"События на {event_date.strftime('%d.%m.%Y')}\n\n" + "\n".join(lines)
        return {"text": text, "attachments": [], "links": []}

    def _handle_list_events_period(self, params: dict, calendar_agent: CalendarAgent) -> dict:
        today = datetime.date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + datetime.timedelta(days=days_until_monday)
        next_sunday = next_monday + datetime.timedelta(days=6)
        events = calendar_agent.list_events_for_period(next_monday, next_sunday)
        if not events:
            text = "События на следующую неделю отсутствуют."
        else:
            grouped_events = {}
            for event in events:
                start_time_str = event.get("start", {}).get("dateTime")
                if not start_time_str:
                    continue
                try:
                    dt = datetime.datetime.fromisoformat(start_time_str)
                except Exception:
                    continue
                event_date = dt.date()
                if event_date not in grouped_events:
                    grouped_events[event_date] = []
                grouped_events[event_date].append((dt, event))
            sorted_dates = sorted(grouped_events.keys())
            week_days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            output_lines = []
            for day in sorted_dates:
                weekday = week_days[day.weekday()]
                header = f"{weekday}, {day.strftime('%d.%m.%Y')}"
                output_lines.append(header)
                events_for_day = sorted(grouped_events[day], key=lambda x: x[0])
                for idx, (start_dt, event) in enumerate(events_for_day, start=1):
                    summary = event.get("summary", "Без названия")
                    end_time_str = event.get("end", {}).get("dateTime")
                    if start_dt and end_time_str:
                        try:
                            end_dt = datetime.datetime.fromisoformat(end_time_str)
                            time_str = f"({start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')})"
                        except Exception:
                            time_str = ""
                    else:
                        time_str = ""
                    line = f"  {idx}. {summary} {time_str}".strip()
                    if event.get("location"):
                        line += f", Место - {event.get('location')}"
                    if event.get("description"):
                        line += f", Описание - {event.get('description')}"
                    output_lines.append(line)
                output_lines.append("")
            text = "События на следующую неделю:\n\n" + "\n".join(output_lines)
        return {"text": text, "attachments": [], "links": []}

    def _handle_create_meeting(self, params: dict, calendar_agent: CalendarAgent, contacts_agent: ContactsAgent) -> str:
        contact_name = params.get("contact_name")
        datetime_str = params.get("datetime")
        if not contact_name or not datetime_str:
            return "Для создания встречи укажите имя контакта и дату/время встречи."
        meeting_datetime = parse_datetime(datetime_str)
        if meeting_datetime is None:
            return "Не удалось распознать дату и время встречи."
        contacts = contacts_agent.search_contacts(name=contact_name)
        if not contacts:
            return f"Контакт с именем '{contact_name}' не найден."
        contacts_with_email = [contact for contact in contacts if contact.get("emails")]
        if not contacts_with_email:
            return f"Найден(ы) контакт(ы), но ни у одного не указана почта для приглашения."
        selected_index = params.get("selected_contact_index")
        if selected_index is not None:
            try:
                index = int(selected_index) - 1
                if index < 0 or index >= len(contacts_with_email):
                    return "Указан неверный номер контакта."
                chosen_contact = contacts_with_email[index]
            except Exception:
                return "Неверный формат номера контакта."
        else:
            if len(contacts_with_email) > 1:
                response = "Найдено несколько контактов с указанным именем:\n"
                for i, contact in enumerate(contacts_with_email, start=1):
                    email = contact.get("emails")[0] if contact.get("emails") else "без почты"
                    response += f"{i}. {contact.get('name')} ({email})\n"
                response += "Укажите номер нужного контакта, добавив параметр 'selected_contact_index'."
                return response
            else:
                chosen_contact = contacts_with_email[0]
        guest_email = chosen_contact.get("emails")[0]
        title = f"Встреча с {chosen_contact.get('name')}"
        event = calendar_agent.create_event(title, meeting_datetime, attendees=[guest_email])
        link = event.get('htmlLink', 'ссылка не доступна')
        return f"Встреча создана: {link}"

    def _handle_cancel_meeting(self, params: dict, calendar_agent: CalendarAgent, contacts_agent: ContactsAgent) -> str:
        contact_name = params.get("contact_name")
        if not contact_name:
            return "Для отмены встречи укажите имя контакта."
        contacts = contacts_agent.search_contacts(name=contact_name)
        if not contacts:
            return f"Контакт с именем '{contact_name}' не найден."
        contact_names = [contact.get("name", contact_name) for contact in contacts]
        upcoming_events = calendar_agent.list_upcoming_events()
        now = datetime.datetime.utcnow()
        matching_events = []
        for event in upcoming_events:
            summary = event.get("summary", "")
            event_start_str = event.get("start", {}).get("dateTime")
            if not event_start_str:
                continue
            try:
                event_start = datetime.datetime.fromisoformat(event_start_str)
            except Exception:
                continue
            if any(name.lower() in summary.lower() for name in contact_names) and event_start >= now:
                matching_events.append((event_start, event))
        if not matching_events:
            return f"Не найдено предстоящих встреч с '{contact_name}'."
        matching_events.sort(key=lambda x: x[0])
        nearest_event = matching_events[0][1]
        event_id = nearest_event.get("id")
        if not event_id:
            return "Ошибка: не удалось получить ID события."
        calendar_agent.delete_event(event_id)
        return f"Встреча '{nearest_event.get('summary')}' отменена."

    # -------------------- Погода --------------------
    def _handle_current_weather(self, params: dict):
        city = params.get("city")
        return self.weather_agent.get_today_weather(city)

    def _handle_current_temperature(self, params: dict):
        city = params.get("city")
        return self.weather_agent.get_current_temperature(city)

    def _handle_week_forecast(self, params: dict):
        city = params.get("city")
        return self.weather_agent.get_week_forecast(city)
