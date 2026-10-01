import webbrowser
import os
import datetime
from voice_engine import speak
from ai_brain import ask_ai

def run_command(command, status_label=None, root=None):

    if "youtube" in command:

        speak("Opening YouTube", status_label, root)
        webbrowser.open("https://youtube.com")

    elif "google" in command:

        speak("Opening Google", status_label, root)
        webbrowser.open("https://google.com")

    elif "time" in command:

        time = datetime.datetime.now().strftime("%H:%M")
        speak("The time is " + time, status_label, root)

    elif "vs code" in command:

        speak("Opening Visual Studio Code", status_label, root)
        os.system("code")

    elif "stop nova" in command or "exit" in command:

        speak("Goodbye Mohanish", status_label, root)
        os._exit(0)

    else:

        ask_ai(command, status_label, root)