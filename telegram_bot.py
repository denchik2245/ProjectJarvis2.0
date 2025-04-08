import json
import logging
import os
from telegram import ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

from llm.normalize_russian_text import normalize_russian_text
from stt.whisper_stt import WhisperSTT
from llm.local_llm import LocalLLM
from orchestrator import Orchestrator
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)

# Текст приветствия для /start
START_TEXT = (
    "Введите текст или голосовое сообщение. Для помощи нажмите кнопку 'Помощь'."
)

# Текст справки для /help
HELP_TEXT = (
    "Доступные команды:\n\n"
    "=== Email ===\n"
    "1) Отправь Антону из ЧелГУ письмо, скажи, что все будет сделано завтра вечером\n"
    "2) Отправь на адрес anton@csu.ru письмо, скажи, что все будет сделано сегодня вечером\n"
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
    "3) Покажи все, что лежит в папке домашка\n\n"

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

    "Отправьте /help или нажмите кнопку 'Помощь' для повторного вывода этой справки."
)

def start_handler(update, context):
    # Создаем постоянную клавиатуру с кнопкой "Помощь"
    reply_keyboard = [[KeyboardButton("Помощь")]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    update.message.reply_text(START_TEXT, reply_markup=markup)

def help_handler(update, context):
    update.message.reply_text(HELP_TEXT)

def process_command(update, context, command_text):
    # Если команда "помощь", перенаправляем на help_handler
    if command_text.strip().lower() == "помощь":
        help_handler(update, context)
        return

    llm = LocalLLM()
    parse_result = llm.analyze_request(command_text)
    intent = parse_result.get("intent", "unknown")
    parameters = parse_result.get("parameters", {})

    orchestrator = Orchestrator()

    # Если ответ ожидается в виде словаря с текстом, вложениями и ссылками
    if intent in ["show_photos", "show_files", "list_starred", "list_unread", "list_events_date", "list_events_period"]:
        result_dict = orchestrator.handle_intent(intent, parameters)
        text = result_dict.get("text", "")
        attachments = result_dict.get("attachments", [])
        links = result_dict.get("links", [])

        # Отправляем текст
        if text:
            update.message.reply_text(text)

        # Отправляем вложения
        if attachments:
            for file_identifier, file_name in attachments:
                if os.path.exists(file_identifier):
                    send_path = file_identifier
                else:
                    temp_path = f"temp_{file_name}"
                    try:
                        orchestrator.drive_agent.download_file(file_identifier, temp_path)
                        send_path = temp_path
                    except Exception as e:
                        logging.error(f"Ошибка скачивания файла {file_name}: {e}")
                        continue

                ext = os.path.splitext(file_name)[1].lower()
                try:
                    with open(send_path, "rb") as f:
                        if ext in [".jpg", ".jpeg", ".png"]:
                            context.bot.send_photo(chat_id=update.message.chat_id, photo=InputFile(f))
                        else:
                            context.bot.send_document(chat_id=update.message.chat_id, document=InputFile(f))
                except Exception as e:
                    logging.error(f"Ошибка отправки файла {file_name}: {e}")
                finally:
                    if send_path.startswith("temp_") and os.path.exists(send_path):
                        os.remove(send_path)

        # Отправляем ссылки
        if links:
            text_links = "\n".join(links)
            update.message.reply_text(text_links)

        # Если ничего не найдено
        if not text and not attachments and not links:
            update.message.reply_text("Нет данных для отображения.")
    else:
        # Если ответ не требует дополнительной обработки
        response = orchestrator.handle_intent(intent, parameters)
        if isinstance(response, dict):
            response = json.dumps(response, ensure_ascii=False, indent=2)
        update.message.reply_text(response)

def voice_message_handler(update, context):
    # Получаем и скачиваем файл голосового сообщения
    file_id = update.message.voice.file_id
    new_file = context.bot.get_file(file_id)
    voice_file_path = "temp_voice.ogg"
    new_file.download(voice_file_path)

    # Распознаем голосовое сообщение через Whisper
    stt = WhisperSTT(model_name="large")
    recognized_text = stt.transcribe_audio(voice_file_path)

    # Нормализуем текст (если требуется)
    normalized_text = normalize_russian_text(recognized_text)

    # Удаляем временный файл
    os.remove(voice_file_path)

    # Можно уведомить пользователя о распознанном тексте
    update.message.reply_text(f"Распознанный текст: {recognized_text}")

    # Передаем полученный текст в общую функцию обработки команды
    process_command(update, context, normalized_text)

def text_message_handler(update, context):
    user_text = update.message.text
    process_command(update, context, user_text)

def send_photo_from_drive(bot, chat_id, drive_agent, file_id, file_name):
    # Сохраняем фото во временный файл
    temp_path = f"temp_{file_name}"
    drive_agent.download_file(file_id, temp_path)
    # Отправляем фото
    bot.send_photo(chat_id=chat_id, photo=InputFile(temp_path))
    # Удаляем временный файл
    os.remove(temp_path)

def run_bot():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_handler))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(MessageHandler(Filters.voice, voice_message_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))

    updater.start_polling()
    logging.info("Бот запущен. Ожидаю сообщения...")
    updater.idle()

if __name__ == "__main__":
    run_bot()
