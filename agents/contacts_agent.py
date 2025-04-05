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
        user_name_clean = (name or "").strip().lower()
        normalized_query = None
        synonyms_list = None
        if user_name_clean:
            words = user_name_clean.split()
            if len(words) == 1:
                normalized_input = normalize_word(words[0])
                # Если ключа нет в словаре, ищем его в значениях
                if normalized_input in NAME_SYNONYMS:
                    synonyms_list = NAME_SYNONYMS[normalized_input]
                else:
                    for key, syn_list in NAME_SYNONYMS.items():
                        if words[0] in syn_list:
                            normalized_input = key
                            synonyms_list = syn_list
                            break
                    if not synonyms_list:
                        synonyms_list = [normalized_input]
            else:
                normalized_query = " ".join([normalize_word(w) for w in words])

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

            if person_name_lower:
                first_word = person_name_lower.split()[0]
                normalized_contact = normalize_word(first_word)
                print(
                    f"Контакт: '{person_name}' -> первая лексема: '{first_word}', нормализовано: '{normalized_contact}'")
            else:
                normalized_contact = ""

            if user_name_clean:
                if normalized_query:
                    normalized_full = " ".join([normalize_word(w) for w in person_name_lower.split()])
                    if normalized_full != normalized_query:
                        continue
                else:
                    if normalized_contact not in synonyms_list:
                        continue

            if company:
                company_lower = company.strip().lower()
                companies_lower = [c.lower() for c in self._extract_companies(person)]
                if not any(company_lower in c for c in companies_lower):
                    continue

            contact_data = {
                "name": person_name,
                "phones": self._extract_phones(person),
                "emails": self._extract_emails(person),
                "companies": self._extract_companies(person),
                "birthdays": self._extract_birthdays(person)
            }
            matched_contacts.append(contact_data)
        return matched_contacts

    def add_contact(self, contact_name: str, phone: str, company: str = None, birthday: str = None) -> dict:
        """
        Добавляет новый контакт с заданными данными:
         - contact_name: имя контакта (строка).
         - phone: номер телефона (строка).
         - company: название компании (строка или None).
         - birthday: строка в формате "DD.MM.YYYY" или "DD.MM" (опционально).
        Использует People API для создания контакта.
        """
        person = {
            "names": [{"givenName": contact_name}],
            "phoneNumbers": [{"value": phone}]
        }
        if company:
            person["organizations"] = [{"name": company}]
        if birthday:
            parts = birthday.split('.')
            date_obj = {}
            if len(parts) == 3:
                day, month, year = parts
                date_obj["day"] = int(day)
                date_obj["month"] = int(month)
                date_obj["year"] = int(year)
            elif len(parts) == 2:
                day, month = parts
                date_obj["day"] = int(day)
                date_obj["month"] = int(month)
            if date_obj:
                person["birthdays"] = [{"date": date_obj}]
        new_contact = self.service.people().createContact(body=person).execute()
        return new_contact

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