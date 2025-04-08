from agents.YandexWeather_agent import YandexWeatherAgent

def handle_weather_intent(intent, parameters):
    weather_agent = YandexWeatherAgent()
    if intent == "current_weather":
         city = parameters.get("city")
         return weather_agent.get_today_weather(city)
    elif intent == "current_temperature":
         city = parameters.get("city")
         return weather_agent.get_current_temperature(city)
    elif intent == "week_forecast":
         city = parameters.get("city")
         return weather_agent.get_week_forecast(city)
    else:
         return "Неподдерживаемый intent для погоды."
