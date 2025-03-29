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
    "Доступные команды:\n"
    "• Голосовое сообщение или текстовое сообщение с командой.\n"
    "Примеры:\n"
    "  – Дай мне номер Антохи\n"
    "  – Дай мне почту и номер телефона Антохи\n"
    "  – Когда день рождения у Антохи?\n"
    "  – Отправь письмо ...\n"
    "  – Покажи последние сообщения от Антона\n"
    "  – Очисти спам и корзину\n"
    "  – Сохрани фото\n"
    "  – Покажи фотографии из папки домашка\n"
    "  – Добавь контакт Глеб из ЧелГУ +79126973674\n"
    "Для получения этой справки нажмите кнопку 'Помощь' или отправьте /help."
)

def start_handler(update, context):
    # Создаем постоянную клавиатуру с кнопкой "Помощь"
    reply_keyboard = [[KeyboardButton("Помощь")]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    update.message.reply_text(START_TEXT, reply_markup=markup)

def help_handler(update, context):
    update.message.reply_text(HELP_TEXT)

def voice_message_handler(update, context):
    # Получаем файл голосового сообщения
    file_id = update.message.voice.file_id
    new_file = context.bot.get_file(file_id)
    voice_file_path = "temp_voice.ogg"
    new_file.download(voice_file_path)

    # Распознаем голос с помощью Whisper
    stt = WhisperSTT(model_name="base")
    recognized_text = stt.transcribe_audio(voice_file_path)

    # Нормализуем текст (если необходимо)
    normalized_text = normalize_russian_text(recognized_text)

    # Удаляем временный файл
    os.remove(voice_file_path)

    # Анализируем запрос через локальную LLM
    llm = LocalLLM()
    parse_result = llm.analyze_request(recognized_text)
    intent = parse_result.get("intent", "unknown")
    parameters = parse_result.get("parameters", {})

    # Вызываем оркестратор
    orchestrator = Orchestrator()
    response = orchestrator.handle_intent(intent, parameters)

    print("LLM RAW OUTPUT:", parse_result)
    update.message.reply_text(f"Распознанный текст: {recognized_text}\n\n{response}")

def text_message_handler(update, context):
    user_text = update.message.text

    # Если текст совпадает с "Помощь", перенаправляем на help_handler
    if user_text.strip().lower() == "помощь":
        help_handler(update, context)
        return

    llm = LocalLLM()
    parse_result = llm.analyze_request(user_text)
    intent = parse_result.get("intent", "unknown")
    parameters = parse_result.get("parameters", {})

    orchestrator = Orchestrator()

    if intent in ["show_photos", "show_files"]:
        # Для обоих intent ожидаем, что orchestrator возвращает словарь с "attachments" и "links"
        result_dict = orchestrator.handle_intent(intent, parameters)
        attachments = result_dict.get("attachments", [])
        links = result_dict.get("links", [])
        if attachments:
            for file_id, file_name in attachments:
                temp_path = f"temp_{file_name}"
                orchestrator.drive_agent.download_file(file_id, temp_path)
                # Определяем, является ли файл изображением по расширению
                ext = os.path.splitext(file_name)[1].lower()
                try:
                    with open(temp_path, "rb") as f:
                        if ext in [".jpg", ".jpeg", ".png"]:
                            context.bot.send_photo(chat_id=update.message.chat_id, photo=InputFile(f))
                        else:
                            context.bot.send_document(chat_id=update.message.chat_id, document=InputFile(f))
                except Exception as e:
                    logging.error(f"Ошибка отправки файла {file_name}: {e}")
                os.remove(temp_path)
        if links:
            # Если остались файлы, выводим текстовое сообщение со ссылками
            text_links = "\n".join(links)
            update.message.reply_text(text_links)
        if not attachments and not links:
            update.message.reply_text("Файлы не найдены в указанной папке.")
    else:
        response = orchestrator.handle_intent(intent, parameters)
        update.message.reply_text(response)

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
