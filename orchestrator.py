from orchestrators.contacts_orchestrator import handle_contacts_intent
from orchestrators.docs_orchestrator import handle_docs_intent
from orchestrators.gmail_orchestrator import handle_gmail_intent
from orchestrators.drive_orchestrator import handle_drive_intent
from orchestrators.calendar_orchestrator import handle_calendar_intent
from orchestrators.weather_orchestrator import handle_weather_intent


def handle_intent(intent: str, parameters: dict, telegram_user_id=None):
    # Intentы, не требующие Google-авторизации:
    if intent in ["current_weather", "current_temperature", "week_forecast"]:
        return handle_weather_intent(intent, parameters)

    if telegram_user_id is None:
        return "Не передан Telegram ID для авторизации."

    if intent in ["search_contact", "add_contact"]:
        return handle_contacts_intent(intent, parameters, telegram_user_id)
    elif intent in ["search_document"]:
        return handle_docs_intent(intent, parameters, telegram_user_id)
    elif intent in ["send_email", "show_messages", "clear_mail", "clear_promotions", "list_starred", "list_unread"]:
        return handle_gmail_intent(intent, parameters, telegram_user_id)
    elif intent in ["save_photo", "show_photos", "show_files"]:
        return handle_drive_intent(intent, parameters, telegram_user_id)
    elif intent in ["create_event", "list_events_date", "list_events_period", "create_meeting", "cancel_meeting", "reschedule_meeting"]:
        return handle_calendar_intent(intent, parameters, telegram_user_id)
    else:
        return "Извините, я не понял вашу команду или это пока не реализовано."