# llm/normalize_russian_text.py

import inspect
if not hasattr(inspect, 'getargspec'):
    def getargspec(func):
        fas = inspect.getfullargspec(func)
        return (fas.args, fas.varargs, fas.varkw, fas.defaults)
    inspect.getargspec = getargspec

import re
import pymorphy2

morph = pymorphy2.MorphAnalyzer()

def normalize_russian_text(text: str) -> str:
    """
    Приводит каждое слово текста к его нормальной форме.
    Пример: "Дай мне номер Антона" -> "давать я номер антон"
    """
    words = re.findall(r"[А-Яа-яA-Za-zёЁ]+", text)
    normalized = []
    for w in words:
        parsed = morph.parse(w)[0]
        normalized.append(parsed.normal_form)
    return " ".join(normalized)
