import subprocess
import json
import os
import re
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

conversation_history = []

def call_tool(tool_name, args):
    request = {"tool": tool_name, "arguments": args}
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())

def pretty_print(result):
    if isinstance(result, dict):
        if result.get("exists") is not None:
            status = "✅ exists" if result["exists"] else "❌ not found"
            print(f"Agent: Repo '{result['name']}' {status}")
        elif "decoded_content" in result:
            print(f"Agent: File content:\n{result['decoded_content']}")
        else:
            print("Agent:", json.dumps(result, indent=2))
    elif isinstance(result, list):
        print("Agent: Files found:")
        for f in result:
            print(f"  - {f['name']} ({f['type']}, {f['size']} bytes)")
    else:
        print("Agent:", result)

def run_agent(user_message):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
IMPORTANT: When you need to call a tool, respond with ONLY a JSON object — no explanation, no extra text.
Just the raw JSON like: {{"tool": "tool_name", "arguments": {{}}}}
Only respond in plain text if no tool is needed."""
            },
            *conversation_history
        ]
    )

    reply = response.choices[0].message.content.strip()
    print("LLM picked:", reply)

    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    # Try direct JSON parse
    try:
        action = json.loads(reply)
        result = call_tool(action["tool"], action["arguments"])
        conversation_history.append({
            "role": "user",
            "content": f"Tool result: {json.dumps(result)[:500]}"
        })
        return result
    except:
        pass

    # Fallback: extract JSON from mixed text
    match = re.search(r'\{.*"tool".*\}', reply, re.DOTALL)
    if match:
        try:
            action = json.loads(match.group())
            result = call_tool(action["tool"], action["arguments"])
            conversation_history.append({
                "role": "user",
                "content": f"Tool result: {json.dumps(result)[:500]}"
            })
            return result
        except Exception as e:
            print("Error:", e)

    return reply

# ✅ Simple chat loop — NO sys.stdin, NO main()
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
    pretty_print(result)