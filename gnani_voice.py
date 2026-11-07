"""Gnani.ai voice layer: Prisma (speech-to-text) and Timbre (text-to-speech).

Endpoints and fields follow docs.gnani.ai (quick-start). Set GNANI_API_KEY in .env.
"""
import os
import requests

API = "https://api.vachana.ai"
STT_MODEL = os.getenv("GNANI_STT_MODEL", "prisma-v3.0")   # or "prisma-v2.5"
TTS_MODEL = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")
TTS_VOICE = os.getenv("GNANI_TTS_VOICE", "Nalini")         # see Voice Catalog in docs


def _headers():
    key = os.getenv("GNANI_API_KEY")
    if not key:
        raise RuntimeError("GNANI_API_KEY is not set")
    return {"X-API-Key-ID": key}


def transcribe(wav_bytes, language_code=None):
    """Audio (WAV, max 30 s) -> (transcript, detected_language_code)."""
    data = {"model": STT_MODEL}
    lang = language_code or os.getenv("GNANI_STT_LANGUAGE")
    data["language_code"] = lang or ("hi-IN" if STT_MODEL == "prisma-v2.5" else "indic-auto")
    r = requests.post(
        f"{API}/stt/v3",
        headers=_headers(),
        files={"audio_file": ("speech.wav", wav_bytes, "audio/wav")},
        data=data,
        timeout=60,
    )
    r.raise_for_status()
    j = r.json()
    if not j.get("success", True):
        raise RuntimeError(f"STT failed: {j}")
    return j.get("transcript", "").strip(), j.get("detected_language_code", "en-IN")


def synthesize(text, language="en-IN", speed=1.0):
    """Text -> WAV bytes. Long replies are trimmed so speech stays snappy."""
    text = text.strip()[:500]
    r = requests.post(
        f"{API}/api/v1/tts/inference",
        headers={**_headers(), "Content-Type": "application/json"},
        json={
            "text": text,
            "voice": TTS_VOICE,
            "model": TTS_MODEL,
            "language": language,
            "speed": speed,
            "audio_config": {
                "sample_rate": 24000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.content