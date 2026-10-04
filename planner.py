"""planner.py - Multi-Command Task Decomposition Engine for ULTRON."""

import re

def plan(command: str) -> list[str]:
    """Splits multi-command prompts into individual actionable sub-tasks."""
    if not command or not command.strip():
        return []

    # ONLY split on explicit sequential multi-action conjunctions ('and then', 'then open', 'then play')
    # NEVER split regular conversational clauses on 'and' or commas!
    raw_parts = re.split(r"\s+(?:and then|then open|then play|then search)\s+", command.strip(), flags=re.IGNORECASE)
    tasks = []
    for p in raw_parts:
        clean = p.strip()
        if clean:
            tasks.append(clean)

    return tasks if tasks else [command.strip()]