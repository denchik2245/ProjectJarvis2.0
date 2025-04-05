import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import GOOGLE_CREDENTIALS_PATH


class CalendarAgent:
    def __init__(self):
        creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)
        self.service = build('calendar', 'v3', credentials=creds)
        self.calendar_id = 'primary'

    def create_event(self, title: str, start_datetime: datetime.datetime, reminder_minutes: int = None, attendees: list = None) -> dict:
        """
        Создаёт событие с заданным заголовком, датой и временем начала.
        Событие длится 1 час. Если reminder_minutes задано, устанавливается напоминание.
        Если передан список email в attendees, они добавляются как гости.
        """
        end_datetime = start_datetime + datetime.timedelta(hours=1)
        event = {
            'summary': title,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'Asia/Yekaterinburg'
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'Asia/Yekaterinburg'
            },
            'attendees': [{'email': email} for email in attendees] if attendees else [],
            'reminders': {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': reminder_minutes}] if reminder_minutes is not None else []
            }
        }
        created_event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
        return created_event

    def list_events_for_date(self, date: datetime.date) -> list:
        """
        Возвращает список событий, запланированных на заданную дату.
        """
        start_dt = datetime.datetime.combine(date, datetime.time.min)
        end_dt = datetime.datetime.combine(date, datetime.time.max)
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start_dt.isoformat() + 'Z',
            timeMax=end_dt.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def list_events_for_period(self, start_date: datetime.date, end_date: datetime.date) -> list:
        """
        Возвращает список событий, запланированных в промежутке от start_date до end_date включительно.
        """
        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max)
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start_dt.isoformat() + 'Z',
            timeMax=end_dt.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def list_upcoming_events(self) -> list:
        """
        Возвращает список предстоящих событий.
        """
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=now,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def delete_event(self, event_id: str) -> None:
        """
        Удаляет событие по его ID.
        """
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()