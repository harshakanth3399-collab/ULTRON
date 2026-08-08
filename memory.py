from modules.memory.profile_manager import get_profile_manager


def remember(key, value):
    pm = get_profile_manager()
    if key == "note":
        pm.add_note(value)
    else:
        pm.set_preference(key, value)


def recall(key):
    pm = get_profile_manager()
    if key == "note":
        notes = pm.get_notes()
        return notes[-1] if notes else None
    return pm.get_preference(key)