import json

def load_memory():
    with open("memory.json") as f:
        return json.load(f)

def save_memory(data):
    with open("memory.json", "w") as f:
        json.dump(data, f, indent=4)