from flask import Flask, request, jsonify, render_template_string
import subprocess
import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)

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
    request_data = {"tool": tool_name, "arguments": args}
    process.stdin.write(json.dumps(request_data) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())

def run_agent(user_message):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    conversation_history.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are an assistant that manages GitHub repos.
You have access to these tools: {json.dumps(tools_schema)}
IMPORTANT RULES:
- Use the EXACT repo name the user typed — never guess, correct, or substitute it.
- If ONE action needed: {{"tool": "tool_name", "arguments": {{}}}}
- If MULTIPLE actions needed: [{{"tool": "t1", "arguments": {{}}}}, {{"tool": "t2", "arguments": {{}}}}]
- NEVER put each JSON on a separate line — always use a single array.
- When editing a file, pass ONLY the new content the user specified — never add extra characters.
- NO extra text — ONLY JSON. Only plain text if no tool needed."""
            },
            *conversation_history
        ]
    )

    reply = response.choices[0].message.content.strip()
    conversation_history.append({"role": "assistant", "content": reply})

    # parse single or multi tool
    try:
        parsed = json.loads(reply)
        if isinstance(parsed, list):
            results = []
            for action in parsed:
                result = call_tool(action["tool"], action["arguments"])
                results.append({"tool": action["tool"], "result": result})
            conversation_history.append({"role": "user", "content": f"Tool results: {json.dumps(results)[:600]}"})
            return format_results(results)
        if isinstance(parsed, dict) and "tool" in parsed:
            result = call_tool(parsed["tool"], parsed["arguments"])
            conversation_history.append({"role": "user", "content": f"Tool result: {json.dumps(result)[:500]}"})
            return format_result(parsed["tool"], result)
    except:
        pass

    # fallback: extract JSON
    match = re.search(r'\[.*\]|\{.*"tool".*\}', reply, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                results = []
                for action in parsed:
                    result = call_tool(action["tool"], action["arguments"])
                    results.append({"tool": action["tool"], "result": result})
                return format_results(results)
            result = call_tool(parsed["tool"], parsed["arguments"])
            return format_result(parsed["tool"], result)
        except:
            pass

    # fallback: newline separated
    lines = [l.strip() for l in reply.strip().split('\n') if l.strip().startswith('{')]
    if len(lines) > 1:
        results = []
        for line in lines:
            try:
                action = json.loads(line)
                if "tool" in action:
                    result = call_tool(action["tool"], action["arguments"])
                    results.append({"tool": action["tool"], "result": result})
            except:
                continue
        if results:
            return format_results(results)

    return reply

def format_result(tool, result):
    if isinstance(result, dict):
        if result.get("exists") is True:
            return f"✅ Repo **{result['name']}** exists — {result.get('url', '')}"
        if result.get("exists") is False:
            return f"❌ Repo **{result['name']}** not found"
        if "decoded_content" in result:
            return f"📄 **{result.get('name', 'file')}**:\n```\n{result['decoded_content']}\n```"
        if result.get("renamed") is True:
            if "url" in result:
                return f"✅ Repo renamed from **{result['from']}** to **{result['to']}** — {result['url']}"
            return f"✅ File renamed from **{result['from']}** to **{result['to']}**"
        if result.get("deleted") is True:        # ✅ moved here inside dict block
            if "file" in result:
                return f"🗑️ File **{result['file']}** deleted from **{result['repo']}**"
            return f"🗑️ Repo **{result['repo']}** deleted permanently"
        if result.get("created") is True and "branch" in result:   # ✅ moved here
            return f"🌿 Branch **{result['branch']}** created in **{result['repo']}** from **{result['from']}**"
        if "content" in result and "commit" in result:
            name = result["content"]["name"]
            url = result["content"]["html_url"]
            sha = result["commit"]["sha"][:7]
            return f"✅ **{name}** pushed successfully! [view on GitHub]({url}) — commit `{sha}`"
        if "html_url" in result:
            return f"✅ Done! [{result['name']}]({result['html_url']})"
        if "error" in result:
            return f"❌ Error: {result['error']}"
    if isinstance(result, list):
        lines = "\n".join([f"- {f['name']} ({f['size']} bytes)" for f in result])
        return f"📁 Files:\n{lines}"
    return str(result)

def format_results(results):
    lines = []
    for r in results:
        lines.append(format_result(r["tool"], r["result"]))
    return "\n".join(lines)


HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>GitHub MCP Agent</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #0d1117; color: #e6edf3; height: 100vh; display: flex; flex-direction: column; }
    header { padding: 16px 24px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; align-items: center; gap: 10px; }
    header h1 { font-size: 16px; font-weight: 600; }
    .badge { background: #238636; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 10px; }
    #chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
    .msg { max-width: 75%; padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
    .user { align-self: flex-end; background: #1f6feb; color: #fff; border-radius: 12px 12px 2px 12px; }
    .agent { align-self: flex-start; background: #161b22; border: 1px solid #30363d; border-radius: 12px 12px 12px 2px; }
    .agent a { color: #58a6ff; }
    footer { padding: 16px 24px; background: #161b22; border-top: 1px solid #30363d; display: flex; gap: 10px; }
    #input { flex: 1; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; color: #e6edf3; font-size: 14px; outline: none; }
    #input:focus { border-color: #58a6ff; }
    #send { background: #238636; color: #fff; border: none; border-radius: 8px; padding: 10px 20px; font-size: 14px; cursor: pointer; }
    #send:hover { background: #2ea043; }
    .typing { align-self: flex-start; color: #8b949e; font-size: 13px; }
    .quick { display: flex; gap: 8px; flex-wrap: wrap; padding: 8px 24px 12px; }   
    .quick button { background: #161b22; border: 1px solid #30363d; color: #8b949e; border-radius: 16px; padding: 4px 12px; font-size: 12px; cursor: pointer; }
    .quick button:hover { border-color: #58a6ff; color: #58a6ff; }
    #upload-panel { display: none; }
    #upload-panel.open { display: flex !important; }
  </style>
</head>
<body>
  <header>
    <span style="font-size:20px">⚡</span>
    <h1>GitHub MCP Agent</h1>
    <span class="badge">live</span>
  </header>

  <div id="chat">
    <div class="msg agent">Hey! I'm your GitHub agent. Ask me anything — create repos, push files, list your projects...</div>
  </div>

<div class="quick">
  <button onclick="send('list all my repos')">list repos</button>
  <button onclick="send('create a repo called test-web')">create repo</button>
  <button onclick="send('check if test-repo exists')">check repo</button>
  <button onclick="send('list files in github-mcp')">list files</button>
  <button onclick="toggleUpload()">upload file</button>

</div>


<div id="upload-panel" style="padding: 10px 24px; background:#161b22; border-top: 1px solid #30363d; border-bottom: 1px solid #30363d; flex-direction: row; gap: 8px; align-items: center; flex-wrap: wrap;">
  <input type="text" id="upload-repo" placeholder="repo name e.g. github-mcp"
    style="background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:8px 12px; color:#e6edf3; font-size:13px; width:200px; outline:none;"/>
  <input type="file" id="upload-file" multiple
    style="color:#8b949e; font-size:13px;"/>
  <button onclick="uploadFiles()"
    style="background:#238636; color:#fff; border:none; border-radius:8px; padding:8px 16px; font-size:13px; cursor:pointer;">
    Push to GitHub
  </button>
  <button onclick="toggleUpload()"
    style="background:transparent; color:#8b949e; border:1px solid #30363d; border-radius:8px; padding:8px 12px; font-size:13px; cursor:pointer;">
    cancel
  </button>
</div>

  <footer>
    <input id="input" placeholder="Ask me anything about your GitHub repos..." onkeydown="if(event.key==='Enter') send()"/>
    <button id="send" onclick="send()">Send</button>
  </footer>

<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('input');

  function addMsg(text, role) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
                        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
                        .replace(/```([\s\S]*?)```/g, '<code style="background:#0d1117;padding:4px 8px;border-radius:4px;display:block;margin-top:6px">$1</code>');
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function addTyping() {
    const div = document.createElement('div');
    div.className = 'typing';
    div.id = 'typing';
    div.textContent = 'Agent is thinking...';
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function toggleUpload() {
    const panel = document.getElementById('upload-panel');
    panel.classList.toggle('open');
  }

  async function send(text) {
    const msg = text || input.value.trim();
    if (!msg) return;
    input.value = '';
    addMsg(msg, 'user');
    addTyping();

    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });
    const data = await res.json();
    document.getElementById('typing')?.remove();
    addMsg(data.reply, 'agent');
  }

  async function uploadFiles() {
  const repo = document.getElementById('upload-repo').value.trim();
  const files = document.getElementById('upload-file').files;

  if (!repo) { addMsg('❌ Please enter a repo name', 'agent'); return; }
  if (files.length === 0) { addMsg('❌ Please select files', 'agent'); return; }

  toggleUpload();
  addMsg(`Uploading ${files.length} file(s) to ${repo}...`, 'user');
  addTyping();

  const formData = new FormData();
  formData.append('repo', repo);
  for (const file of files) {
    formData.append('files', file, file.webkitRelativePath || file.name);
  }

  const res = await fetch('/upload-folder', {
    method: 'POST',
    body: formData
  });
  const data = await res.json();
  document.getElementById('typing')?.remove();
  data.results.forEach(r => addMsg(r, 'agent'));
}



</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    reply = run_agent(user_message)
    return jsonify({"reply": reply})


@app.route('/upload-folder', methods=['POST'])
def upload_folder():
    repo = request.form.get('repo')
    files = request.files.getlist('files')

    if not files or not repo:
        return jsonify({"results": ["❌ Missing files or repo name"]})

    results = []
    for file in files:
        filename = file.filename
        content = file.read().decode('utf-8', errors='replace')
        result = call_tool("push_file", {
            "repo": repo,
            "path": filename,
            "content": content,
            "message": f"uploaded {filename} via MCP agent"
        })
        results.append(format_result("push_file", result))

    return jsonify({"results": results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)