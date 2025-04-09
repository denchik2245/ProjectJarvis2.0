import json
import logging
import os
import re
import uuid
import datetime
from telegram import ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from llm.local_llm import LocalLLM
from orchestrator import handle_intent  # Основной диспетчер для email и календаря
from config import TELEGRAM_BOT_TOKEN, AUTH_SERVER_BASE_URL
from google_auth_manager import get_user_google_credentials
from agents.gmail_agent import GmailAgent
from agents.calendar_agent import CalendarAgent

logging.basicConfig(level=logging.INFO)

START_TEXT = (
    "Введите текст или голосовое сообщение. Для помощи нажмите кнопку 'Помощь'.\n"
    "Чтобы привязать учётную запись Google, нажмите кнопку 'Авторизация'."
)

HELP_TEXT = (
    "Доступные команды:\n\n"
    "=== Email ===\n"
    "1) Отправь Антону из ЧелГУ письмо, скажи, что всё будет сделано завтра вечером\n"
    "2) Отправь на адрес anton@csu.ru письмо, скажи, что всё будет сделано сегодня вечером\n"
    "3) Отправь 28 числа письмо Антону. Привет! С днем рождения!\n"
    "4) Покажи последние сообщения от Антона\n"
    "5) Очисти спам\n"
    "6) Очисти спам и корзину\n"
    "7) Покажи непрочитанные сообщения\n"
    "8) Покажи помеченные сообщения\n\n"
    "=== Google Calendar ===\n"
    "1) Добавь в календарь тренировку на 5 апреля в 18:00 и напомни за 30 минут\n"
    "2) Создай мне встречу с Иваном на 3 часа до начала\n"
    "3) Удали мне встречу с Иваном на 3 часа до начала\n"
    "4) Создай урок английского каждый понедельник в 19:00\n"
    "5) Покажи события на пятницу\n\n"
    "=== Google Drive ===\n"
    "1) Сохрани мне фото\n"
    "2) Покажи файлы из папки домашка\n"
    "3) Покажи всё, что лежит в папке домашка\n\n"
    "=== Google Contacts ===\n"
    "1) Дай мне номер Антона из ЧелГУ\n"
    "2) Дай мне номер Антохи\n"
    "3) Когда день рождения у Антохи?\n"
    "4) Добавь контакт Глеб из ЧелГУ +79126973674\n"
    "5) Добавь контакт Глеб из ЧелГУ, день рождения 15.05.1990, номер +79126973674\n"
    "6) Дай мне почту и номер телефона Антохи\n\n"
    "=== Яндекс Погода ===\n"
    "1) Какая погода сейчас в Москве?\n"
    "2) Какая погода в Сочи на следующей неделе?\n\n"
    "Отправьте /help или нажмите кнопку 'Помощь' для повторного вывода справки."
)

# Глобальное «хранилище» незавершённых запросов на отправку писем,
# когда нужно уточнить у пользователя, какой именно контакт он имел в виду.
pending_email_requests = {}
pending_meeting_requests = {}

def start_handler(update, context):
    reply_keyboard = [[KeyboardButton("Помощь"), KeyboardButton("Авторизация")]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    update.message.reply_text(START_TEXT, reply_markup=markup)


def help_handler(update, context):
    update.message.reply_text(HELP_TEXT)


def auth_handler(update, context):
    user_id = update.message.from_user.id
    auth_link = f"{AUTH_SERVER_BASE_URL}/authorize?user_id={user_id}"
    update.message.reply_text(
        "Для привязки учётной записи Google скопируйте и откройте эту ссылку в браузере:\n" + auth_link
    )


def process_command(update, context, command_text):
    # Приводим идентификатор пользователя к строке для единообразия
    user_key = str(update.message.from_user.id)

    # 1) Проверяем наличие незавершённого запроса по отправке письма
    if user_key in pending_email_requests:
        logging.info(
            f"Найдены pending_email_requests для пользователя {user_key}: {pending_email_requests[user_key]}")
        user_input = command_text.strip()
        try:
            selected_index = int(user_input)
        except ValueError:
            selected_index = None

        if selected_index is not None:
            data = pending_email_requests[user_key]
            contacts = data["contacts"]
            if 1 <= selected_index <= len(contacts):
                chosen_contact = contacts[selected_index - 1]
                if not chosen_contact.get("emails"):
                    update.message.reply_text(f"У контакта {chosen_contact['name']} нет электронной почты.")
                    del pending_email_requests[user_key]
                    return
                email_addr = chosen_contact["emails"][0]
                creds = get_user_google_credentials(user_key)
                if not creds:
                    update.message.reply_text("Для отправки письма необходимо авторизоваться через Google.")
                    del pending_email_requests[user_key]
                    return
                gmail_agent = GmailAgent(credentials_info=creds)
                if data.get("scheduled_day"):
                    gmail_agent.schedule_email(
                        email_addr,
                        data["subject"],
                        data["message_content"],
                        data["scheduled_day"]
                    )
                    update.message.reply_text(f"Письмо запланировано для отправки на электронную почту: {email_addr}")
                else:
                    gmail_agent.send_email(
                        email_addr,
                        data["subject"],
                        data["message_content"]
                    )
                    update.message.reply_text(f"Письмо отправлено на электронную почту: {email_addr}")
                del pending_email_requests[user_key]
                return
            else:
                update.message.reply_text("Некорректный номер контакта. Попробуйте ещё раз.")
                return

    # 2) Проверяем наличие незавершённого запроса для создания встречи
    if user_key in pending_meeting_requests:
        user_input = command_text.strip()
        try:
            selected_index = int(user_input)
        except ValueError:
            selected_index = None
        if selected_index is not None:
            data = pending_meeting_requests[user_key]
            contacts = data["contacts"]
            if 1 <= selected_index <= len(contacts):
                chosen_contact = contacts[selected_index - 1]
                if not chosen_contact.get("emails"):
                    update.message.reply_text(f"У контакта {chosen_contact['name']} нет электронной почты.")
                    del pending_meeting_requests[user_key]
                    return
                guest_email = chosen_contact["emails"][0]
                # Восстанавливаем дату встречи из ISO-строки
                meeting_datetime = datetime.datetime.fromisoformat(data["meeting_datetime"])
                creds = get_user_google_credentials(user_key)
                if not creds:
                    update.message.reply_text("Для создания встречи необходимо авторизоваться через Google.")
                    del pending_meeting_requests[user_key]
                    return
                calendar_agent = CalendarAgent(credentials_info=creds)
                title = f"Встреча с {chosen_contact.get('name')}"
                event = calendar_agent.create_event(title, meeting_datetime, attendees=[guest_email])
                link = event.get('htmlLink', 'ссылка не доступна')
                update.message.reply_text(f"Встреча создана: {link}")
                del pending_meeting_requests[user_key]
                return
            else:
                update.message.reply_text("Некорректный номер контакта. Попробуйте ещё раз.")
                return

    # 3) Если нет ожидающих выборов, обрабатываем команду через LLM
    llm = LocalLLM()
    parse_result = llm.analyze_request(command_text)
    logging.info(f"LLM parse_result: {parse_result}")
    intent = parse_result.get("intent", "unknown")
    parameters = parse_result.get("parameters", {})

    result = handle_intent(intent, parameters, telegram_user_id=user_key)

    if isinstance(result, dict):
        # Обработка случаев multiple_contacts / multiple_contacts_meeting
        if result.get("action") == "multiple_contacts":
            pending_email_requests[user_key] = {
                "contacts": result["contacts"],
                "message_content": result["message_content"],
                "subject": result["subject"],
                "scheduled_day": result["scheduled_day"]
            }
            update.message.reply_text(result["text"])
            return
        if result.get("action") == "multiple_contacts_meeting":
            pending_meeting_requests[user_key] = {
                "contacts": result["contacts"],
                "meeting_datetime": result["meeting_datetime"],
                "contact_name": result["contact_name"]
            }
            update.message.reply_text(result["text"])
            return

        # Остальная обработка (например, для email-вложений)
        text = result.get("text", "")
        attachments = result.get("attachments", [])
        links = result.get("links", [])

        if text:
            update.message.reply_text(text)

        # === Разделяем логику обработки attachments ===
        if attachments:
            # Если это Drive-интент (show_photos / show_files), возвращаются кортежи (file_id, file_name)
            if intent in ["show_photos", "show_files"]:
                from agents.drive_agent import DriveAgent
                creds = get_user_google_credentials(user_key)
                drive_agent = DriveAgent(credentials_info=creds)
                for file_id, file_name in attachments:
                    try:
                        sanitized_name = re.sub(r'[^\w\s\.-]', '_', file_name)
                        unique_id = uuid.uuid4().hex
                        local_filename = f"temp_{unique_id}_{sanitized_name}"
                        drive_agent.download_file(file_id, local_filename)
                    except Exception as e:
                        logging.error(f"Ошибка скачивания файла {file_name}: {e}")
                        continue

                    try:
                        ext = os.path.splitext(file_name)[1].lower()
                        with open(local_filename, "rb") as f:
                            if ext in [".jpg", ".jpeg", ".png"]:
                                context.bot.send_photo(
                                    chat_id=update.message.chat_id,
                                    photo=InputFile(f, filename=file_name)
                                )
                            else:
                                context.bot.send_document(
                                    chat_id=update.message.chat_id,
                                    document=InputFile(f, filename=file_name)
                                )
                    except Exception as e:
                        logging.error(f"Ошибка отправки файла {file_name}: {e}")
                    finally:
                        if os.path.exists(local_filename):
                            os.remove(local_filename)
            # Если это Gmail-интент (list_starred, list_unread, etc.), у нас (message_id, attachment_id, file_name)
            elif intent in ["list_starred", "list_unread"]:
                creds = get_user_google_credentials(user_key)
                if creds:
                    try:
                        gmail_agent = GmailAgent(credentials_info=creds)
                    except Exception as e:
                        logging.error(f"Ошибка создания GmailAgent: {e}")
                        gmail_agent = None
                else:
                    gmail_agent = None

                if gmail_agent:
                    for message_id, attachment_id, file_name in attachments:
                        try:
                            sanitized_name = re.sub(r'[^\w\s\.-]', '_', file_name)
                            unique_id = uuid.uuid4().hex
                            local_filename = f"temp_{unique_id}_{sanitized_name}"
                            downloaded_path = gmail_agent.download_attachment(
                                message_id=message_id,
                                attachment_id=attachment_id,
                                filename=local_filename,
                                save_dir="."
                            )
                            if not downloaded_path or not os.path.exists(downloaded_path):
                                logging.error(f"Файл так и не создался: {downloaded_path or local_filename}")
                                continue
                        except Exception as e:
                            logging.error(f"Ошибка скачивания файла {file_name}: {e}")
                            continue

                        try:
                            with open(downloaded_path, "rb") as f:
                                context.bot.send_document(
                                    chat_id=update.message.chat_id,
                                    document=InputFile(f, filename=file_name)
                                )
                        except Exception as e:
                            logging.error(f"Ошибка отправки файла {file_name}: {e}")
                        finally:
                            if downloaded_path and os.path.exists(downloaded_path):
                                os.remove(downloaded_path)
            else:
                logging.warning(f"Пришли attachments от intent={intent}, но логика не определена.")

        if links:
            text_links = "\n".join(links)
            update.message.reply_text(text_links)

        if not text and not attachments and not links:
            update.message.reply_text("Нет данных для отображения.")

    else:
        response = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2)
        update.message.reply_text(response)

def voice_message_handler(update, context):
    # Пример обработки голосовых сообщений
    file_id = update.message.voice.file_id
    new_file = context.bot.get_file(file_id)
    voice_file_path = "temp_voice.ogg"
    new_file.download(voice_file_path)
    from stt.whisper_stt import WhisperSTT
    from llm.normalize_russian_text import normalize_russian_text

    stt = WhisperSTT(model_name="large")
    recognized_text = stt.transcribe_audio(voice_file_path)
    normalized_text = normalize_russian_text(recognized_text)
    os.remove(voice_file_path)

    update.message.reply_text(f"Распознанный текст: {recognized_text}")
    process_command(update, context, normalized_text)


def text_message_handler(update, context):
    user_text = update.message.text
    process_command(update, context, user_text)


def run_bot():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start_handler))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(
        MessageHandler(
            Filters.regex(r"^(Помощь|Авторизация)$"),
            lambda u, c: auth_handler(u, c) if u.message.text == "Авторизация" else help_handler(u, c)
        )
    )
    dp.add_handler(MessageHandler(Filters.voice, voice_message_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))

    updater.start_polling()
    logging.info("Бот запущен. Ожидаю сообщения...")
    updater.idle()


if __name__ == "__main__":
    run_bot()
