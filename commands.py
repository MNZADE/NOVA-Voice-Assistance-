import datetime
import ctypes
import os
import re
import urllib.parse
import webbrowser
from pathlib import Path

from ai_brain import ask_ai
from voice_engine import listen, speak


SAFE_FILE_EXTENSIONS = {
    ".bmp", ".csv", ".doc", ".docx", ".gif", ".jpeg", ".jpg",
    ".m4a", ".mkv", ".mov", ".mp3", ".mp4", ".mpeg", ".pdf",
    ".png", ".ppt", ".pptx", ".rtf", ".txt", ".wav", ".webp",
    ".xls", ".xlsx",
}
NAMED_FOLDERS = {
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "downloads": Path.home() / "Downloads",
    "pictures": Path.home() / "Pictures",
    "videos": Path.home() / "Videos",
}


def _available_drives():
    try:
        drive_mask = ctypes.windll.kernel32.GetLogicalDrives()
    except (AttributeError, OSError):
        drive_mask = 0

    drives = []
    for index in range(26):
        if drive_mask and not drive_mask & (1 << index):
            continue
        drive = Path(f"{chr(ord('A') + index)}:\\")
        if drive.is_dir():
            drives.append(drive)
    return drives


def _list_navigation_items(folder):
    folders = []
    files = []
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        folders.append(entry.name)
                    elif (
                        entry.is_file(follow_symlinks=False)
                        and Path(entry.name).suffix.lower() in SAFE_FILE_EXTENSIONS
                    ):
                        files.append(entry.name)
                except OSError:
                    continue
    except OSError as e:
        print(f"Could not list folder {folder}: {e}")

    return sorted(folders, key=str.casefold), sorted(files, key=str.casefold)


def _normalize_navigation_choice(choice):
    choice = choice.strip().strip("\"'")
    if choice.casefold() in {
        "open here",
        "open this folder",
        "open current folder",
        "open this location",
    }:
        return choice.casefold()
    choice = re.sub(r"^(?:open|go to|enter|select)\s+", "", choice.strip(), flags=re.I)
    choice = re.sub(r"\s+(?:folder|file|drive)$", "", choice, flags=re.I)
    return choice.strip().strip("\"'").casefold()


def _set_browse_status(text, status_label, root):
    if status_label is None:
        return
    try:
        if root is not None:
            root.after(0, lambda: status_label.config(text=text))
        else:
            status_label.config(text=text)
    except Exception as e:
        print("Could not update file browser status:", e)


def _browse_computer(status_label=None, root=None):
    try:
        os.startfile("shell:MyComputerFolder")
    except (AttributeError, OSError) as e:
        print("Could not open This PC in File Explorer:", e)

    drives = _available_drives()
    if not drives:
        speak("I couldn't find any available computer drives.", status_label, root)
        return

    drive_labels = [f"{drive.drive[0]} drive" for drive in drives]
    speak(
        "This PC is open. Available drives are "
        + ", ".join(drive_labels)
        + ". Which drive should I open? Say a drive letter, or say cancel.",
        status_label,
        root,
    )
    _set_browse_status("Computer open. Choose a drive by voice.", status_label, root)

    try:
        response = listen(status_label, root)
    except Exception as e:
        print("Could not hear drive selection:", e)
        speak("I couldn't hear which drive you chose.", status_label, root)
        return

    drive_choice = _normalize_navigation_choice(response)
    drive_match = re.fullmatch(r"(?:drive\s+)?([a-z])(?::)?(?:\s+drive)?", drive_choice)
    if drive_choice in {"cancel", "stop", "never mind", "close"}:
        speak("Okay, I cancelled computer browsing.", status_label, root)
        return
    if drive_match is None:
        speak("Please say a drive letter, such as C drive, or say cancel.", status_label, root)
        return

    drive_letter = drive_match.group(1).upper()
    current = next((drive for drive in drives if drive.drive[0].upper() == drive_letter), None)
    if current is None:
        speak(f"I couldn't find drive {drive_letter}.", status_label, root)
        return

    path_stack = [current]
    page_index = 0
    while path_stack:
        current = path_stack[-1]
        folders, files = _list_navigation_items(current)
        items = [(True, name) for name in folders]
        items.extend((False, name) for name in files)
        page_size = 12
        page_count = max(1, (len(items) + page_size - 1) // page_size)
        page_index = min(page_index, page_count - 1)
        page_items = items[page_index * page_size:(page_index + 1) * page_size]
        shown_folders = [name for is_folder, name in page_items if is_folder]
        shown_files = [name for is_folder, name in page_items if not is_folder]
        listing = []
        if shown_folders:
            listing.append("Folders: " + ", ".join(shown_folders))
        if shown_files:
            listing.append("Files: " + ", ".join(shown_files))
        contents = ". ".join(listing) if listing else "This folder is empty."
        page_prompt = (
            f" Page {page_index + 1} of {page_count}."
            if page_count > 1
            else ""
        )
        paging_prompt = (
            " Say next page or previous page to hear more."
            if page_count > 1
            else ""
        )

        _set_browse_status(f"Browsing {current}", status_label, root)
        speak(
            f"You are in {current}. {contents}.{page_prompt} "
            "Say a folder or file name, go back, open this folder, or cancel."
            f"{paging_prompt}",
            status_label,
            root,
        )

        try:
            response = listen(status_label, root)
        except Exception as e:
            print("Could not hear folder selection:", e)
            speak("I couldn't hear your choice. I'll close computer browsing.", status_label, root)
            return

        choice = _normalize_navigation_choice(response)
        if choice in {"cancel", "stop", "stop browsing", "never mind", "close"}:
            speak("Okay, I cancelled computer browsing.", status_label, root)
            return
        if choice in {"back", "go back", "parent", "previous folder"}:
            if len(path_stack) > 1:
                path_stack.pop()
                page_index = 0
                continue
            speak("You are already at the drive. Computer browsing is finished.", status_label, root)
            return
        if choice in {"next", "next page", "more"}:
            if page_index + 1 < page_count:
                page_index += 1
                continue
            speak("There are no more items on this page.", status_label, root)
            continue
        if choice in {"previous page", "previous", "last page"}:
            if page_index > 0:
                page_index -= 1
                continue
            speak("This is already the first page.", status_label, root)
            continue
        if choice in {"open here", "open this folder", "open current folder", "open this location"}:
            _open_local_target(current, status_label, root)
            return

        selected_item = next(
            (
                (is_folder, name)
                for is_folder, name in page_items
                if name.casefold() == choice
            ),
            None,
        )
        if selected_item is not None and selected_item[0]:
            selected_folder = selected_item[1]
            path_stack.append(current / selected_folder)
            page_index = 0
            continue

        if selected_item is not None:
            selected_file = selected_item[1]
            _open_local_target(current / selected_file, status_label, root)
            continue

        speak(
            "I couldn't find that name in this folder. "
            "Please choose one of the names I listed, go back, or cancel.",
            status_label,
            root,
        )


def _song_query(command):
    match = re.match(r"^(?:play|search(?: for)?)\s+(.+)$", command, re.IGNORECASE)
    if not match:
        return None

    query = match.group(1).strip()
    query = re.sub(
        r"\s+(?:on|in)\s+(?:youtube|youtube music)$",
        "",
        query,
        flags=re.IGNORECASE,
    )
    query = re.sub(r"^(?:the\s+)?song\s+", "", query, flags=re.IGNORECASE)
    if query.casefold() in {"music", "a song", "some music", "youtube"}:
        return None
    return query or None


def _resolve_local_target(command):
    match = re.match(
        r"^(?:open|show)\s+(?:(?:the\s+)?(?:file|folder|document|pdf|image)\s+)?(.+)$",
        command,
        re.IGNORECASE,
    )
    if not match:
        return None, False

    target_text = match.group(1).strip().strip("\"'")
    folder_match = re.fullmatch(
        r"(?:my\s+)?(desktop|documents|downloads|pictures|videos|home)",
        target_text,
        re.IGNORECASE,
    )
    if folder_match:
        folder_name = folder_match.group(1).lower()
        folder = Path.home() if folder_name == "home" else NAMED_FOLDERS[folder_name]
        return (folder if folder.exists() else None), True

    in_folder = re.fullmatch(
        r"(.+?)\s+in\s+(?:my\s+)?"
        r"(desktop|documents|downloads|pictures|videos)",
        target_text,
        re.IGNORECASE,
    )
    if in_folder:
        filename, folder_name = in_folder.groups()
        folder = NAMED_FOLDERS[folder_name.lower()]
        if not folder.is_dir():
            return None, True

        direct_match = folder / filename.strip().strip("\"'")
        if direct_match.exists():
            return direct_match, True

        requested_name = Path(filename.strip().strip("\"'")).name.casefold()
        try:
            for candidate in folder.rglob("*"):
                if candidate.is_file() and candidate.name.casefold() == requested_name:
                    return candidate, True
        except OSError as e:
            print(f"Could not search {folder}: {e}")
        return None, True

    target = Path(os.path.expandvars(os.path.expanduser(target_text)))
    if target.exists():
        return target, True
    return None, True


def _open_local_target(target, status_label=None, root=None):
    if target is None:
        speak(
            "I couldn't find that item. Give me its full path, or name a folder "
            "such as Downloads or Pictures.",
            status_label,
            root,
        )
        return

    if target.is_file() and target.suffix.lower() not in SAFE_FILE_EXTENSIONS:
        speak(
            "For safety, I only open documents, images, and media files from "
            "voice commands. I won't launch that file type.",
            status_label,
            root,
        )
        return

    try:
        os.startfile(str(target))
        speak(f"Opening {target.name or target}", status_label, root)
    except OSError as e:
        print(f"Could not open {target}: {e}")
        speak("I found it, but Windows could not open that item.", status_label, root)


def _is_time_request(command):
    return command == "time" or bool(
        re.search(
            r"\b(?:what(?:'s| is)? the time|what time is it|current time|"
            r"time now|tell me the time|clock)\b",
            command,
        )
    )


def _is_date_request(command):
    return any(
        phrase in command
        for phrase in ("what day", "day is it", "today's date", "today is")
    ) or bool(re.search(r"\bdate\b", command))


def is_general_question(command):
    question_starters = [
        "what ", "who ", "when ", "where ", "why ", "how ",
        "which ", "can you ", "tell me ", "explain ", "search for ",
        "find ", "what is ", "who is ", "what are ", "who are "
    ]
    return any(start in command for start in question_starters)


def run_command(command, status_label=None, root=None):
    original_command = (command or "").strip()
    command = original_command.lower()

    if not command:
        return

    if command in {
        "open my computer",
        "open this pc",
        "open computer",
        "browse my computer",
        "browse computer",
        "open my pc",
    }:
        _browse_computer(status_label, root)

    elif (song_query := _song_query(original_command)):
        speak(f"Searching YouTube for {song_query}", status_label, root)
        encoded_query = urllib.parse.quote_plus(song_query)
        webbrowser.open(
            f"https://www.youtube.com/results?search_query={encoded_query}"
        )

    elif any(phrase in command for phrase in ("open browser", "start browser", "launch browser")):
        speak("Opening your browser", status_label, root)
        webbrowser.open("https://www.google.com")

    elif "youtube" in command:
        speak("Opening YouTube", status_label, root)
        webbrowser.open("https://youtube.com")

    elif any(phrase in command for phrase in ("google drive", "my drive", "open drive")):
        speak("Opening your Google Drive", status_label, root)
        webbrowser.open("https://drive.google.com/drive/my-drive")

    elif any(
        phrase in command
        for phrase in ("my location", "where am i", "where is my location")
    ):
        speak(
            "Opening Maps. Use the current location button in your browser "
            "and allow location access if you want a precise result.",
            status_label,
            root,
        )
        webbrowser.open("https://www.google.com/maps")

    elif "google" in command:
        speak("Opening Google", status_label, root)
        webbrowser.open("https://google.com")

    elif command.startswith(("open ", "show ")):
        target, matched = _resolve_local_target(original_command)
        if matched:
            _open_local_target(target, status_label, root)
        else:
            ask_ai(command, status_label, root)

    elif _is_time_request(command):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak("The current time is " + current_time, status_label, root)

    elif _is_date_request(command):
        today = datetime.datetime.now()
        speak(
            "Today is " + today.strftime("%A, %B %d, %Y"),
            status_label,
            root,
        )

    elif "vs code" in command:
        speak("Opening Visual Studio Code", status_label, root)
        try:
            os.system("code")
        except Exception:
            pass

    elif "stop nova" in command or "exit" in command:
        speak("Goodbye Mohanish", status_label, root)
        raise SystemExit(0)

    elif is_general_question(command):
        ask_ai(command, status_label, root)

    else:
        ask_ai(command, status_label, root)