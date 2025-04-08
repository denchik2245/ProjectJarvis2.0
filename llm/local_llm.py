import re
import json
import requests
from config import DEEPSEEKS_BASE_URL, MODEL_NAME, TEMPERATURE
from llm.llm_prompts import FEW_SHOT_EXAMPLES

class DeepseekClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434/v1/completions",
                 model: str = "deepseek-r1:14b", temperature: float = 0.2):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature
        }
        response = requests.post(self.base_url, json=payload)
        response.raise_for_status()
        return response.text

class LocalLLM:
    def __init__(self):
        self.client = DeepseekClient(
            base_url=DEEPSEEKS_BASE_URL,
            model=MODEL_NAME,
            temperature=TEMPERATURE
        )

    def analyze_request(self, user_text: str) -> dict:
        final_prompt = FEW_SHOT_EXAMPLES + f"\nПользователь: \"{user_text}\"\nОтвет:"
        generated_text = self.client.generate(final_prompt).strip()

        try:
            full_response = json.loads(generated_text)
            choice_text = full_response.get("choices", [{}])[0].get("text", "")
        except json.JSONDecodeError:
            choice_text = generated_text

        json_text = self.extract_json(choice_text)
        try:
            data = json.loads(json_text)
            return data
        except json.JSONDecodeError as e:
            print("Ошибка JSONDecode:", e)
            print("Сгенерированный текст для парсинга:", choice_text)
            return {"intent": "unknown", "parameters": {}}

    def extract_json(self, text: str) -> str:
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return text