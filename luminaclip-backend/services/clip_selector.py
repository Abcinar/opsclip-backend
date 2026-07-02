"""
Clip Selector — Claude AI ile en iyi anları seçer.
Kullanıcı komutu varsa ona göre, yoksa viral potansiyel hesaplar.
"""
import json
import anthropic
from core.config import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

VIRAL_CRITERIA = {
    "ar": "اللحظات التي تثير المشاعر، والاقتباسات القوية، والمعلومات المفاجئة، والنقاط الجدلية",
    "hi": "Emotional moments, surprising facts, controversial opinions, Hinglish code-switching moments that feel natural",
    "id": "Momen emosional, fakta mengejutkan, pendapat kontroversial, humor lokal",
    "tr": "Duygusal anlar, şaşırtıcı bilgiler, tartışmalı görüşler, güçlü alıntılar",
    "en": "Emotional hooks, surprising facts, controversial takes, strong quotes",
}

async def select_clips(
    transcript_segments: list,
    language: str = "ar",
    user_command: str = None,
    max_clips: int = 8,
    min_duration: float = 20.0,
    max_duration: float = 90.0
) -> list:
    """
    Transkript segmentlerinden en iyi klipleri seçer.
    Döndürür: [{start, end, title, viral_score, reason}]
    """
    # Transkript metni oluştur
    transcript_text = ""
    for seg in transcript_segments:
        transcript_text += f"[{seg['start']:.1f}s - {seg['end']:.1f}s]: {seg['text']}\n"

    viral_criteria = VIRAL_CRITERIA.get(language, VIRAL_CRITERIA["en"])

    if user_command:
        task = f"""The user wants: "{user_command}"
Find segments that match this request."""
    else:
        task = f"""Find the most viral-worthy moments based on: {viral_criteria}"""

    prompt = f"""You are an expert viral video editor specializing in {language} content.

TRANSCRIPT:
{transcript_text}

TASK: {task}

Select {max_clips} best clips. Each clip should be {min_duration}-{max_duration} seconds long.
Return ONLY a JSON array, no other text:

[
  {{
    "start": 12.5,
    "end": 47.2,
    "title": "Short catchy title (max 8 words)",
    "viral_score": 92,
    "reason": "Why this moment is viral-worthy"
  }}
]

Rules:
- viral_score: 0-100 (be realistic, not everything is 90+)
- Clips must not overlap
- Prefer complete thoughts/sentences
- For {language}: respect natural speech boundaries"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # JSON parse
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    clips = json.loads(raw)

    # Duration filtresi
    filtered = [
        c for c in clips
        if min_duration <= (c["end"] - c["start"]) <= max_duration
    ]

    return sorted(filtered, key=lambda x: x["viral_score"], reverse=True)
