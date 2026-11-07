# Jarvis upgrade: setup

## 1. Add the files
Copy `gnani_voice.py`, `jarvis_tools.py`, `jarvis.py` and `jarvis.html` into the root of your repo (next to `app.py`).

## 2. Register the blueprint in `app.py`
```python
from jarvis import jarvis_bp
app.register_blueprint(jarvis_bp)
```
Make sure `load_dotenv()` runs before the import if you use python-dotenv.

## 3. Environment (`.env`, never commit it)
```
GNANI_API_KEY=your_key_from_app.gnani.ai/voice
OPENWEATHER_API_KEY=your_openweather_key
JARVIS_USER_NAME=Uday
# optional
GNANI_STT_MODEL=prisma-v3.0     # or prisma-v2.5
GNANI_TTS_VOICE=Nalini
```
Add `.env` to `.gitignore`, and rotate any key that was already pushed.

## 4. Dependencies
`requests` and `flask` are already needed. Nothing else to install.

## 5. Connect your existing agents (one edit)
In `jarvis.py`, edit `MAIN_AGENT_FUNCS` and `EMOTION_FUNCS` to the real function names in
`main_agent.py` and `emotion_agent.py`. Anything the fast skills don't handle falls through to your main agent.

## 6. Run
`python app.py`, then open http://127.0.0.1:5000/jarvis (Chrome or Edge for the wake word).

## Notes
- Voice requires HTTPS or localhost for microphone access.
- Gnani STT accepts audio up to 30 s; the page converts recordings to 16 kHz WAV before upload.
- If Gnani TTS fails, the page speaks with the browser voice so the demo never goes silent.
- Check the Voice Catalog and language codes at docs.gnani.ai before choosing a voice for Telugu or Hindi.
