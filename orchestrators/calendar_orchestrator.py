import datetime
from agents.calendar_agent import CalendarAgent
from agents.format_date import format_date
from orchestrators.common import parse_datetime
from agents.contacts_agent import ContactsAgent
from google_auth_manager import get_user_google_credentials

def handle_calendar_intent(intent, parameters, telegram_user_id):
    creds = get_user_google_credentials(str(telegram_user_id))
    if not creds:
        return "Для использования этой функции необходимо авторизоваться через Google."
    calendar_agent = CalendarAgent(credentials_info=creds)

    if intent == "create_event":
        title = parameters.get("title", "Событие")
        date_str = parameters.get("date")
        time_str = parameters.get("time")
        reminder = parameters.get("reminder")
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
        except Exception:
            reminder_minutes = None
        created_event = calendar_agent.create_event(title, event_dt, reminder_minutes)
        return f"Событие '{title}' создано на {event_dt.strftime('%d.%m.%Y %H:%M')}" + (
            f" с напоминанием за {reminder_minutes} минут." if reminder_minutes else "."
        )

    elif intent == "list_events_date":
        date_query = parameters.get("date", "завтра").lower()
        if date_query == "завтра":
            event_date = datetime.date.today() + datetime.timedelta(days=1)
        elif date_query == "сегодня":
            event_date = datetime.date.today()
        else:
            try:
                day, month, year = date_query.split(".")
                event_date = datetime.date(int(year), int(month), int(day))
            except Exception:
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

    elif intent == "list_events_period":
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

    elif intent == "create_meeting":
        # Ожидаются параметры: "contact_name" и "datetime"
        contact_name = parameters.get("contact_name")
        datetime_str = parameters.get("datetime")
        if not contact_name or not datetime_str:
            return "Для создания встречи укажите имя контакта и дату/время встречи."
        meeting_datetime = parse_datetime(datetime_str)
        if meeting_datetime is None:
            return "Не удалось распознать дату и время встречи."
        # Если meeting_datetime не имеет timezone, устанавливаем его, используя tz календаря
        if meeting_datetime.tzinfo is None:
            meeting_datetime = meeting_datetime.replace(tzinfo=calendar_agent.tz)
        # Получаем текущее время с учетом timezone
        now = datetime.datetime.now(meeting_datetime.tzinfo)
        # Если встреча назначена на время, которое уже прошло, сдвигаем её на 7 дней (на следующую неделю)
        if meeting_datetime <= now:
            meeting_datetime += datetime.timedelta(days=7)

        # Используем агента контактов с авторизацией
        contacts_agent = ContactsAgent(credentials_info=creds)
        contacts = contacts_agent.search_contacts(name=contact_name)
        if not contacts:
            return f"Контакт с именем '{contact_name}' не найден."
        contacts_with_email = [contact for contact in contacts if contact.get("emails")]
        if not contacts_with_email:
            return f"Найден(ы) контакт(ы), но ни у одного не указана почта для приглашения."
        selected_index = parameters.get("selected_contact_index")
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
                lines = []
                for i, contact in enumerate(contacts_with_email, start=1):
                    email = contact.get("emails")[0] if contact.get("emails") else "без почты"
                    lines.append(f"{i}. {contact.get('name')} ({email})")
                response = "Найдено несколько контактов с указанным именем:\n" + "\n".join(lines)
                response += "\nУкажите номер нужного контакта, добавив параметр 'selected_contact_index'."
                return {
                    "action": "multiple_contacts_meeting",
                    "text": response,
                    "contacts": contacts_with_email,
                    "meeting_datetime": meeting_datetime.isoformat(),
                    "contact_name": contact_name,
                    "intent": intent
                }
            else:
                chosen_contact = contacts_with_email[0]
        guest_email = chosen_contact.get("emails")[0]
        title = f"Встреча с {chosen_contact.get('name')}"
        event = calendar_agent.create_event(title, meeting_datetime, attendees=[guest_email])
        link = event.get('htmlLink', 'ссылка не доступна')
        return f"Встреча создана: {link}"

    elif intent == "cancel_meeting":
        contact_name = parameters.get("contact_name")
        if not contact_name:
            return "Для отмены встречи укажите имя контакта."
        contacts_agent = ContactsAgent(credentials_info=creds)
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

    else:
        return "Неподдерживаемый intent для календаря."
