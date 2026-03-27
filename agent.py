import subprocess
import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

with open("tools.json") as f:
    tools_schema = json.load(f)

process = subprocess.Popen(
    ["python", "server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

# ✅ Memory — stores full conversation history
conversation_history = []

def call_tool(tool_name, args):
    request = {"tool": tool_name, "arguments": args}
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())

def run_agent(user_message):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # ✅ Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are an assistant that manages GitHub repos.
You have access to these tools: {json.dumps(tools_schema)}
When the user asks something, respond ONLY with a JSON object like:
{{"tool": "tool_name", "arguments": {{}}}}
If no tool is needed, respond normally in plain text.
Use context from previous messages to fill in missing details.
For example if user says 'push a file to it', figure out which repo from history."""
            },
            *conversation_history  # ✅ send full history every time
        ]
    )

    reply = response.choices[0].message.content.strip()
    print("LLM picked:", reply)

    # ✅ Add assistant reply to history
    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    try:
        action = json.loads(reply)
        result = call_tool(action["tool"], action["arguments"])

        # ✅ Also store the tool result so LLM knows what happened
        conversation_history.append({
            "role": "user",
            "content": f"Tool result: {json.dumps(result)[:500]}"  # truncate to avoid huge history
        })

        return result
    except Exception as e:
        return reply

print("Agent ready! Type 'exit' to quit, 'history' to see memory.\n")

while True:
    user_input = input("\nYou: ")

    if user_input.lower() == "exit":
        break

    if user_input.lower() == "history":
        print("\n--- Conversation Memory ---")
        for msg in conversation_history:
            print(f"[{msg['role']}]: {msg['content'][:100]}")
        continue

    result = run_agent(user_input)
    print("Agent:", json.dumps(result, indent=2) if isinstance(result, dict) else result)