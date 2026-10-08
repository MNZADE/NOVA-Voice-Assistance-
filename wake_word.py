import re


def detect_wake_word(command):
    return get_command_after_wake_word(command) is not None


def get_command_after_wake_word(command):
    match = re.search(r"\b(?:hey\s+)?nova\b[,.!? ]*(.*)$", command, re.IGNORECASE)
    if match is None:
        return None

    return match.group(1).strip()