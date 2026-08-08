import ollama
from modules.memory.profile_manager import get_profile_manager


def get_system_prompt() -> str:
    pm = get_profile_manager()
    return pm.get_system_context()


def ask_ai(prompt: str) -> str:
    system_prompt = get_system_prompt()
    models_to_try = ["ultron-harsha", "qwen2.5:3b", "llama3.2:3b", "phi3:mini", "llama3"]
    
    for model_name in models_to_try:
        try:
            stream = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )

            answer = ""
            print()
            for chunk in stream:
                part = chunk["message"]["content"]
                print(part, end="", flush=True)
                answer += part
            print()

            if answer.strip():
                return answer.strip()

        except Exception as e:
            # Try next model if current fails
            continue

    return "I'm right here with you, Harsha. System is online and ready."