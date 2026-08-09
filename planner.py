"""planner.py - Multi-Command Task Decomposition Engine for ULTRON."""

import re

def plan(command: str) -> list[str]:
    """Splits multi-command prompts into individual actionable sub-tasks."""
    if not command or not command.strip():
        return []

    # Split on conjunctions: 'and then', 'then', 'and', ',', ';'
    raw_parts = re.split(r"\s+(?:and then|then|and|,|;)\s+", command.strip(), flags=re.IGNORECASE)
    tasks = []
    for p in raw_parts:
        clean = p.strip()
        if clean:
            tasks.append(clean)

    return tasks if tasks else [command.strip()]