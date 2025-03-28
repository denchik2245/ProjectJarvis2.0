import re
import pymorphy2
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import GOOGLE_CREDENTIALS_PATH
from .synonyms import NAME_SYNONYMS  # Файл synonyms.py

morph = pymorphy2.MorphAnalyzer()


def normalize_word(word: str) -> str:
    """
    Приводит слово к его нормальной форме (именительный падеж).
    Например, "антона" -> "антон". Если слово не меняется, возвращает его как есть.
    """
    parsed = morph.parse(word)[0]
    return parsed.normal_form


class ContactsAgent:
    def __init__(self):
        creds = Credentials.from_authorized_user_file(GOOGLE_CREDENTIALS_PATH)
        # Добавляем поле birthdays в список personFields
        self.service = build('people', 'v1', credentials=creds)

    def search_contacts(self, name=None, company=None):
        """
        Ищет контакты по имени и компании.
        Если name состоит из одного слова (например, "Антон", "Антоха"),
        то производится нормализация и проверка по словарю синонимов.
        Если name содержит несколько слов, используется обычное сравнение подстроки.

        Теперь дополнительно извлекается информация о днях рождения.
        """
        user_name_clean = (name or "").strip().lower()
        if user_name_clean:
            words = user_name_clean.split()
            if len(words) == 1:
                normalized_input = normalize_word(words[0])
                # Получаем список синонимов для normalized_input,
                # если его нет в словаре, используем само normalized_input.
                synonyms_list = NAME_SYNONYMS.get(normalized_input, [normalized_input])
            else:
                normalized_input = None  # будем искать по подстроке
        else:
            normalized_input = None

        # Запрашиваем контакты. Добавляем поле 'birthdays' для получения дня рождения.
        results = self.service.people().connections().list(
            resourceName='people/me',
            pageSize=1000,
            personFields='names,phoneNumbers,emailAddresses,organizations,birthdays'
        ).execute()
        connections = results.get('connections', [])
        matched_contacts = []

        for person in connections:
            person_name = self._extract_name(person)
            person_name_lower = person_name.lower()

            # Отладочный вывод: покажем имя контакта и его первую лексему с нормализацией
            if person_name_lower:
                first_word = person_name_lower.split()[0]
                normalized_contact = normalize_word(first_word)
                print(
                    f"Контакт: '{person_name}' -> первая лексема: '{first_word}', нормализовано: '{normalized_contact}'")
            else:
                normalized_contact = ""

            if user_name_clean:
                if normalized_input is None:
                    # Многословный запрос – ищем точное вхождение
                    if user_name_clean not in person_name_lower:
                        continue
                else:
                    # Одно слово: проверяем, содержится ли нормализованное имя контакта в списке синонимов
                    if normalized_contact not in synonyms_list:
                        continue

            # Собираем данные контакта
            contact_data = {
                "name": person_name,
                "phones": self._extract_phones(person),
                "emails": self._extract_emails(person),
                "companies": self._extract_companies(person),
                "birthdays": self._extract_birthdays(person)
            }
            matched_contacts.append(contact_data)
        return matched_contacts

    def _extract_name(self, person):
        names = person.get('names', [])
        if names:
            return names[0].get('displayName', '')
        return ''

    def _extract_phones(self, person):
        phones = person.get('phoneNumbers', [])
        return [p.get('value', '').strip() for p in phones if p.get('value')]

    def _extract_emails(self, person):
        emails = person.get('emailAddresses', [])
        return [e.get('value', '').strip() for e in emails if e.get('value')]

    def _extract_companies(self, person):
        orgs = person.get('organizations', [])
        return [o.get('name', '').strip() for o in orgs if o.get('name')]

    def _extract_birthdays(self, person):
        """
        Извлекает дни рождения контакта.
        Если поле 'birthdays' присутствует и содержит дату, возвращает список дат в формате "DD.MM.YYYY"
        (или "DD.MM", если год не указан).
        """
        birthdays = person.get('birthdays', [])
        results = []
        for b in birthdays:
            date = b.get('date')
            if date:
                day = date.get('day')
                month = date.get('month')
                year = date.get('year')
                if day and month and year:
                    results.append(f"{day:02d}.{month:02d}.{year}")
                elif day and month:
                    results.append(f"{day:02d}.{month:02d}")
        return results