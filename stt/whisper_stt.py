import whisper
import numpy as np

class WhisperSTT:
    def __init__(self, model_name="large"):
        """
        model_name может быть 'tiny', 'base', 'small', 'medium', 'large' и т.д.
        """
        self.model = whisper.load_model(model_name)

    def transcribe_audio(self, audio_file_path: str,
                         temperature: float = 0.0,
                         beam_size: int = 5,
                         best_of: int = 5,
                         apply_preprocessing: bool = True) -> str:
        """
        Распознаёт речь из аудио (русский язык) с улучшенными настройками декодирования.

        :param audio_file_path: Путь к аудиофайлу.
        :param temperature: Параметр температуры для стабильного декодирования (0.0 - минимальная случайность).
        :param beam_size: Размер луча поиска для улучшенного декодирования.
        :param best_of: Количество вариантов для выбора лучшего результата.
        :param apply_preprocessing: Если True, аудио предварительно обрабатывается (обрезается, нормализуется).
        :return: Строка с распознанным текстом.
        """
        if apply_preprocessing:
            # Загрузка аудио и его подготовка
            audio = whisper.load_audio(audio_file_path)
            audio = whisper.pad_or_trim(audio)
            # Пример нормализации громкости (опционально, можно расширить обработку)
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))
            # Передаем аудио в модель
            result = self.model.transcribe(
                audio,
                language="ru",
                temperature=temperature,
                beam_size=beam_size,
                best_of=best_of
            )
        else:
            # Если предварительная обработка не требуется, передаем путь к файлу напрямую
            result = self.model.transcribe(
                audio_file_path,
                language="ru",
                temperature=temperature,
                beam_size=beam_size,
                best_of=best_of
            )
        return result["text"]
