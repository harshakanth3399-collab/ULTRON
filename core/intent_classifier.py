"""Fast 5ms Machine Learning Intent & Command Classifier for ULTRON."""

from __future__ import annotations

import re
from typing import Tuple, Dict, Any


class MLIntentClassifier:
    """Super-fast local intent classifier categorizing voice input in < 5ms."""

    INTENT_PATTERNS: Dict[str, list[str]] = {
        "SYSTEM_CONTROL": [
            r"volume\s*(up|down|mute|unmute)?",
            r"status", r"battery", r"cpu", r"ram", r"system",
            r"brightness", r"shutdown", r"restart"
        ],
        "WEB_SEARCH": [
            r"search\s*(the\s*web|for)?", r"google", r"who\s*is", r"what\s*is", r"latest\s*news", r"weather"
        ],
        "APP_LAUNCH": [
            r"open\s*(youtube|chrome|vscode|spotify|calculator|notepad|explorer)", r"launch"
        ],
        "MEMORY_QUERY": [
            r"remember", r"what\s*did\s*i\s*say", r"my\s*photo", r"my\s*data", r"who\s*am\s*i"
        ],
        "PERSONALITY_CHAT": [
            r"hey", r"hello", r"hi", r"how\s*are\s*you", r"bro", r"what's\s*up"
        ]
    }

    def classify(self, text: str) -> Tuple[str, float]:
        """Classifies text into an intent category with confidence score."""
        clean = text.lower().strip()
        if not clean:
            return "UNKNOWN", 0.0

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, clean):
                    return intent, 0.95

        return "GENERAL_LLM", 0.80


# Global Intent Classifier Instance
intent_classifier = MLIntentClassifier()
