import json
import os
import re
import time
import urllib.error
import urllib.request

from voice_engine import speak


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_MODEL = "gemini-3.8-flash"
MAX_GEMINI_ATTEMPTS = 2
GEMINI_REQUEST_TIMEOUT = 15
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


class GeminiConfigurationError(Exception):
    pass


class GeminiResponseError(Exception):
    pass


class GeminiQuotaError(Exception):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


_quota_reset_at = 0.0


def _parse_retry_delay(message):
    match = re.search(
        r"retry in\s+(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?",
        message,
        re.IGNORECASE,
    )
    if match is None:
        return 0
    hours, minutes, seconds = (int(value or 0) for value in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def _is_daily_quota_error(message):
    normalized = message.lower()
    return "per day" in normalized or "daily limit" in normalized


def _format_retry_delay(seconds):
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} hours and {minutes} minutes"
    if minutes:
        return f"{minutes} minutes"
    return f"{seconds} seconds"


def _set_api_status(message, status_label, root):
    if status_label is None:
        return

    try:
        if root is not None:
            root.after(0, lambda: status_label.config(text=message))
        else:
            status_label.config(text=message)
    except Exception as e:
        print("Could not update Nova status:", e)


def _extract_interaction_text(data):
    interaction = data.get("interaction", data.get("response", data))
    if not isinstance(interaction, dict):
        return ""

    direct_text = interaction.get("output_text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    for field in ("outputs", "output", "steps", "candidates"):
        items = interaction.get(field, [])
        if not isinstance(items, list):
            continue

        text_parts = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type not in (None, "model_output", "text", "candidate"):
                continue

            direct_item_text = item.get("text")
            if isinstance(direct_item_text, str) and direct_item_text.strip():
                text_parts.append(direct_item_text.strip())

            content = item.get("content", item.get("parts", []))
            if isinstance(content, dict):
                content = content.get("parts", [content])
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") not in (None, "text"):
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())

        if text_parts:
            return " ".join(text_parts)

    return ""


def _generate_gemini_answer(question, status_label=None, root=None):
    global _quota_reset_at
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY is not configured")

    quota_remaining = max(0, int(_quota_reset_at - time.monotonic()))
    if quota_remaining:
        raise GeminiQuotaError(
            "Gemini daily quota was reached.",
            quota_remaining,
        )

    payload = {
        "model": GEMINI_MODEL,
        "input": question,
        "system_instruction": (
            "You are Nova, a helpful voice assistant. Answer clearly and "
            "conversationally, suitable for being spoken aloud. Keep answers "
            "concise unless asked for detail."
        ),
        "generation_config": {"max_output_tokens": 512},
    }
    request = urllib.request.Request(
        GEMINI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    for attempt in range(MAX_GEMINI_ATTEMPTS):
        try:
            with urllib.request.urlopen(
                request,
                timeout=GEMINI_REQUEST_TIMEOUT,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                error_body = e.read().decode("utf-8", errors="replace")
                try:
                    error_data = json.loads(error_body)
                    detail = error_data.get("error", {}).get("message", error_body)
                except json.JSONDecodeError:
                    detail = error_body

                if _is_daily_quota_error(detail):
                    retry_after = _parse_retry_delay(detail)
                    if retry_after:
                        _quota_reset_at = time.monotonic() + retry_after
                    raise GeminiQuotaError(detail, retry_after) from e

                raise

            if e.code not in RETRYABLE_HTTP_CODES or attempt == MAX_GEMINI_ATTEMPTS - 1:
                raise
            delay = 1
            _set_api_status(
                f"Gemini API is busy. Retrying in {delay} seconds "
                f"({attempt + 1}/{MAX_GEMINI_ATTEMPTS - 1})...",
                status_label,
                root,
            )
            print(
                f"Gemini temporarily unavailable (HTTP {e.code}); "
                f"retrying in {delay} seconds ({attempt + 1}/{MAX_GEMINI_ATTEMPTS - 1})."
            )
            time.sleep(delay)

    answer = _extract_interaction_text(data)
    if not answer:
        raise GeminiResponseError(
            "Gemini returned no text; response keys: "
            + ", ".join(sorted(data.keys()))
        )
    return answer


def ask_ai(question, status_label=None, root=None):
    question = (question or "").strip()
    if not question:
        return

    api_busy = False
    try:
        answer = _generate_gemini_answer(question, status_label, root)
    except GeminiQuotaError as e:
        if e.retry_after:
            retry_message = _format_retry_delay(e.retry_after)
            answer = (
                "Gemini's daily free limit has been reached. Please try again "
                f"in about {retry_message}."
            )
        else:
            answer = (
                "Gemini's daily free limit has been reached. Please try again "
                "later."
            )
        print("Gemini daily quota reached:", e)
        _set_api_status(answer, status_label, root)
    except GeminiConfigurationError as e:
        print("Gemini configuration error:", e)
        answer = (
            "Gemini is not configured yet. Set the GEMINI_API_KEY environment "
            "variable in the terminal, then restart Nova."
        )
    except GeminiResponseError as e:
        print("Gemini response error:", e)
        answer = (
            "Gemini responded, but Nova couldn't read the answer. "
            "Please check the terminal output."
        )
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(error_body)
            detail = error_data.get("error", {}).get("message", error_body)
        except json.JSONDecodeError:
            detail = error_body
        print(f"Gemini API error: HTTP {e.code}: {detail[:1000]}")

        if e.code == 404:
            answer = (
                "Gemini returned a not found error. Please check the model "
                "and API key configuration."
            )
        elif e.code in (401, 403):
            answer = (
                "Gemini rejected the API key. Please check that the key is "
                "valid and that the Gemini API is enabled for its project."
            )
        elif e.code in RETRYABLE_HTTP_CODES:
            api_busy = True
            answer = (
                "Gemini is busy right now. I tried again, but it is still "
                "unavailable. Please try your question again shortly."
            )
        else:
            answer = (
                "Sorry, I couldn't get an answer from Gemini. Check the "
                "terminal for the API error details."
            )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print("Gemini connection or response error:", e)
        answer = "Sorry, I couldn't connect to Gemini. Please check your internet connection."
    except Exception as e:
        print("Gemini error:", e)
        answer = "Sorry, something went wrong while I was preparing that answer."

    speak(answer, status_label, root)
    if api_busy:
        _set_api_status(
            "Gemini API is busy. Please try again shortly.",
            status_label,
            root,
        )
    return answer
