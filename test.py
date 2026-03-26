import subprocess
import json

process = subprocess.Popen(
    ["python", "server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

request = {
    "tool": "create_repo",
    "arguments": {"name": "mcp-test"}
}

process.stdin.write(json.dumps(request) + "\n")
process.stdin.flush()

response = process.stdout.readline()
print("Response:", response)