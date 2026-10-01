import tkinter as tk


def create_ui():

    root = tk.Tk()
    root.title("Nova AI Assistant")
    root.geometry("600x550")
    root.configure(bg="#0f172a")   # modern dark background

    # Title
    title = tk.Label(
        root,
        text="NOVA AI",
        font=("Segoe UI", 28, "bold"),
        fg="#22d3ee",
        bg="#0f172a"
    )
    title.pack(pady=25)

    # Chatbot animation
    gif = tk.PhotoImage(file="animations/Live chatbot.gif")

    chatbot_label = tk.Label(
        root,
        image=gif,
        bg="#0f172a"
    )
    chatbot_label.image = gif
    chatbot_label.pack(pady=20)

    # Status text
    status_label = tk.Label(
        root,
        text="Nova is ready...",
        font=("Segoe UI", 13),
        fg="#94a3b8",
        bg="#0f172a"
    )
    status_label.pack(pady=30)

    return root, status_label