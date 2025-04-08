import datetime
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import SCOPES

class CalendarAgent:
    def __init__(self, credentials_info: dict):
        # credentials_info – словарь с учётными данными Google
        creds = Credentials.from_authorized_user_info(credentials_info, scopes=SCOPES)
        self.service = build('calendar', 'v3', credentials=creds)
        self.calendar_id = 'primary'
        self.tz = ZoneInfo("Asia/Yekaterinburg")  # Временная зона календаря

    def create_event(self, title: str, start_datetime: datetime.datetime, reminder_minutes: int = None, attendees: list = None) -> dict:
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=self.tz)
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
        start_dt = datetime.datetime.combine(date, datetime.time.min, tzinfo=self.tz)
        end_dt = datetime.datetime.combine(date, datetime.time.max, tzinfo=self.tz)
        start_dt_utc = start_dt.astimezone(datetime.timezone.utc)
        end_dt_utc = end_dt.astimezone(datetime.timezone.utc)
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start_dt_utc.isoformat(),
            timeMax=end_dt_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def list_events_for_period(self, start_date: datetime.date, end_date: datetime.date) -> list:
        start_dt = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=self.tz)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=self.tz)
        start_dt_utc = start_dt.astimezone(datetime.timezone.utc)
        end_dt_utc = end_dt.astimezone(datetime.timezone.utc)
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start_dt_utc.isoformat(),
            timeMax=end_dt_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def list_upcoming_events(self) -> list:
        now = datetime.datetime.now(self.tz).astimezone(datetime.timezone.utc).isoformat()
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=now,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
