"""
agent.py - ULTRON Dynamic Autonomous Agent Engine

Executes multi-step prompts, Tool-Use function calling,
semantic long-term memory retrieval & auto-indexing.
"""

from __future__ import annotations

import re
import os
from pathlib import Path

from modules.memory.vector_memory import vector_memory
from modules.adb_bridge import adb_bridge
from modules.internet import search_web_live
from commands import execute
from ai import ask_ai


class UltronAgent:
    """Dynamic autonomous tool-use agent for ULTRON."""

    def process_task(self, prompt: str) -> tuple[bool, str]:
        prompt_raw = prompt.strip()
        if not prompt_raw:
            return True, "I'm right here, Harsha."

        # 1. Store interaction into Long-Term Semantic Vector Memory
        vector_memory.remember(prompt_raw, category="user_conversation")

        # 2. Retrieve relevant context from semantic vector memory
        relevant_memories = vector_memory.query(prompt_raw, top_k=2)
        context_str = ""
        if relevant_memories:
            mem_texts = [m["text"] for m in relevant_memories]
            context_str = f"\n[Relevant Semantic Memory: {'; '.join(mem_texts)}]\n"

        raw_lower = prompt_raw.lower()

        # ── Tool 1: Camera Vision Perception ──────────────────────────────────
        if any(k in raw_lower for k in ["look at camera", "phone camera", "scan using camera", "what is in front of camera"]):
            res = adb_bridge.capture_phone_camera_vision()
            return True, f"{res} Analyzing camera frame view for you, Harsha."

        # ── Tool 2: Cross-Device Clipboard Sync ───────────────────────────────
        if any(k in raw_lower for k in ["clipboard", "send to phone clipboard", "copy to phone"]):
            text_match = re.search(r"(?:text|clipboard|copy)\s+(.*)", raw_lower)
            text_to_copy = text_match.group(1) if text_match else prompt_raw
            res = adb_bridge.copy_to_phone_clipboard(text_to_copy)
            return True, res

        # ── Tool 3: Wireless File Drop ─────────────────────────────────────────
        if any(k in raw_lower for k in ["send file", "drop file", "push file to phone"]):
            file_match = re.search(r"(?:file|drop|push)\s+(.*)", raw_lower)
            filepath = file_match.group(1).strip() if file_match else ""
            res = adb_bridge.push_file_to_phone(filepath)
            return True, res

        # ── Tool 4: Explicit Remember Command ─────────────────────────────────
        if raw_lower.startswith(("remember that", "save note", "remember ")):
            note_content = re.sub(r"^(remember that|save note|remember)\s+", "", prompt_raw, flags=re.I).strip()
            vector_memory.remember(note_content, category="user_note")
            return True, f"Saved to my long-term semantic memory: '{note_content}', Harsha!"

        # ── Tool 5: Multi-Step Task Execution ─────────────────────────────────
        # Check if prompt contains multiple instructions ("and", "then")
        if " and " in raw_lower or " then " in raw_lower:
            parts = re.split(r"\s+(?:and|then)\s+", prompt_raw, flags=re.I)
            responses = []
            for part in parts:
                p_clean = part.strip()
                if not p_clean:
                    continue
                # Try app execution
                exec_ok = execute(p_clean)
                if exec_ok:
                    responses.append(f"Executed '{p_clean}'.")
                else:
                    ai_reply = ask_ai(context_str + p_clean)
                    if ai_reply:
                        responses.append(ai_reply)

            if responses:
                return True, " ".join(responses)

        # Fallback to AI with semantic memory context
        ai_reply = ask_ai(context_str + prompt_raw)
        if ai_reply:
            return True, ai_reply

        return True, "On it, Harsha!"


ultron_agent = UltronAgent()
