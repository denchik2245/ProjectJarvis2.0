import json
import logging
import os
import re
import uuid

from telegram import ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

from llm.normalize_russian_text import normalize_russian_text
from stt.whisper_stt import WhisperSTT
from llm.local_llm import LocalLLM
from orchestrator import handle_intent  # Главный диспетчер, импортированный из orchestrator.py
from config import TELEGRAM_BOT_TOKEN, AUTH_SERVER_BASE_URL
from google_auth_manager import get_user_google_credentials
from agents.gmail_agent import GmailAgent

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
    text_lower = command_text.strip().lower()
    if text_lower == "помощь":
        help_handler(update, context)
        return
    if text_lower == "авторизация":
        auth_handler(update, context)
        return

    llm = LocalLLM()
    parse_result = llm.analyze_request(command_text)
    intent = parse_result.get("intent", "unknown")
    parameters = parse_result.get("parameters", {})

    telegram_user_id = update.message.from_user.id
    result = handle_intent(intent, parameters, telegram_user_id=telegram_user_id)

    # Если результат – словарь с ключами text, attachments, links
    if isinstance(result, dict):
        text = result.get("text", "")
        attachments = result.get("attachments", [])
        links = result.get("links", [])
        if text:
            update.message.reply_text(text)

        if attachments:
            # Если intent относится к Gmail (например, list_starred, list_unread),
            # используем GmailAgent для скачивания вложений
            creds = get_user_google_credentials(str(telegram_user_id))
            if creds:
                try:
                    gmail_agent = GmailAgent(credentials_info=creds)
                except Exception as e:
                    logging.error(f"Ошибка создания GmailAgent: {e}")
                    gmail_agent = None
            else:
                gmail_agent = None

            for message_id, attachment_id, file_name in attachments:
                # Генерируем «безопасное» имя файла
                sanitized_name = re.sub(r'[^\w\s\.-]', '_', file_name)
                unique_id = uuid.uuid4().hex
                # Это базовое имя, под которым хотим сохранить файл
                # (можно без префикса "temp_", если не нужно)
                local_filename = f"temp_{unique_id}_{sanitized_name}"

                # Пытаемся скачать вложение
                try:
                    # Метод возвращает полный путь к сохранённому файлу
                    downloaded_path = gmail_agent.download_attachment(
                        message_id=message_id,
                        attachment_id=attachment_id,
                        filename=local_filename,
                        save_dir="."  # Сохраняем в текущую директорию
                    )
                    # Если вернулся пустой путь или файла нет – выводим ошибку
                    if not downloaded_path or not os.path.exists(downloaded_path):
                        logging.error(f"Файл так и не создался: {downloaded_path or local_filename}")
                        continue

                except Exception as e:
                    logging.error(f"Ошибка скачивания файла {file_name}: {e}")
                    continue

                # Пытаемся отправить файл в чат
                try:
                    with open(downloaded_path, "rb") as f:
                        context.bot.send_document(
                            chat_id=update.message.chat_id,
                            document=f,
                            filename=file_name  # Чтобы пользователь видел оригинальное имя в Telegram
                        )
                except Exception as e:
                    logging.error(f"Ошибка отправки файла {file_name}: {e}")
                finally:
                    # Удаляем временный файл
                    if downloaded_path and os.path.exists(downloaded_path):
                        os.remove(downloaded_path)

        if links:
            text_links = "\n".join(links)
            update.message.reply_text(text_links)

        if not text and not attachments and not links:
            update.message.reply_text("Нет данных для отображения.")
    else:
        response = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2)
        update.message.reply_text(response)

def voice_message_handler(update, context):
    file_id = update.message.voice.file_id
    new_file = context.bot.get_file(file_id)
    voice_file_path = "temp_voice.ogg"
    new_file.download(voice_file_path)
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
    dp.add_handler(MessageHandler(Filters.regex(r"^(Помощь|Авторизация)$"),
                                  lambda u, c: auth_handler(u, c) if u.message.text == "Авторизация" else help_handler(u, c)))
    dp.add_handler(MessageHandler(Filters.voice, voice_message_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))
    updater.start_polling()
    logging.info("Бот запущен. Ожидаю сообщения...")
    updater.idle()

if __name__ == "__main__":
    run_bot()
