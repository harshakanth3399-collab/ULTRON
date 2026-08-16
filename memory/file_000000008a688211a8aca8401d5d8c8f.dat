import ollama

SYSTEM_PROMPT = """
You are Ultron.

You are Harsha's personal AI assistant.

Rules:
- Calm
- Intelligent
- Friendly
- Concise
- Never rude
"""


def ask_ai(prompt):

    stream = ollama.chat(
        model="qwen2.5:3b",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=True
    )

    answer = ""

    print()

    for chunk in stream:

        part = chunk["message"]["content"]

        print(part, end="", flush=True)

        answer += part

    print()

    return answer.strip()