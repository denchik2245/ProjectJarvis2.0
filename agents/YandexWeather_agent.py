import os
import requests
import datetime

class YandexWeatherAgent:
    def __init__(self):
        self.api_key = os.getenv("YANDEX_WEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("YANDEX_WEATHER_API_KEY не задан в переменной окружения")
        self.base_url = "https://api.weather.yandex.ru/v2/forecast"
        # Координаты по умолчанию — Челябинск
        self.default_lat = "55.1644"
        self.default_lon = "61.4368"
        self.headers = {
            "X-Yandex-API-Key": self.api_key
        }
        self.weekday_mapping = {
            "Monday": "Понедельник",
            "Tuesday": "Вторник",
            "Wednesday": "Среда",
            "Thursday": "Четверг",
            "Friday": "Пятница",
            "Saturday": "Суббота",
            "Sunday": "Воскресенье"
        }

    def get_coordinates(self, city: str) -> (str, str):
        """
        Получает координаты (широту и долготу) для заданного города.
        Если не удалось определить координаты, возвращает координаты по умолчанию.
        """
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "format": "json",
            "q": f"{city}, Россия",
            "limit": 1
        }
        response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = data[0]["lat"]
                lon = data[0]["lon"]
                return lat, lon
        return self.default_lat, self.default_lon

    def get_current_forecast(self, city: str = None):
        """
        Получает текущий прогноз для заданного города. Если город не указан, используется значение по умолчанию.
        """
        if city:
            lat, lon = self.get_coordinates(city)
        else:
            lat, lon = self.default_lat, self.default_lon
        params = {
            "lat": lat,
            "lon": lon,
            "lang": "ru_RU",
            "limit": 1,
            "hours": "true"
        }
        response = requests.get(self.base_url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        return None

    def get_today_weather(self, city: str = None) -> str:
        data = self.get_current_forecast(city)
        if not data:
            return "Не удалось получить данные о погоде."
        fact = data.get("fact", {})
        temp = fact.get("temp")
        condition = fact.get("condition")
        # Словарь перевода значений condition
        condition_mapping = {
            "clear": "ясно",
            "partly-cloudy": "переменная облачность",
            "cloudy": "облачно с прояснениями",
            "overcast": "пасмурно",
            "drizzle": "морось",
            "light-rain": "небольшой дождь",
            "rain": "дождь",
            "moderate-rain": "умеренно сильный дождь",
            "heavy-rain": "сильный дождь",
            "continuous-heavy-rain": "длительный сильный дождь",
            "showers": "ливень",
            "wet-snow": "дождь со снегом",
            "light-snow": "небольшой снег",
            "snow": "снег",
            "snow-showers": "снегопад",
            "hail": "град",
            "thunderstorm": "гроза",
            "thunderstorm-with-rain": "гроза с дождём",
            "thunderstorm-with-hail": "гроза с градом"
        }
        condition_ru = condition_mapping.get(condition, condition)
        city_name = city if city else "Челябинске"
        return f"Сегодня в {city_name} {temp}° и {condition_ru}."

    def get_current_temperature(self, city: str = None) -> str:
        """
        Возвращает строку с текущей температурой для заданного города.
        """
        data = self.get_current_forecast(city)
        if not data:
            return "Не удалось получить данные о температуре."
        fact = data.get("fact", {})
        temp = fact.get("temp")
        city_name = city if city else "Челябинске"
        return f"Сейчас в {city_name} {temp}°."

    def get_week_forecast(self, city: str = None) -> str:
        """
        Возвращает прогноз погоды на неделю для заданного города.
        Для каждого дня указывается дата, день недели, средняя температура и состояние (на русском).
        """
        if city:
            lat, lon = self.get_coordinates(city)
        else:
            lat, lon = self.default_lat, self.default_lon
        params = {
            "lat": lat,
            "lon": lon,
            "lang": "ru_RU",
            "limit": 7,
            "hours": "false"
        }
        response = requests.get(self.base_url, headers=self.headers, params=params)
        if response.status_code != 200:
            return "Не удалось получить прогноз на неделю."
        data = response.json()
        forecasts = data.get("forecasts", [])
        if not forecasts:
            return "Прогноз на неделю отсутствует."
        output_lines = []

        # Словарь перевода значений condition
        condition_mapping = {
            "clear": "ясно",
            "partly-cloudy": "переменная облачность",
            "cloudy": "облачно с прояснениями",
            "overcast": "пасмурно",
            "drizzle": "морось",
            "light-rain": "небольшой дождь",
            "rain": "дождь",
            "moderate-rain": "умеренно сильный дождь",
            "heavy-rain": "сильный дождь",
            "continuous-heavy-rain": "длительный сильный дождь",
            "showers": "ливень",
            "wet-snow": "дождь со снегом",
            "light-snow": "небольшой снег",
            "snow": "снег",
            "snow-showers": "снегопад",
            "hail": "град",
            "thunderstorm": "гроза",
            "thunderstorm-with-rain": "гроза с дождём",
            "thunderstorm-with-hail": "гроза с градом"
        }

        for forecast in forecasts:
            date_str = forecast.get("date")
            try:
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                continue
            weekday_en = date_obj.strftime("%A")
            weekday_ru = self.weekday_mapping.get(weekday_en, weekday_en)
            day_part = forecast.get("parts", {}).get("day", {})
            temp_avg = day_part.get("temp_avg")
            condition = day_part.get("condition")
            condition_ru = condition_mapping.get(condition, condition)
            output_lines.append(f"{date_obj.strftime('%d.%m.%Y')} - {weekday_ru}: {temp_avg}°, {condition_ru}")
        return "\n".join(output_lines)
