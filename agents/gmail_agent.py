import base64
from email.mime.text import MIMEText
from datetime import datetime
from calendar import monthrange
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import GOOGLE_CREDENTIALS_PATH


class GmailAgent:
    def __init__(self):
        creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)
        self.service = build('gmail', 'v1', credentials=creds)

    def send_email(self, to_address: str, subject: str, body: str) -> dict:
        """
        Отправляет письмо немедленно на указанный адрес.
        """
        message = MIMEText(body, 'plain', 'utf-8')
        message['to'] = to_address
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        create_message = {'raw': raw_message}
        sent_message = self.service.users().messages().send(
            userId='me', body=create_message
        ).execute()
        return sent_message

    def schedule_email(self, to_address: str, subject: str, body: str, scheduled_day: int) -> str:
        """
        Планирует отправку письма на указанный день текущего месяца (или следующего, если день уже прошёл).
        Здесь для демонстрации возвращается сообщение о запланированной отправке.
        """
        now = datetime.now()
        try:
            scheduled_date = now.replace(day=scheduled_day, hour=9, minute=0, second=0, microsecond=0)
        except ValueError:
            return "Неверная дата для планирования письма."

        if scheduled_date < now:
            next_month = now.month + 1 if now.month < 12 else 1
            next_year = now.year if now.month < 12 else now.year + 1
            last_day = monthrange(next_year, next_month)[1]
            if scheduled_day > last_day:
                scheduled_day = last_day
            scheduled_date = datetime(next_year, next_month, scheduled_day, 9, 0, 0)

        return (f"Письмо для адреса {to_address} запланировано на "
                f"{scheduled_date.strftime('%d.%m.%Y %H:%M')}. Текст письма: {body}")

    def list_messages_from_address(self, from_address: str, max_results: int = 10) -> list:
        """
        Возвращает список (до max_results) последних сообщений, где отправитель равен from_address.
        Для каждого сообщения возвращает тему, дату и краткий фрагмент (snippet) содержимого.
        """
        query = f"from:{from_address}"
        response = self.service.users().messages().list(
            userId='me', q=query, maxResults=max_results
        ).execute()
        messages = response.get('messages', [])
        results = []
        for msg in messages:
            msg_detail = self.service.users().messages().get(
                userId='me', id=msg['id'], format='full'
            ).execute()
            headers = msg_detail.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            results.append({
                "subject": header_dict.get("Subject", "(без темы)"),
                "from": header_dict.get("From", ""),
                "date": header_dict.get("Date", ""),
                "snippet": msg_detail.get("snippet", "")
            })
        return results

    def empty_spam(self) -> str:
        """
        Очищает папку "Спам": удаляет все сообщения, помеченные как SPAM.
        """
        spam_ids = self._list_messages_by_label("SPAM")
        if spam_ids:
            self.service.users().messages().batchDelete(
                userId='me', body={"ids": spam_ids}
            ).execute()
            return f"Очистка спама завершена. Удалено сообщений: {len(spam_ids)}"
        else:
            return "Папка 'Спам' уже пуста."

    def empty_trash(self) -> str:
        """
        Очищает корзину: удаляет все сообщения, помеченные как TRASH.
        """
        trash_ids = self._list_messages_by_label("TRASH")
        if trash_ids:
            self.service.users().messages().batchDelete(
                userId='me', body={"ids": trash_ids}
            ).execute()
            return f"Очистка корзины завершена. Удалено сообщений: {len(trash_ids)}"
        else:
            return "Корзина уже пуста."

    def _list_messages_by_label(self, label: str) -> list:
        """
        Возвращает список ID сообщений с заданным label.
        """
        response = self.service.users().messages().list(
            userId='me', labelIds=[label]
        ).execute()
        messages = response.get('messages', [])
        return [msg['id'] for msg in messages]
