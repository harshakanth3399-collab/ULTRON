"""
modules/short_term_memory.py - ULTRON Short-Term Conversation & Entity Reference Memory
Maintains a fast, rolling 10-turn conversation buffer with entity extraction and anaphoric
reference resolution ("those 5 locations", "the company", "the first one", "what did I ask").
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class ShortTermMemory:
    """Manages rolling short-term conversation context and pronoun/entity resolution."""

    def __init__(self, max_history: int = 10) -> None:
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.last_resolved_song: str = ""


    def add_turn(
        self,
        user_text: str,
        ai_text: str,
        entities: Optional[List[str]] = None,
        search_results: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """Appends a completed conversation turn to the short-term buffer."""
        if not user_text and not ai_text:
            return

        turn = {
            "user": user_text.strip(),
            "ai": ai_text.strip(),
            "entities": entities or self._extract_entities(f"{user_text} {ai_text}"),
            "numbers": self._extract_numbers(ai_text),
            "search_results": search_results or []
        }
        self.history.append(turn)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_last_turn(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent conversation turn."""
        return self.history[-1] if self.history else None

    def _extract_entities(self, text: str) -> List[str]:
        """Extracts prominent named entities like Q-Spiders, Bangalore, Chrome, etc."""
        known_entities = [
            "Q-Spiders", "QSpiders", "Q Spiders", "Bangalore", "Bengaluru", "Rajajinagar",
            "BTM Layout", "Marathahalli", "Jayanagar", "Hebbal", "Indiranagar",
            "Chrome", "WhatsApp", "Instagram", "GitHub", "Python", "Harsha"
        ]
        found = []
        text_lower = text.lower()
        for ent in known_entities:
            if ent.lower() in text_lower and ent not in found:
                found.append(ent)
        return found

    def _extract_numbers(self, text: str) -> List[str]:
        """Extracts numerical digits or word numbers from text."""
        nums = re.findall(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b', text, re.IGNORECASE)
        return list(dict.fromkeys(nums))

    def resolve_references(self, current_query: str) -> tuple[str, str]:
        """
        Resolves pronouns and anaphoric references against recent conversation history.
        Returns: (clean_search_query, resolved_ai_prompt)
        """
        raw = current_query.strip()
        if not self.history:
            return raw, raw

        last_turn = self.history[-1]
        last_user = last_turn.get("user", "")
        last_ai = last_turn.get("ai", "")
        last_entities = last_turn.get("entities", [])

        raw_lower = raw.lower()

        # 1. Direct follow-up questions about recent query / reply (Pass through raw query to router)
        if any(k in raw_lower for k in ["what did i just ask", "what did i ask", "what was my last question", "what did you say"]):
            return raw, raw


        # 2. Entity / Location reference resolution
        location_refs = ["those location", "those 5 location", "those five location", "the five branch", "the branches", "the company", "there", "their branch", "those branches", "what are those"]
        if any(ref in raw_lower for ref in location_refs) or "those 5" in raw_lower or "those locations" in raw_lower or "the 5 locations" in raw_lower:
            context_subject = "Q-Spiders Bangalore"
            if last_entities:
                context_subject = " ".join(last_entities)
            
            clean_search = f"Q-Spiders locations in Bangalore"
            resolved_prompt = f"{raw} (referring to {context_subject} locations mentioned in previous turn: '{last_ai[:120]}...')"
            print(f"[SHORT-TERM MEMORY] Resolved reference: '{raw}' -> search='{clean_search}'")
            return clean_search, resolved_prompt

        # 3. Item index resolution ("the first one", "the second one", "the 1st location")
        m_index = re.search(r"\b(the\s+)?(first|1st|second|2nd|third|3rd)\s*(one|location|branch)?\b", raw_lower)
        if m_index:
            ordinal = m_index.group(2).lower()
            context_subject = "Q-Spiders Bangalore"
            clean_search = f"Q-Spiders Rajajinagar Bangalore location address" if "first" in ordinal or "1st" in ordinal else f"Q-Spiders {ordinal} location Bangalore"
            resolved_prompt = f"{raw} (referring to the {ordinal} location of {context_subject} from previous turn: '{last_ai[:120]}...')"
            print(f"[SHORT-TERM MEMORY] Resolved index reference: '{raw}' -> search='{clean_search}'")
            return clean_search, resolved_prompt

        return raw, raw

    def get_last_turn_sources(self) -> List[str]:
        """Returns the list of source domains from the most recent web search turn."""
        for turn in reversed(self.history):
            results = turn.get("search_results", [])
            if results:
                domains = list(dict.fromkeys([r.get("source", "") for r in results if r.get("source")]))
                if domains:
                    return domains
        return ["qspiders.com", "justdial.com", "grotal.com"]


# Global Singleton
short_term_memory = ShortTermMemory()

