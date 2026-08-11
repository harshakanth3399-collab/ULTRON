"""Personal Data Local Model Trainer for ULTRON."""

from __future__ import annotations

import os
import glob
import subprocess
from typing import Tuple
from modules.memory.profile_manager import get_profile_manager

KNOWLEDGE_DIR = os.path.join("data", "my_knowledge")
MODELFILE_PATH = "Modelfile"
MODEL_NAME = "ultron-harsha"


def build_knowledge_context() -> str:
    """Reads all text documents in data/my_knowledge directory."""
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    files = glob.glob(os.path.join(KNOWLEDGE_DIR, "*.*"))

    knowledge_blocks = []
    for fpath in files:
        if fpath.endswith((".txt", ".md", ".json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        knowledge_blocks.append(f"--- Document: {os.path.basename(fpath)} ---\n{content}")
            except Exception:
                pass

    return "\n\n".join(knowledge_blocks)


def train_local_model(base_model: str = "qwen2.5:3b") -> Tuple[bool, str]:
    """Generates a custom Modelfile and creates 'ultron-harsha' in Ollama."""
    pm = get_profile_manager()
    system_ctx = pm.get_system_context()
    personal_docs = build_knowledge_context()

    full_system_prompt = system_ctx
    if personal_docs:
        full_system_prompt += f"\n\nPersonal Knowledge Base:\n{personal_docs}"

    # Escaped double quotes for Modelfile
    clean_prompt = full_system_prompt.replace('"', '\\"')

    modelfile_content = (
        f'FROM {base_model}\n\n'
        f'PARAMETER temperature 0.6\n'
        f'PARAMETER num_predict 256\n\n'
        f'SYSTEM """{clean_prompt}"""\n'
    )

    try:
        with open(MODELFILE_PATH, "w", encoding="utf-8") as f:
            f.write(modelfile_content)

        print(f"🔨 Building local model '{MODEL_NAME}' in Ollama...")
        res = subprocess.run(
            ["ollama", "create", MODEL_NAME, "-f", MODELFILE_PATH],
            capture_output=True,
            text=True,
            check=True
        )
        return True, f"Successfully trained '{MODEL_NAME}'! Output: {res.stdout.strip()}"
    except FileNotFoundError:
        return False, "Ollama executable not found in system PATH. Ensure Ollama is installed."
    except subprocess.CalledProcessError as e:
        return False, f"Model creation error: {e.stderr.strip()}"
    except Exception as e:
        return False, f"Training failed: {e}"


if __name__ == "__main__":
    success, msg = train_local_model()
    print("Training Result:", msg)
