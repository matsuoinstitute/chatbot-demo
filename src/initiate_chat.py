from openai import OpenAI

from prompt import get_initial_manager_prompt


def initiate_chat(message: str):
    client = OpenAI()
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": get_initial_manager_prompt(),
            },
            {
                "role": "user",
                "content": message
            }
        ],
        model="gpt-4",
    )
    return response.choices[0].message.content
