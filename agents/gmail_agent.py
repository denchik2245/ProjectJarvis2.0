# import base64
# from email.mime.text import MIMEText
# from datetime import datetime
# from calendar import monthrange
# from googleapiclient.discovery import build
# from google.oauth2.credentials import Credentials
# from config import GOOGLE_CREDENTIALS_PATH, SCOPES
# from base64 import urlsafe_b64decode
# import os

# class GmailAgent:
#     def __init__(self, credentials_info=None):
#         if credentials_info is not None:
#             creds = Credentials.from_authorized_user_info(credentials_info, scopes=SCOPES)
#         else:
#             creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
#         self.service = build('gmail', 'v1', credentials=creds)

#     # Отправить письмо на указанный адрес
#     def send_email(self, to_address: str, subject: str, body: str) -> dict:
#         message = MIMEText(body, 'plain', 'utf-8')
#         message['to'] = to_address
#         message['subject'] = subject
#         raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
#         create_message = {'raw': raw_message}
#         sent_message = self.service.users().messages().send(
#             userId='me', body=create_message
#         ).execute()
#         return sent_message

#     # Отправить письмо в определенное время
#     def schedule_email(self, to_address: str, subject: str, body: str, scheduled_day: int) -> str:
#         """
#         Планирует отправку письма на указанный день текущего месяца (или следующего, если день уже прошёл).
#         Здесь для демонстрации возвращается сообщение о запланированной отправке.
#         """
#         now = datetime.now()
#         try:
#             scheduled_date = now.replace(day=scheduled_day, hour=9, minute=0, second=0, microsecond=0)
#         except ValueError:
#             return "Неверная дата для планирования письма."

#         if scheduled_date < now:
#             next_month = now.month + 1 if now.month < 12 else 1
#             next_year = now.year if now.month < 12 else now.year + 1
#             last_day = monthrange(next_year, next_month)[1]
#             if scheduled_day > last_day:
#                 scheduled_day = last_day
#             scheduled_date = datetime(next_year, next_month, scheduled_day, 9, 0, 0)

#         return (f"Письмо для адреса {to_address} запланировано на "
#                 f"{scheduled_date.strftime('%d.%m.%Y %H:%M')}. Текст письма: {body}")

#     # Получить последние сообщения от определенного человека
#     def list_messages_from_address(self, from_address: str, max_results: int = 10) -> list:
#         query = f"from:{from_address}"
#         response = self.service.users().messages().list(
#             userId='me', q=query, maxResults=max_results
#         ).execute()
#         messages = response.get('messages', [])
#         results = []
#         for msg in messages:
#             msg_detail = self.service.users().messages().get(
#                 userId='me', id=msg['id'], format='full'
#             ).execute()
#             headers = msg_detail.get('payload', {}).get('headers', [])
#             header_dict = {h['name']: h['value'] for h in headers}
#             results.append({
#                 "subject": header_dict.get("Subject", "(без темы)"),
#                 "from": header_dict.get("From", ""),
#                 "date": header_dict.get("Date", ""),
#                 "snippet": msg_detail.get("snippet", "")
#             })
#         return results

#     # Очистить спам
#     def empty_spam(self) -> str:
#         spam_ids = self._list_messages_by_label("SPAM")
#         if spam_ids:
#             self.service.users().messages().batchDelete(
#                 userId='me', body={"ids": spam_ids}
#             ).execute()
#             return f"Очистка спама завершена. Удалено сообщений: {len(spam_ids)}"
#         else:
#             return "Папка 'Спам' уже пуста."

#     # Очистить корзину
#     def empty_trash(self) -> str:
#         trash_ids = self._list_messages_by_label("TRASH")
#         if trash_ids:
#             self.service.users().messages().batchDelete(
#                 userId='me', body={"ids": trash_ids}
#             ).execute()
#             return f"Очистка корзины завершена. Удалено сообщений: {len(trash_ids)}"
#         else:
#             return "Корзина уже пуста."

#     # Очистить промоакции
#     def empty_promotions(self) -> str:
#         promo_ids = self._list_messages_by_label("CATEGORY_PROMOTIONS")
#         if promo_ids:
#             self.service.users().messages().batchDelete(
#                 userId='me', body={"ids": promo_ids}
#             ).execute()
#             return f"Очистка промоакций завершена. Удалено сообщений: {len(promo_ids)}"
#         else:
#             return "Папка промоакций уже пуста."

#     # Возвращает список ID сообщений с заданным label
#     def _list_messages_by_label(self, label: str) -> list:
#         response = self.service.users().messages().list(
#             userId='me', labelIds=[label]
#         ).execute()
#         messages = response.get('messages', [])
#         return [msg['id'] for msg in messages]

#     def list_unread_messages_with_attachments(self, max_results: int = 10) -> list:
#         response = self.service.users().messages().list(
#             userId='me',
#             labelIds=["UNREAD"],
#             maxResults=max_results
#         ).execute()

#         messages_info = []
#         messages = response.get('messages', [])
#         for msg in messages:
#             msg_detail = self.service.users().messages().get(
#                 userId='me',
#                 id=msg['id'],
#                 format='full'
#             ).execute()

#             headers = msg_detail.get('payload', {}).get('headers', [])
#             header_dict = {h['name']: h['value'] for h in headers}

#             subject = header_dict.get("Subject", "(без темы)")
#             from_ = header_dict.get("From", "")
#             date_ = header_dict.get("Date", "")
#             snippet = msg_detail.get('snippet', '')

#             attachments = []
#             payload = msg_detail.get('payload', {})
#             parts = payload.get('parts', [])
#             for part in parts:
#                 filename = part.get("filename")
#                 body = part.get("body", {})
#                 if filename and body.get("attachmentId"):
#                     attachment_id = body["attachmentId"]
#                     attachments.append({
#                         "filename": filename,
#                         "mimeType": part.get("mimeType", ""),
#                         "attachmentId": attachment_id,
#                         "messageId": msg['id']
#                     })

#             messages_info.append({
#                 "subject": subject,
#                 "from": from_,
#                 "date": date_,
#                 "snippet": snippet,
#                 "attachments": attachments
#             })

#         return messages_info

#     def list_starred_messages_with_attachments(self, max_results: int = 10) -> list:
#         response = self.service.users().messages().list(
#             userId='me',
#             labelIds=["STARRED"],
#             maxResults=max_results
#         ).execute()

#         messages_info = []
#         messages = response.get('messages', [])
#         for msg in messages:
#             msg_detail = self.service.users().messages().get(
#                 userId='me',
#                 id=msg['id'],
#                 format='full'
#             ).execute()

#             headers = msg_detail.get('payload', {}).get('headers', [])
#             header_dict = {h['name']: h['value'] for h in headers}
#             subject = header_dict.get("Subject", "(без темы)")
#             from_ = header_dict.get("From", "")
#             date_ = header_dict.get("Date", "")

#             snippet = msg_detail.get('snippet', '')

#             attachments = []
#             payload = msg_detail.get('payload', {})
#             parts = payload.get('parts', [])
#             for part in parts:
#                 filename = part.get("filename")
#                 body = part.get("body", {})
#                 if filename and body.get("attachmentId"):
#                     attach_id = body["attachmentId"]
#                     attachments.append({
#                         "filename": filename,
#                         "mimeType": part.get("mimeType", ""),
#                         "attachmentId": attach_id,
#                         "messageId": msg['id']
#                     })

#             messages_info.append({
#                 "subject": subject,
#                 "from": from_,
#                 "date": date_,
#                 "snippet": snippet,
#                 "attachments": attachments
#             })

#         return messages_info

#     def download_attachment(self, message_id: str, attachment_id: str, filename: str,
#                             save_dir: str = "./downloads") -> str:
#         attach_resp = self.service.users().messages().attachments().get(
#             userId='me',
#             messageId=message_id,
#             id=attachment_id
#         ).execute()

#         file_data = attach_resp.get('data', "")
#         if not file_data:
#             return ""

#         file_bytes = urlsafe_b64decode(file_data.encode('utf-8'))

#         os.makedirs(save_dir, exist_ok=True)
#         filepath = os.path.join(save_dir, filename)
#         with open(filepath, 'wb') as f:
#             f.write(file_bytes)

#         return filepath

import base64
from email.mime.text import MIMEText
from datetime import datetime
from calendar import monthrange
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.datetime import DateTrigger
from base64 import urlsafe_b64decode
import os
from config import GOOGLE_CREDENTIALS_PATH, SCOPES

class GmailAgent:
    def __init__(self, credentials_info=None):
        if credentials_info is not None:
            creds = Credentials.from_authorized_user_info(credentials_info, scopes=SCOPES)
        else:
            creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        
        self.service = build('gmail', 'v1', credentials=creds)
        self.scheduler = BackgroundScheduler()  # Для планирования задач
        self.scheduler.start()

    # Отправить письмо на указанный адрес
    def send_email(self, to_address: str, subject: str, body: str) -> dict:
        message = MIMEText(body, 'plain', 'utf-8')
        message['to'] = to_address
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        create_message = {'raw': raw_message}
        
        try:
            sent_message = self.service.users().messages().send(
                userId='me', body=create_message
            ).execute()
            return sent_message
        except Exception as e:
            if "401" in str(e):
                # Обработка ошибки 401 (неавторизован)
                return "Ошибка авторизации. Пожалуйста, войдите в аккаунт."

    # Отправить письмо в определенное время (с отложенной отправкой)
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

        # Планируем отправку письма
        self.scheduler.add_job(self.send_email, DateTrigger(run_date=scheduled_date), args=[to_address, subject, body])
        
        return (f"Письмо для адреса {to_address} запланировано на "
                f"{scheduled_date.strftime('%d.%m.%Y %H:%M')}. Текст письма: {body}")

    # Получить последние сообщения от определенного человека
    def list_messages_from_address(self, from_address: str, max_results: int = 10) -> list:
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

    # Очистить спам
    def empty_spam(self) -> str:
        spam_ids = self._list_messages_by_label("SPAM")
        if spam_ids:
            self.service.users().messages().batchDelete(
                userId='me', body={"ids": spam_ids}
            ).execute()
            return f"Очистка спама завершена. Удалено сообщений: {len(spam_ids)}"
        else:
            return "Папка 'Спам' уже пуста."

    # Очистить корзину
    def empty_trash(self) -> str:
        trash_ids = self._list_messages_by_label("TRASH")
        if trash_ids:
            self.service.users().messages().batchDelete(
                userId='me', body={"ids": trash_ids}
            ).execute()
            return f"Очистка корзины завершена. Удалено сообщений: {len(trash_ids)}"
        else:
            return "Корзина уже пуста."

    # Очистить промоакции
    def empty_promotions(self) -> str:
        promo_ids = self._list_messages_by_label("CATEGORY_PROMOTIONS")
        if promo_ids:
            self.service.users().messages().batchDelete(
                userId='me', body={"ids": promo_ids}
            ).execute()
            return f"Очистка промоакций завершена. Удалено сообщений: {len(promo_ids)}"
        else:
            return "Папка промоакций уже пуста."

    # Возвращает список ID сообщений с заданным label
    def _list_messages_by_label(self, label: str) -> list:
        response = self.service.users().messages().list(
            userId='me', labelIds=[label]
        ).execute()
        messages = response.get('messages', [])
        return [msg['id'] for msg in messages]

    def list_unread_messages_with_attachments(self, max_results: int = 10) -> list:
        response = self.service.users().messages().list(
            userId='me',
            labelIds=["UNREAD"],
            maxResults=max_results
        ).execute()

        messages_info = []
        messages = response.get('messages', [])
        for msg in messages:
            msg_detail = self.service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = msg_detail.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}

            subject = header_dict.get("Subject", "(без темы)")
            from_ = header_dict.get("From", "")
            date_ = header_dict.get("Date", "")
            snippet = msg_detail.get('snippet', '')

            attachments = []
            payload = msg_detail.get('payload', {})
            parts = payload.get('parts', [])
            for part in parts:
                filename = part.get("filename")
                body = part.get("body", {})
                if filename and body.get("attachmentId"):
                    attachment_id = body["attachmentId"]
                    attachments.append({
                        "filename": filename,
                        "mimeType": part.get("mimeType", ""),
                        "attachmentId": attachment_id,
                        "messageId": msg['id']
                    })

            messages_info.append({
                "subject": subject,
                "from": from_,
                "date": date_,
                "snippet": snippet,
                "attachments": attachments
            })

        return messages_info

    def download_attachment(self, message_id: str, attachment_id: str, filename: str,
                            save_dir: str = "./downloads") -> str:
        attach_resp = self.service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()

        file_data = attach_resp.get('data', "")
        if not file_data:
            return ""

        file_bytes = urlsafe_b64decode(file_data.encode('utf-8'))

        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(file_bytes)

        return filepath
