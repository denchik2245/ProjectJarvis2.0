from agents.docs_agent import DocsAgent
from google_auth_manager import get_user_google_credentials


def handle_docs_intent(intent, parameters, telegram_user_id):
    creds = get_user_google_credentials(str(telegram_user_id))
    if not creds:
        return "Для использования этой функции необходимо авторизоваться через Google."
    docs_agent = DocsAgent(credentials_info=creds)

    if intent == "search_document":
        keywords = parameters.get("keywords", [])
        docs = docs_agent.search_documents(keywords)
        if docs:
            lines = []
            for doc in docs:
                line = f"{doc.get('name')} (ссылка: {doc.get('webViewLink')})"
                lines.append(line)
            return "\n".join(lines)
        else:
            return "Ничего не найдено по заданным ключевым словам."
    else:
        return "Неподдерживаемый intent для документов."
