import whisper

class WhisperSTT:

    def __init__(self, model_name="large"):
        """
        model_name может быть 'tiny', 'base', 'small', 'medium', 'large' и т.д.
        """
        self.model = whisper.load_model(model_name)

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Распознаёт речь из аудио (русский язык).
        Возвращает строку с распознанным текстом.
        """
        # Обратите внимание, что Whisper сам декодирует форматы вроде .ogg
        # при наличии ffmpeg на системе.
        result = self.model.transcribe(audio_file_path, language="ru")
        return result["text"]
