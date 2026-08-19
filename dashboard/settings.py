import json
import os

SETTINGS_FILE = "dashboard/settings.json"


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"hide_balance": False}

    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def is_balance_hidden():
    settings = load_settings()
    return settings.get("hide_balance", False)


def toggle_balance():
    settings = load_settings()
    settings["hide_balance"] = not settings.get("hide_balance", False)
    save_settings(settings)
