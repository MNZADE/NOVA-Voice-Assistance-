import threading
from voice_engine import listen, speak
from commands import run_command
from wake_word import detect_wake_word
from ui import create_ui


# Create UI
root, status_label = create_ui()


def update_status(text):
    status_label.config(text=text)
    root.update_idletasks()


def assistant_loop():

    speak("Hello Mohanish. Nova system online.", status_label, root)

    while True:

        try:

            update_status("Listening...")

            command = listen(status_label, root)

            if command == "":
                continue

            print("User:", command)

            # Wake word detection
            if detect_wake_word(command):

                speak("Yes Mohanish, how can I help you?", status_label, root)

                update_status("Waiting for command...")

                command = listen(status_label, root)

                if command == "":
                    continue

                print("Command:", command)

                update_status("Processing...")

                run_command(command, status_label, root)

            else:
                # If user directly says command
                run_command(command, status_label, root)

        except Exception as e:

            print("Nova Error:", e)


# Start assistant thread
assistant_thread = threading.Thread(
    target=assistant_loop,
    daemon=True
)

assistant_thread.start()


# Start UI
root.mainloop()