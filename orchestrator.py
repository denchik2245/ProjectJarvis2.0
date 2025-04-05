from agents.YandexWeather_agent import YandexWeatherAgent
from agents.calendar_agent import CalendarAgent
from agents.contacts_agent import ContactsAgent
from agents.docs_agent import DocsAgent
from agents.format_date import format_date
from agents.gmail_agent import GmailAgent
from agents.drive_agent import DriveAgent
import datetime
import dateparser

def parse_datetime(datetime_str: str) -> datetime.datetime:
    """
    Преобразует строку вида "завтра в 15:00" или "15:00 01.04.2025" в объект datetime.
    Используем dateparser для гибкого парсинга.
    """
    dt = dateparser.parse(datetime_str, languages=['ru'])
    return dt


class Orchestrator:
    def __init__(self):
        self.contacts_agent = ContactsAgent()
        self.docs_agent = DocsAgent()
        self.gmail_agent = GmailAgent()
        self.drive_agent = DriveAgent()
        self.calendar_agent = CalendarAgent()
        self.weather_agent = YandexWeatherAgent()

    def handle_intent(self, intent: str, parameters: dict):
        print("Обработка intent:", intent, "с параметрами:", parameters)

        if intent == "search_contact":
            return self._handle_search_contact(parameters)
        elif intent == "add_contact":
            return self._handle_add_contact(parameters)


        elif intent == "search_document":
            return self._handle_search_document(parameters)

        elif intent == "send_email":
            return self._handle_send_email(parameters)
        elif intent == "show_messages":
            return self._handle_show_messages(parameters)
        elif intent == "clear_mail":
            return self._handle_clear_mail(parameters)
        elif intent == "clear_promotions":
            return self._handle_clear_promotions(parameters)
        elif intent == "list_starred":
            return self._handle_list_starred(parameters)
        elif intent == "list_unread":
            return self._handle_list_unread(parameters)

        elif intent == "save_photo":
            return self._handle_save_photo(parameters)
        elif intent == "show_photos":
            return self._handle_show_photos(parameters)
        elif intent == "show_files":
            return self._handle_show_files(parameters)

        elif intent == "create_event":
            return self._handle_create_event(parameters)
        elif intent == "list_events_date":
            return self._handle_list_events_date(parameters)
        elif intent == "list_events_period":
            return self._handle_list_events_period(parameters)
        elif intent == "create_meeting":
            return self._handle_create_meeting(parameters)
        elif intent == "cancel_meeting":
            return self._handle_cancel_meeting(parameters)

        elif intent == "current_weather":
            return self._handle_current_weather(parameters)
        elif intent == "current_temperature":
            return self._handle_current_temperature(parameters)
        elif intent == "week_forecast":
            return self._handle_week_forecast(parameters)

        else:
            return "Извините, я не понял вашу команду или это пока не реализовано."

        """
        КОНТАКТЫ
        """

    # Найти контакт
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

    # Добавить контакт
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

    """
    ДОКУМЕНТЫ
    """

    # Искать документ по ключевым словам
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

    """
    ПОЧТА
    """

    #Отправить письмо
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

    # Показать письмо от определенного человека
    def _handle_show_messages(self, params: dict) -> str:
        """
        Обрабатывает запрос "Покажи последние сообщения от <контакт>".
        Находит контакт по имени (и опционально компании), затем извлекает email и запрашивает последние сообщения.
        Выводит данные в формате:
          Тема: <тема>
          Дата: <отформатированная дата>
          Содержимое: <фрагмент>
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
            return "Найдено несколько контактов:\n" + "\n".join(lines) + "\nПожалуйста, уточните номер нужного контакта."

    # Очистить почту
    def _handle_clear_mail(self, params: dict) -> str:
        target = params.get("target", "").lower()
        results = []

        # Если в target упоминается "spam" — чистим спам
        if "spam" in target:
            results.append(self.gmail_agent.empty_spam())

        # Если в target упоминается "trash" — чистим корзину
        if "trash" in target:
            results.append(self.gmail_agent.empty_trash())

        # Если в target упоминается "promotions" — чистим промоакции
        if "promotions" in target:
            results.append(self.gmail_agent.empty_promotions())

        # Если что-то почистили — вернуть сводку, иначе — подсказку
        if results:
            return "\n".join(results)
        else:
            return (
                "Не указано, какую папку очищать. "
                "Укажите 'spam', 'trash', 'promotions' или любую их комбинацию."
            )

    # Показать помеченные сообщения
    def _handle_list_starred(self, params: dict) -> dict:
        """
        Возвращает помеченные сообщения в виде:
        {
          "text": "<строка со всеми письмами>",
          "attachments": [ (local_file_path, file_name), ... ],
          "links": []
        }
        """
        messages = self.gmail_agent.list_starred_messages_with_attachments(max_results=10)
        if not messages:
            return {
                "text": "Сообщения со звёздочкой не найдены.",
                "attachments": [],
                "links": []
            }

        all_lines = []
        all_attachments = []

        for msg in messages:
            subject = msg.get("subject", "(без темы)")
            raw_date = msg.get("date", "")
            snippet = msg.get("snippet", "")
            formatted_date = format_date(raw_date)  # Ваш хелпер для форматирования

            line = (
                f"Тема: {subject}\n"
                f"Дата: {formatted_date}\n"
                f"Содержимое: {snippet}"
            )
            all_lines.append(line)

            # Скачиваем вложения и добавляем в общий список
            for attach in msg.get("attachments", []):
                filename = attach["filename"]
                attachment_id = attach["attachmentId"]
                message_id = attach["messageId"]
                saved_path = self.gmail_agent.download_attachment(
                    message_id, attachment_id, filename, save_dir="./downloads"
                )
                if saved_path:
                    # Дополняем attachments для дальнейшей отправки
                    all_attachments.append((saved_path, filename))

        text_result = "\n\n".join(all_lines)
        return {
            "text": text_result,
            "attachments": all_attachments,
            "links": []
        }

    # Показать непрочитанные сообщения
    def _handle_list_unread(self, params: dict) -> dict:
        """
        Возвращает непрочитанные сообщения в виде словаря:
        {
          "text": "<объединённый текст>",
          "attachments": [ (local_path, file_name), ... ],
          "links": []
        }
        """
        messages = self.gmail_agent.list_unread_messages_with_attachments(max_results=10)
        if not messages:
            return {
                "text": "Непрочитанные сообщения не найдены.",
                "attachments": [],
                "links": []
            }

        all_lines = []
        all_attachments = []

        for msg in messages:
            subject = msg.get("subject", "(без темы)")
            raw_date = msg.get("date", "")
            snippet = msg.get("snippet", "")
            formatted_date = format_date(raw_date)  # ваша функция

            # Собираем текст о письме
            line = (
                f"Тема: {subject}\n"
                f"Дата: {formatted_date}\n"
                f"Содержимое: {snippet}"
            )
            all_lines.append(line)

            # Скачиваем вложения, если есть
            for attach in msg.get("attachments", []):
                filename = attach["filename"]
                attachment_id = attach["attachmentId"]
                message_id = attach["messageId"]

                saved_path = self.gmail_agent.download_attachment(
                    message_id, attachment_id, filename, save_dir="./downloads"
                )
                if saved_path:
                    # Добавляем в общий список для отправки
                    all_attachments.append((saved_path, filename))

        text_result = "\n\n".join(all_lines)
        return {
            "text": text_result,
            "attachments": all_attachments,
            "links": []
        }

    """
    ДИСК
    """

    # Сохранить фото
    def _handle_save_photo(self, params: dict) -> str:
        file_path = params.get("file_path")
        file_name = params.get("file_name")
        folder_name = params.get("folder_name", "Photos")
        if not file_path or not file_name:
            return "Параметры файла не указаны."
        result = self.drive_agent.save_photo(file_path, file_name, folder_name)
        return f"Фото сохранено: {result.get('name')} (ID: {result.get('id')})"

    # Показать фото с диска
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

    # Показать файлы с диска
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

    """
    КАЛЕНДАРЬ
    """

    def _handle_create_event(self, params: dict) -> str:
        # Ожидаются параметры: title, date (формат DD.MM.YYYY), time (формат HH:MM) и reminder (в минутах)
        title = params.get("title", "Событие")
        date_str = params.get("date")
        time_str = params.get("time")
        reminder = params.get("reminder")  # Напоминание в минутах
        if not date_str or not time_str:
            return "Не указана дата или время события."
        try:
            day, month, year = date_str.split(".")
            hour, minute = time_str.split(":")
            event_dt = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
        except Exception as e:
            return "Неверный формат даты или времени."
        try:
            reminder_minutes = int(reminder) if reminder is not None else None
        except:
            reminder_minutes = None
        created_event = self.calendar_agent.create_event(title, event_dt, reminder_minutes)
        return f"Событие '{title}' создано на {event_dt.strftime('%d.%m.%Y %H:%M')}" + (
            f" с напоминанием за {reminder_minutes} минут." if reminder_minutes else "."
        )

    def _handle_list_events_date(self, params: dict) -> dict:
        # Ожидается параметр "date" (например, "завтра", "сегодня" или дата в формате DD.MM.YYYY)
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
        events = self.calendar_agent.list_events_for_date(event_date)
        if not events:
            text = f"На {event_date.strftime('%d.%m.%Y')} событий не найдено."
        else:
            lines = []
            for idx, event in enumerate(events, start=1):
                summary = event.get("summary", "Без названия")
                # Получаем время начала и окончания события
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
                # Формируем строку для события
                line = f"{idx}. {summary} {time_str}".strip()
                # Добавляем дополнительные поля, если они есть
                if event.get("location"):
                    line += f", Место - {event.get('location')}"
                if event.get("description"):
                    line += f", Описание - {event.get('description')}"
                lines.append(line)
            text = f"События на {event_date.strftime('%d.%m.%Y')}\n\n" + "\n".join(lines)
        return {"text": text, "attachments": [], "links": []}

    def get_next_week_period(self) -> (datetime.date, datetime.date):
        today = datetime.date.today()
        # Определяем, сколько дней осталось до следующего понедельника
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # если сегодня понедельник, берем следующую неделю
        next_monday = today + datetime.timedelta(days=days_until_monday)
        next_sunday = next_monday + datetime.timedelta(days=6)
        return next_monday, next_sunday

    def _handle_list_events_period(self, params: dict) -> dict:
        # Вычисляем даты начала и конца следующей календарной недели (с понедельника по воскресенье)
        today = datetime.date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # если сегодня понедельник, берем следующую неделю
        next_monday = today + datetime.timedelta(days=days_until_monday)
        next_sunday = next_monday + datetime.timedelta(days=6)

        events = self.calendar_agent.list_events_for_period(next_monday, next_sunday)
        if not events:
            text = "События на следующую неделю отсутствуют."
        else:
            # Группируем события по датам
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

            # Сортируем даты и события внутри каждой даты
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
                output_lines.append("")  # пустая строка между днями
            text = "События на следующую неделю:\n\n" + "\n".join(output_lines)
        return {"text": text, "attachments": [], "links": []}

    def _handle_create_meeting(self, params: dict) -> str:
        # Ожидаются параметры: "contact_name", "datetime"
        # Дополнительно, если уточнение выбора контакта уже дано, может передаваться "selected_contact_index"
        contact_name = params.get("contact_name")
        datetime_str = params.get("datetime")
        if not contact_name or not datetime_str:
            return "Для создания встречи укажите имя контакта и дату/время встречи."

        meeting_datetime = parse_datetime(datetime_str)
        if meeting_datetime is None:
            return "Не удалось распознать дату и время встречи."

        # Поиск контактов по имени (с учетом нормализации и синонимов)
        contacts = self.contacts_agent.search_contacts(name=contact_name)
        if not contacts:
            return f"Контакт с именем '{contact_name}' не найден."

        # Фильтруем контакты, у которых указана почта
        contacts_with_email = [contact for contact in contacts if contact.get("emails")]
        if not contacts_with_email:
            return f"Найден(ы) контакт(ы), но ни у одного не указана почта для приглашения."

        # Если в параметрах уже передан номер выбранного контакта (индекс)
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
            # Если подходящих контактов несколько, возвращаем список для уточнения
            if len(contacts_with_email) > 1:
                response = "Найдено несколько контактов с указанным именем:\n"
                for i, contact in enumerate(contacts_with_email, start=1):
                    email = contact.get("emails")[0] if contact.get("emails") else "без почты"
                    response += f"{i}. {contact.get('name')} ({email})\n"
                response += "Укажите номер нужного контакта, добавив параметр 'selected_contact_index'."
                return response
            else:
                chosen_contact = contacts_with_email[0]

        guest_email = chosen_contact.get("emails")[0]  # Берем первую почту
        title = f"Встреча с {chosen_contact.get('name')}"
        event = self.calendar_agent.create_event(title, meeting_datetime, attendees=[guest_email])
        link = event.get('htmlLink', 'ссылка не доступна')
        return f"Встреча создана: {link}"

    def _handle_cancel_meeting(self, params: dict) -> str:
        # Обработчик отмены встречи (код остается прежним)
        contact_name = params.get("contact_name")
        if not contact_name:
            return "Для отмены встречи укажите имя контакта."

        contacts = self.contacts_agent.search_contacts(name=contact_name)
        if not contacts:
            return f"Контакт с именем '{contact_name}' не найден."
        contact_names = [contact.get("name", contact_name) for contact in contacts]

        upcoming_events = self.calendar_agent.list_upcoming_events()
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
        self.calendar_agent.delete_event(event_id)
        return f"Встреча '{nearest_event.get('summary')}' отменена."

    """
    КАЛЕНДАРЬ
    """

    def _handle_current_weather(self, params: dict):
        city = params.get("city")
        return self.weather_agent.get_today_weather(city)

    def _handle_current_temperature(self, params: dict):
        city = params.get("city")
        return self.weather_agent.get_current_temperature(city)

    def _handle_week_forecast(self, params: dict):
        city = params.get("city")
        return self.weather_agent.get_week_forecast(city)