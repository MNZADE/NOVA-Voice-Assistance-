def detect_wake_word(command):

    wake_words = ["hey nova","nova"]

    for word in wake_words:
        if word in command:
            return True

    return False