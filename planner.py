def plan(command):

    tasks = []

    parts = command.replace(" then ", " and ").split(" and ")

    for part in parts:
        part = part.strip()
        if part:
            tasks.append(part)

    return tasks