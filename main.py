import os
import json
import requests
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT
from memory import load_memory, save_memory
from tools import TOOL_FUNCTIONS

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

API_KEY_ERROR_MESSAGE = (
    "OPENROUTER_API_KEY is missing. Create a .env file (see .env.example) "
    "and put your key in it."
)

MODEL = "openai/gpt-4o-mini"

URL = "https://openrouter.ai/api/v1/chat/completions"

# Set to True to print raw API responses / tool calls while debugging
DEBUG = False

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather of any city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_history",
            "description": (
                "Get historical weather for a city over a past period "
                "(e.g. last week, last month): average/min/max temperature, "
                "total rainfall, and a day-by-day breakdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name"
                    },
                    "days": {
                        "type": "integer",
                        "description": "How many past days to cover. Use 7 for "
                                        "'last week', 30 for 'last month'. Defaults to 30."
                    }
                },
                "required": ["city"]
            }
        }
    }
]


# -----------------------------
# LLM CALL
# -----------------------------
def call_llm(messages):
    if not API_KEY:
        raise RuntimeError(API_KEY_ERROR_MESSAGE)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Weather Agent"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto"
    }

    response = requests.post(URL, headers=headers, json=payload)

    if DEBUG:
        print("\n========== RAW RESPONSE ==========")
        print(response.status_code)
        print(response.text)
        print("==================================\n")

    response.raise_for_status()

    return response.json()


# -----------------------------
# RUN TOOL
# -----------------------------
def run_tool(tool_call):

    if DEBUG:
        print("\nTool Call:")
        print(json.dumps(tool_call, indent=2))

    tool_name = tool_call["function"]["name"]
    args = tool_call["function"].get("arguments", "{}")

    try:
        arguments = json.loads(args)
    except json.JSONDecodeError as e:
        if DEBUG:
            print("JSON Error:", e)
        arguments = {}

    if tool_name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[tool_name](**arguments)

    return {"error": f"Tool '{tool_name}' not found"}


# -----------------------------
# AGENT LOOP
# -----------------------------
def weather_agent(user_input):
    if not API_KEY:
        return API_KEY_ERROR_MESSAGE

    memory = load_memory()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(memory)

    messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    for _ in range(5):

        response = call_llm(messages)
        message = response["choices"][0]["message"]

        messages.append(message)

        tool_calls = message.get("tool_calls", [])

        if tool_calls:

            for tool_call in tool_calls:

                result = run_tool(tool_call)

                if DEBUG:
                    print("Tool Result:", result)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "content": json.dumps(result)
                    }
                )

        else:
            # NOTE: message.get("content", default) only falls back when the
            # key is MISSING, not when it's present but set to None (which
            # some models do when they finish reasoning without real text).
            # So we check explicitly instead of relying on the .get() default.
            answer = message.get("content")
            if not answer:
                answer = message.get("reasoning") or "No response generated."

            save_memory(messages[1:])
            return answer

    return "Maximum iterations reached."


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    print("\n🌤  Weather Agent Started. Type 'exit' to stop.\n")

    while True:

        user = input("You : ")

        if user.lower() == "exit":
            print("Goodbye!")
            break

        try:
            answer = weather_agent(user)
            print("\nAgent :", answer, "\n")
        except Exception as e:
            print("\nERROR:", e, "\n")
