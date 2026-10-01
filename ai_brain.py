import os
from openai import OpenAI
from voice_engine import speak
import webbrowser

# Get API key from environment variable (SAFE)
API_KEY = os.getenv("OPENAI_API_KEY")

client = None

if API_KEY:
    client = OpenAI(api_key=API_KEY)


def ask_ai(question, status_label=None, root=None):
    try:
        if client is None:
            raise Exception("No API key found")

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are Nova, a helpful AI assistant."},
                {"role": "user", "content": question}
            ]
        )

        answer = response.choices[0].message.content

        speak(answer, status_label, root)

    except Exception as e:
        print("AI Error:", e)

        speak("I will search the internet for you.", status_label, root)

        webbrowser.open(
            "https://www.google.com/search?q=" + question
        )