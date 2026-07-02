"""
ASR Service — Dile göre en iyi modele yönlendirir.
Şu an: OpenAI Whisper API
İleride: Fine-tuned modeller
"""
import openai
from core.config import settings

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

# Dil → Whisper dil kodu
LANGUAGE_MAP = {
    "ar": "ar",   # Arabic
    "hi": "hi",   # Hindi (Hinglish için prompt eklenecek)
    "id": "id",   # Indonesian
    "tr": "tr",   # Turkish
    "en": "en",
}

# Dil-özel Whisper prompt'ları — doğruluğu artırır
LANGUAGE_PROMPTS = {
    "ar": "هذا نص باللغة العربية. يرجى النسخ بدقة مع علامات الترقيم.",
    "hi": "यह हिंदी और English मिश्रित भाषा है। Hinglish transcription with accurate word boundaries.",
    "id": "Ini adalah transkripsi dalam Bahasa Indonesia. Tolong transkripsikan dengan akurat.",
    "tr": "Bu Türkçe bir ses kaydıdır. Lütfen kelime sınırlarına dikkat ederek transkrip edin.",
    "en": "This is an English audio recording. Please transcribe accurately.",
}

async def transcribe_audio(audio_path: str, language: str = "ar") -> dict:
    """
    Ses dosyasını metne çevirir.
    Döndürür: { text, segments: [{start, end, text}] }
    """
    lang_code = LANGUAGE_MAP.get(language, "ar")
    prompt = LANGUAGE_PROMPTS.get(language, "")

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=lang_code,
            prompt=prompt,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"]
        )

    return {
        "text": response.text,
        "language": language,
        "segments": [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            }
            for seg in (response.segments or [])
        ],
        "words": [
            {
                "start": w.start,
                "end": w.end,
                "word": w.word
            }
            for w in (response.words or [])
        ] if hasattr(response, "words") and response.words else []
    }
