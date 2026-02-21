"""
app/api/voice.py
================
Voice Assistant API – LangChain Q&A + gTTS audio generation.

Routes:
  POST /api/voice/ask          – Query the AI assistant, get text + audio
  GET  /api/voice/audio/<file> – Serve generated audio files
  GET  /api/voice/languages    – List supported languages
"""

import os

from flask import Blueprint, request, current_app, send_from_directory
from flask_login import current_user

from app import limiter
from app.utils.security import (
    api_success, api_error, login_required_api,
    sanitise_text, get_json_body,
)

voice_bp = Blueprint("voice", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# ASK THE VOICE ASSISTANT
# ─────────────────────────────────────────────────────────────────────────────
@voice_bp.post("/ask")
@login_required_api
@limiter.limit("60 per hour; 5 per minute")
def ask_voice():
    """
    Submit a text or voice query to the LangChain design assistant
    and receive both a text answer and a gTTS-generated audio file.

    Body (JSON):
        query     (str, required)  – user's question
        language  (str, optional)  – 'english', 'hindi', 'telugu' | 'en', 'hi', 'te'
                                      default 'english'
        voice_response (bool)      – whether to generate audio, default True

    Response:
        {
          "answer":    "...",
          "language":  "en",
          "audio_url": "/api/voice/audio/<filename.mp3>",
          "audio_filename": "filename.mp3"
        }
    """
    data, err = get_json_body(query="str")
    if err:
        return api_error(err, 400)

    raw_query   = sanitise_text(data["query"], 500)
    language    = data.get("language", "english").lower().strip()
    want_audio  = bool(data.get("voice_response", True))

    if not raw_query:
        return api_error("Query cannot be empty.", 400)

    # Resolve language code
    supported = current_app.config.get("SUPPORTED_LANGUAGES", {
        "english": "en", "hindi": "hi", "telugu": "te",
        "en": "en", "hi": "hi", "te": "te",
    })
    lang_code = supported.get(language, "en")

    # ── 1. Get text answer from LangChain agent ───────────────────────────────
    try:
        from ai_engine import get_voice_agent
        agent  = get_voice_agent()
        answer = agent.answer(raw_query, language=lang_code)
    except Exception as e:
        current_app.logger.error("VoiceAgent error: %s", e, exc_info=True)
        answer = ("I'm having trouble processing your request right now. "
                  "Please try again in a moment.")

    # ── 2. Generate audio with gTTS ───────────────────────────────────────────
    audio_url      = None
    audio_filename = None

    if want_audio:
        try:
            from ai_engine import get_tts_engine
            audio_dir = current_app.config["AUDIO_FOLDER"]
            os.makedirs(audio_dir, exist_ok=True)

            tts      = get_tts_engine()
            out_path = tts.synthesize(
                text       = answer,
                language   = lang_code,
                output_dir = audio_dir,
            )
            audio_filename = os.path.basename(out_path)
            audio_url      = f"/api/voice/audio/{audio_filename}"

            current_app.logger.info(
                "TTS generated: user=%d lang=%s file=%s",
                current_user.id, lang_code, audio_filename
            )
        except Exception as e:
            current_app.logger.error("TTS generation error: %s", e, exc_info=True)
            # Non-fatal: return text answer even if audio fails
            audio_url = None

    return api_success(
        data={
            "query":          raw_query,
            "answer":         answer,
            "language":       lang_code,
            "audio_url":      audio_url,
            "audio_filename": audio_filename,
            "audio_available": audio_url is not None,
        },
        message="Voice assistant response ready.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SERVE AUDIO FILE
# ─────────────────────────────────────────────────────────────────────────────
@voice_bp.get("/audio/<path:filename>")
@login_required_api
def serve_audio(filename: str):
    """
    Stream a generated gTTS audio file.

    Only the authenticated user's session can access audio files.
    Files are UUID-named so they are not guessable, but we still
    require authentication for defence-in-depth.
    """
    audio_dir = current_app.config["AUDIO_FOLDER"]

    if not os.path.isfile(os.path.join(audio_dir, filename)):
        return api_error("Audio file not found.", 404)

    # Guard: only allow mp3/txt files served here
    allowed_exts = {".mp3", ".wav", ".ogg", ".txt"}
    if not any(filename.lower().endswith(ext) for ext in allowed_exts):
        return api_error("File type not permitted.", 403)

    return send_from_directory(audio_dir, filename)


# ─────────────────────────────────────────────────────────────────────────────
# LIST SUPPORTED LANGUAGES
# ─────────────────────────────────────────────────────────────────────────────
@voice_bp.get("/languages")
def list_languages():
    """Return the list of supported voice languages."""
    languages = [
        {
            "code":         "en",
            "name":         "English",
            "native_name":  "English",
            "keywords":     ["english", "en"],
        },
        {
            "code":         "hi",
            "name":         "Hindi",
            "native_name":  "हिन्दी",
            "keywords":     ["hindi", "hi"],
        },
        {
            "code":         "te",
            "name":         "Telugu",
            "native_name":  "తెలుగు",
            "keywords":     ["telugu", "te"],
        },
    ]
    return api_success(
        data={"languages": languages, "default": "en"},
        message="Supported voice languages.",
    )
