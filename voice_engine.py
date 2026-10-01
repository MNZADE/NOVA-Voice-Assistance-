import speech_recognition as sr
import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate',150)
engine.setProperty('volume',0.9)

voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)

def speak(text, status_label=None, root=None):

    if status_label:
        status_label.config(text="NOVA: " + text)
        root.update()

    engine.say(text)
    engine.runAndWait()

def listen(status_label=None, root=None):

    r = sr.Recognizer()

    with sr.Microphone() as source:

        if status_label:
            status_label.config(text="Listening...")
            root.update()

        r.adjust_for_ambient_noise(source)

        try:
            audio = r.listen(source, timeout=10, phrase_time_limit=8)
        except:
            return ""

    try:
        command = r.recognize_google(audio)
        return command.lower()

    except:
        return ""