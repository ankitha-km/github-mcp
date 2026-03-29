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
    if isinstance(result, list):
        # ✅ multi-tool results
        if result and "tool" in result[0]:
            for r in result:
                tool = r["tool"]
                res = r["result"]
                if isinstance(res, dict) and res.get("name"):
                    print(f"  ✅ {tool} → {res.get('name')} done")
                elif isinstance(res, dict) and "exists" in res:
                    status = "exists" if res["exists"] else "not found"
                    print(f"  ✅ {tool} → {res['name']} {status}")
                else:
                    print(f"  ✅ {tool} → done")
        else:
            print("Agent: Files found:")
            for f in result:
                print(f"  - {f['name']} ({f['type']}, {f['size']} bytes)")
    elif isinstance(result, dict):
        if result.get("exists") is not None:
            status = "✅ exists" if result["exists"] else "❌ not found"
            print(f"Agent: Repo '{result['name']}' {status}")
        elif "decoded_content" in result:
            print(f"Agent: File content:\n{result['decoded_content']}")
        else:
            print("Agent:", json.dumps(result, indent=2))
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

IMPORTANT RULES:
- If ONE action needed: respond with a single JSON object
  {{"tool": "tool_name", "arguments": {{}}}}

- If MULTIPLE actions needed: respond with a JSON array
  [{{"tool": "tool_name", "arguments": {{}}}}, {{"tool": "tool_name", "arguments": {{}}}}]

- NO extra text, NO explanation — ONLY JSON.
- Use context from previous messages to fill missing details."""
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

    # ✅ Try parsing as JSON (single or list)
    try:
        parsed = json.loads(reply)

        # ✅ If it's a LIST — multi-tool calling!
        if isinstance(parsed, list):
            results = []
            for action in parsed:
                print(f"  calling: {action['tool']} with {action['arguments']}")
                result = call_tool(action["tool"], action["arguments"])
                results.append({"tool": action["tool"], "result": result})
            conversation_history.append({
                "role": "user",
                "content": f"Tool results: {json.dumps(results)[:600]}"
            })
            return results

        # ✅ If it's a single object
        if isinstance(parsed, dict) and "tool" in parsed:
            result = call_tool(parsed["tool"], parsed["arguments"])
            conversation_history.append({
                "role": "user",
                "content": f"Tool result: {json.dumps(result)[:500]}"
            })
            return result

    except:
        pass

    # ✅ Fallback: extract JSON from mixed text
    match = re.search(r'\[.*\]|\{.*"tool".*\}', reply, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                results = []
                for action in parsed:
                    result = call_tool(action["tool"], action["arguments"])
                    results.append({"tool": action["tool"], "result": result})
                return results
            result = call_tool(parsed["tool"], parsed["arguments"])
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