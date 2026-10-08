from datetime import datetime
from threading import Lock
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai_brain import ask_ai
from commands import run_command
from voice_engine import capture_speech, listen, speak, speech_available


app = FastAPI(title="NOVA Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_microphone_lock = Lock()


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _validated_text(request: MessageRequest) -> str:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be blank.")
    return text


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 21:
        return "Good evening"
    return "Good night"


@app.get("/api/health")
def health():
    return {
        "status": "ready",
        "assistant": "NOVA",
        "ai_configured": bool(os.getenv("GEMINI_API_KEY")),
        "speech_available": speech_available(),
    }


@app.post("/api/greeting")
def greeting():
    salutation = _time_of_day(datetime.now().hour)
    message = f"{salutation}, Mohanish. How can I help you today?"
    speak(message)
    return {"greeting": salutation, "spoken": True}


@app.post("/api/listen")
def listen_for_command():
    if not _microphone_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="NOVA is already listening through the microphone.",
        )

    try:
        with capture_speech():
            recognized_text = listen(timeout=3, phrase_time_limit=12)
        return {
            "recognized": bool(recognized_text),
            "heard": recognized_text or "",
        }
    finally:
        _microphone_lock.release()


@app.post("/api/ask")
def ask(request: MessageRequest):
    answer = ask_ai(_validated_text(request))
    return {"response": answer}


@app.post("/api/command")
def command(request: MessageRequest):
    text = _validated_text(request)
    if not _microphone_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="NOVA is currently processing another voice request.",
        )

    try:
        with capture_speech() as spoken_messages:
            try:
                run_command(text)
            except SystemExit:
                pass
        return {"spoken": bool(spoken_messages)}
    finally:
        _microphone_lock.release()
