import array
from contextlib import contextmanager
from contextvars import ContextVar
import math
import queue
import speech_recognition as sr
import pyttsx3
import sys
import threading

_speech_queue = queue.Queue()
_speech_engine_ready = threading.Event()
_speech_engine_error = None
_speech_capture = ContextVar("speech_capture", default=None)


@contextmanager
def capture_speech():
    messages = []
    token = _speech_capture.set(messages)
    try:
        yield messages
    finally:
        _speech_capture.reset(token)


def _speech_worker():
    global _speech_engine_error
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.setProperty("volume", 1.0)

        voices = engine.getProperty("voices")
        if voices:
            preferred_voice = voices[1] if len(voices) > 1 else voices[0]
            engine.setProperty("voice", preferred_voice.id)
    except Exception as e:
        _speech_engine_error = e
        print("Speech engine initialization error:", e)
        _speech_engine_ready.set()
        return

    _speech_engine_ready.set()
    while True:
        text, completed, errors = _speech_queue.get()
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            errors.append(e)
            print("Speak error:", e)
        finally:
            completed.set()
            _speech_queue.task_done()


_speech_thread = threading.Thread(
    target=_speech_worker,
    name="NovaSpeech",
    daemon=True,
)
_speech_thread.start()
_speech_engine_ready.wait()


def speech_available():
    return _speech_engine_error is None and _speech_thread.is_alive()


# Selected microphone device index (None => default)
SELECTED_MIC = None
SELECTED_MIC_LOCK = threading.Lock()
RECOGNIZER = sr.Recognizer()
RECOGNIZER.dynamic_energy_threshold = True
RECOGNIZER.pause_threshold = 0.8
RECOGNIZER.operation_timeout = 5
SPEECH_LANGUAGES = ("en-IN", "hi-IN", "en-US")
MIC_CALIBRATION_DURATION = 0.3


def _select_working_microphone():
    global SELECTED_MIC
    try:
        # Try default first
        with sr.Microphone():
            return None
    except Exception:
        # Try enumerating microphones
        try:
            names = sr.Microphone.list_microphone_names()
        except Exception:
            names = []

        for i, name in enumerate(names):
            try:
                with sr.Microphone(device_index=i):
                    print(f"Using microphone #{i}: {name}")
                    return i
            except Exception:
                continue

    return None


# Try to select a microphone at import time
with SELECTED_MIC_LOCK:
    SELECTED_MIC = _select_working_microphone()


def speak(text, status_label=None, root=None):
    text = text or ""
    if not text:
        return

    captured_messages = _speech_capture.get()
    if captured_messages is not None:
        captured_messages.append(text)

    if status_label and root is not None:
        try:
            root.after(0, lambda: status_label.config(text="NOVA: " + text))
        except Exception as e:
            print("Could not update Nova's spoken-response status:", e)

    if _speech_engine_error is not None:
        raise RuntimeError(
            "Speech unavailable because the speech engine failed to initialize."
        ) from _speech_engine_error

    completed = threading.Event()
    errors = []
    _speech_queue.put((text, completed, errors))
    completed.wait()
    if errors:
        raise RuntimeError("Could not play NOVA's spoken response.") from errors[0]


def _set_status(text, status_label, root):
    if status_label and root is not None:
        try:
            root.after(0, lambda: status_label.config(text=text))
        except Exception as e:
            print("Status update error:", e)


def listen(status_label=None, root=None, timeout=8, phrase_time_limit=12):
    """
    Listen once and return the recognized text in lowercase, or empty string on failure.
    Uses a previously selected working microphone if available.
    """
    global SELECTED_MIC
    _set_status("Listening...", status_label, root)

    device_index = None
    with SELECTED_MIC_LOCK:
        device_index = SELECTED_MIC

    try:
        with sr.Microphone(device_index=device_index) as source:
            RECOGNIZER.adjust_for_ambient_noise(
                source,
                duration=MIC_CALIBRATION_DURATION,
            )
            print(
                "Microphone calibrated; energy threshold:",
                round(RECOGNIZER.energy_threshold),
            )
            try:
                audio = RECOGNIZER.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            except sr.WaitTimeoutError:
                print("No speech detected before listening timed out.")
                _set_status("I didn't hear speech. Please try again.", status_label, root)
                return ""
    except Exception as e:
        print("Microphone open error:", e)
        message = "Microphone error. Check Windows microphone settings."
        _set_status(message, status_label, root)
        raise RuntimeError(message) from e

    samples = array.array("h")
    samples.frombytes(audio.get_raw_data(convert_width=2))
    if sys.byteorder != "little":
        samples.byteswap()
    rms = math.sqrt(sum(sample * sample for sample in samples) / max(1, len(samples)))
    peak = max((abs(sample) for sample in samples), default=0)
    print(f"Captured microphone signal: RMS={rms:.0f}, peak={peak}")

    if peak == 0:
        retry_message = (
            "I'm sorry, I can't hear any sound. Please check your microphone "
            "and speak again."
        )
        print("Microphone captured digital silence.")
        _set_status(retry_message, status_label, root)
        speak(retry_message, status_label, root)
        return ""

    if rms < 1500:
        gain = min(10.0, 1500 / max(rms, 1))
        gain = min(gain, 30000 / peak)
        normalized_samples = array.array(
            "h",
            (max(-32768, min(32767, round(sample * gain))) for sample in samples),
        )
        audio = sr.AudioData(
            normalized_samples.tobytes(),
            audio.sample_rate,
            2,
        )
        print(f"Raised quiet microphone audio by {gain:.1f}x for recognition.")

    for language in SPEECH_LANGUAGES:
        try:
            command = RECOGNIZER.recognize_google(audio, language=language)
            print(f"Recognized ({language}):", command)
            return command.lower()
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print("Speech recognition request error:", e)
            message = (
                "Speech recognition unavailable. Check your internet connection."
            )
            _set_status(message, status_label, root)
            raise RuntimeError(message) from e

    print("Speech was recorded but could not be understood in English or Hindi.")
    retry_message = (
        "I'm sorry, I heard some sound but couldn't understand your question. "
        "Please speak clearly and repeat it."
    )
    _set_status(retry_message, status_label, root)
    speak(retry_message, status_label, root)
    return ""
