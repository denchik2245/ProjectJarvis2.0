google_auth.py - Скрипт, который нужно запустить один раз, чтобы авторизоваться в Google и сохранить токены в google_credentials.json

whisper_stt.py - Модуль для распознавания речи с помощью Whisper

local_llm.py - 

orchestrator.py - Этот класс отвечает за логику распределения: получает от LLM (intent, parameters) и решает, что делать (обращаться к ContactsAgent и т.п.).

telegram_bot.py - Здесь код, который работает с Telegram Bot API. Логика получения голосового сообщения, сохранения в файл, вызова WhisperSTT, вызова LLM и оркестратора
При получении голосового сообщения:
Скачиваем файл.
Распознаём с помощью WhisperSTT.
Определяем intent через LocalLLM.
Вызываем Orchestrator.
Возвращаем результат пользователю.

Как расширять проект
Чтобы добавить новую функциональность (новый Google-сервис или иной API), создаётся новый модуль-агент в папке agents (например, calendar_agent.py), пишется логика, а затем в orchestrator.py добавляется соответствующий метод _handle_*, который вызывает новый агент
Чтобы улучшить распознавание речи, можно поменять реализацию stt/whisper_stt.py, не затрагивая остальной код
Чтобы поменять или улучшить работу LLM, достаточно изменить llm/local_llm.py
