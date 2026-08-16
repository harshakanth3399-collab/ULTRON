import json
import os

FILE = "memory/data.json"

def remember(key, value):
    os.makedirs("memory", exist_ok=True)

    data = {}

    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            data = json.load(f)

    data[key] = value

    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)


def recall(key):
    if not os.path.exists(FILE):
        return None

    with open(FILE, "r") as f:
        data = json.load(f)

    return data.get(key)