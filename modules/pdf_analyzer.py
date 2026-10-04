"""
modules/pdf_analyzer.py - ULTRON Natural Voice PDF & Document Intelligence Engine

Locates PDFs on Desktop, Documents, or Downloads, extracts textual contents,
and answers user questions or provides spoken executive summaries.
"""

from __future__ import annotations

import os
import re
from typing import Optional, Tuple

from ai import ask_ai
from modules.smart_file_finder import search_files
from modules.system_paths import get_desktop_dir, get_downloads_dir


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts readable text strings from a PDF file using binary stream filtering."""
    try:
        with open(pdf_path, "rb") as f:
            content = f.read()

        # Extract text within stream blocks or parentheses
        text_parts = []
        # Match text chunks between BT (Begin Text) and ET (End Text)
        raw_text = content.decode("latin1", errors="ignore")
        # Extract text in parentheses (Tj / TJ operators in PDF)
        matches = re.findall(r"\((.*?)\)\s*T[jJ]", raw_text)
        if matches:
            text = " ".join(matches)
            text = re.sub(r"\\[nrtbf\\]", " ", text)
            if len(text.strip()) > 50:
                return text.strip()

        # Fallback to general printable ascii strings
        strings = re.findall(r"[A-Za-z0-9\s\.,;:!?'\"/\-()]{4,}", raw_text)
        return " ".join(strings[:200]).strip()
    except Exception as e:
        print(f"[PDF EXTRACT ERROR] {e}")
        return ""


def analyze_pdf(query: str = "") -> Tuple[bool, str]:
    """Finds target PDF on user's machine and provides a spoken summary or answer."""
    # Find matching PDF
    search_q = query if query and not any(k in query.lower() for k in ["analyze", "summarize", "read", "check"]) else "pdf"
    ok, _, paths = search_files(search_q, search_content=False, max_results=3)

    pdf_target = None
    if paths:
        for p in paths:
            if p.lower().endswith(".pdf"):
                pdf_target = p
                break

    if not pdf_target:
        # Check desktop
        desktop = get_desktop_dir()
        for f in os.listdir(desktop):
            if f.lower().endswith(".pdf"):
                pdf_target = os.path.join(desktop, f)
                break

    if not pdf_target:
        return False, "I could not find any PDF document on your Desktop or Downloads to analyze, Harsha."

    extracted_text = _extract_text_from_pdf(pdf_target)
    if not extracted_text or len(extracted_text) < 30:
        return True, f"Located {os.path.basename(pdf_target)}, but the PDF contains scanned image data rather than searchable text."

    prompt = (
        "You are ULTRON, Harsha's personal AI assistant. "
        f"Summarize the key takeaways of this PDF document ({os.path.basename(pdf_target)}) "
        "in 2 clear, direct, spoken sentences:\n\n" + extracted_text[:3000]
    )
    if query:
        prompt += f"\nSpecifically address Harsha's question: '{query}'."

    reply = ask_ai(prompt)
    if reply:
        return True, str(reply)

    return True, f"Analyzed {os.path.basename(pdf_target)}. Extracted {len(extracted_text.split())} words."
