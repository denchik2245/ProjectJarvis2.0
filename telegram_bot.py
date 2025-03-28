import logging
import os

from telegram.ext import Updater, MessageHandler, Filters

from llm.normalize_russian_text import normalize_russian_text
from stt.whisper_stt import WhisperSTT
from llm.local_llm import LocalLLM
from orchestrator import Orchestrator
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)


def voice_message_handler(update, context):
    # Получаем файл голосового сообщения
    file_id = update.message.voice.file_id
    new_file = context.bot.get_file(file_id)

    # Сохраняем во временный файл (OGG)
    voice_file_path = "temp_voice.ogg"
    new_file.download(voice_file_path)

    # 1. Распознаем (Whisper)
    stt = WhisperSTT(model_name="base")  # можно "small", "medium" и т.д.
    recognized_text = stt.transcribe_audio(voice_file_path)

    # Нормализуем (pymorphy2)
    normalized_text = normalize_russian_text(recognized_text)

    # Удалим временный файл после обработки (опционально)
    os.remove(voice_file_path)

    # 2. Запрашиваем LLM (определить intent, параметры)
    llm = LocalLLM()
    parse_result = llm.analyze_request(recognized_text)
    intent = parse_result.get("intent", "unknown")
    parameters = parse_result.get("parameters", {})

    # 3. Оркестратор
    orchestrator = Orchestrator()
    response = orchestrator.handle_intent(intent, parameters)

    # 4. Отправляем ответ
    print("LLM RAW OUTPUT:", parse_result)
    update.message.reply_text(f"Распознанный текст: {recognized_text}\n\n{response}")


def text_message_handler(update, context):
    # Если пользователь отправил обычный текст
    user_text = update.message.text

    # 1. Анализируем LLM
    llm = LocalLLM()
    parse_result = llm.analyze_request(user_text)
    intent = parse_result.get("intent", "unknown")
    parameters = parse_result.get("parameters", {})

    # 2. Оркестратор
    orchestrator = Orchestrator()
    response = orchestrator.handle_intent(intent, parameters)

    # 3. Ответ
    update.message.reply_text(response)


def run_bot():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Обработка голосовых сообщений
    dp.add_handler(MessageHandler(Filters.voice, voice_message_handler))

    # Обработка любого текста
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler))

    # Запуск бота
    updater.start_polling()
    logging.info("Бот запущен. Ожидаю сообщения...")
    updater.idle()
