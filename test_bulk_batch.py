#bulk automation script  for terminal version
import subprocess
import json

process = subprocess.Popen(
    ["python", "server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

def call_tool(tool_name, args):
    request = {"tool": tool_name, "arguments": args}
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())

# ✅ Create 10 repos at once
repos = ["project-1", "project-2", "project-3", "project-4", "project-5",
         "project-6", "project-7", "project-8", "project-9", "project-10"]

for repo in repos:
    result = call_tool("create_repo", {"name": repo})
    if "error" in result:
        print(f"❌ {repo}: {result['error']}")
    else:
        print(f"✅ {repo} created — {result['html_url']}")


files_to_push = [
    {"repo": "project-1", "path": "README.md", "content": "# Project 1", "message": "init"},
    {"repo": "project-2", "path": "README.md", "content": "# Project 2", "message": "init"},
    {"repo": "project-3", "path": "README.md", "content": "# Project 3", "message": "init"},
]

for f in files_to_push:
    result = call_tool("push_file", f)
    if "error" in result:
        print(f"❌ {f['repo']}: {result['error']}")
    else:
        print(f"✅ pushed {f['path']} to {f['repo']}")




projects = ["ai-notes", "ml-experiments", "data-pipeline"]

for name in projects:
    # create repo
    r = call_tool("create_repo", {"name": name})
    print(f"✅ created {name}")

    # immediately push a README
    call_tool("push_file", {
        "repo": name,
        "path": "README.md",
        "content": f"# {name}\nCreated automatically by MCP agent.",
        "message": "initial commit"
    })
    print(f"✅ pushed README to {name}")