"""Jarvis blueprint: voice in -> emotion -> skills or your existing agents -> voice out.

Register in app.py:
    from jarvis import jarvis_bp
    app.register_blueprint(jarvis_bp)
Then open http://127.0.0.1:5000/jarvis
"""
import base64
import os
import logging

from flask import Blueprint, jsonify, request, send_from_directory

import gnani_voice
import jarvis_tools

jarvis_bp = Blueprint("jarvis", __name__)
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = os.getenv("JARVIS_USER_NAME", "boss")

# --- Hooks into your existing agents ----------------------------------------
try:
    from emotion_agent import detect_emotion # type: ignore
except Exception as e:
    logging.warning("jarvis: emotion_agent unavailable (%s)", e)
    detect_emotion = None
try:
    from main_agent import main_agent # type: ignore
except Exception as e:
    logging.warning("jarvis: main_agent unavailable (%s)", e)
    main_agent = None

# Must match the user_id your app.py passes to main_agent (set JARVIS_USER_ID in .env).
USER_ID = os.getenv("JARVIS_USER_ID", "default_user")

EMPATHY = {
    "sad": "I'm sorry you're feeling low, {n}. ",
    "angry": "I understand this is frustrating, {n}. ",
    "happy": "Glad to hear it, {n}! ",
}


def _emotion(text):
    try:
        e = str(detect_emotion(text)).lower() if detect_emotion else "neutral"
    except Exception as ex:
        logging.warning("jarvis: detect_emotion failed (%s)", ex)
        e = "neutral"
    return e if e in ("happy", "sad", "angry", "neutral") else "neutral"


def _reply(text, emotion):
    res = jarvis_tools.run(text)
    if res:
        return res["text"], res.get("action")
    if main_agent:
        try:
            out = main_agent(USER_ID, text)
            if out:
                return EMPATHY.get(emotion, "").format(n=NAME) + str(out), None
        except Exception as ex:
            logging.warning("jarvis: main_agent failed (%s)", ex)
            return f"Something went wrong inside my task core, {NAME}.", None
    return f"I heard you, {NAME}, but my reasoning core isn't connected yet.", None


def _pack(text, lang="en-IN"):
    emotion = _emotion(text)
    reply, action = _reply(text, emotion)
    out = {"transcript": text, "reply": reply, "emotion": emotion, "action": action, "audio": None}
    try:
        out["audio"] = base64.b64encode(gnani_voice.synthesize(reply, language=lang)).decode()
    except Exception as e:  # browser falls back to its own voice
        logging.warning("jarvis TTS failed: %s", e)
    return out


@jarvis_bp.get("/jarvis")
def page():
    return send_from_directory(HERE, "jarvis.html")


@jarvis_bp.post("/api/jarvis/voice")
def voice():
    f = request.files.get("audio")
    if not f:
        return jsonify(error="no audio"), 400
    try:
        text, lang = gnani_voice.transcribe(f.read())
    except Exception as e:
        return jsonify(error=f"Speech recognition failed: {e}"), 502
    if not text:
        return jsonify(error="I didn't catch that."), 200
    return jsonify(_pack(text, lang))


@jarvis_bp.post("/api/jarvis/text")
def text():
    t = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not t:
        return jsonify(error="empty"), 400
    return jsonify(_pack(t))