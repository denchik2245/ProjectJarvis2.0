import whisper
import numpy as np

class WhisperSTT:
    def __init__(self, model_name="large"):
        self.model = whisper.load_model(model_name)

    def transcribe_audio(self, audio_file_path: str,
                         temperature: float = 0.0,
                         beam_size: int = 5,
                         best_of: int = 5,
                         apply_preprocessing: bool = True) -> str:
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
