from email.utils import parsedate_to_datetime
from datetime import timezone, timedelta

def format_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        # Учитываем часовую зону Екатеринбурга (UTC+5)
        yekat_timezone = timezone(timedelta(hours=5))
        dt_yekat = dt.astimezone(yekat_timezone)
        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        day = dt_yekat.day
        month_name = months.get(dt_yekat.month, str(dt_yekat.month))
        year = dt_yekat.year
        time_str = dt_yekat.strftime("%H:%M")
        return f"{day} {month_name} {year} год, {time_str}"
    except Exception:
        return date_str