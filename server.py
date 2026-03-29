import requests
import base64
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def create_repo(name):
    url = "https://api.github.com/user/repos"
    res = requests.post(url, json={"name": name}, headers=HEADERS)
    if res.status_code != 201:
        return {"error": res.json()}
    return res.json()

def push_file(repo, path, content, message):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{path}"
    encoded = base64.b64encode(content.encode()).decode()
    res = requests.put(url, json={"message": message, "content": encoded}, headers=HEADERS)
    if res.status_code != 201:
        return {"error": res.json()}
    return res.json()

def check_repo(name):
    url = f"https://api.github.com/repos/{USERNAME}/{name}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        data = res.json()
        return {"exists": True, "name": name, "url": data["html_url"], "private": data["private"], "language": data["language"]}
    elif res.status_code == 404:
        return {"exists": False, "name": name, "message": "Repo not found"}
    return {"error": res.json()}

def list_repos():
    url = "https://api.github.com/user/repos"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:   # ✅ fixed
        return {"error": res.json()}
    return res.json()

def get_file(repo, path):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    
    if res.status_code == 404 and path:
        root_url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/"
        root_res = requests.get(root_url, headers=HEADERS)
        
        if root_res.status_code == 200:
            files = root_res.json()
            for f in files:
                if f["name"].lower() == path.lower():
                    correct_url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{f['name']}"
                    res = requests.get(correct_url, headers=HEADERS)
                    break
            else:
                
                return [{"name": f["name"], "type": f["type"], "size": f["size"]} for f in files]

    if res.status_code != 200:
        return {"error": res.json()}

    data = res.json()

    
    if isinstance(data, list):
        return [{"name": f["name"], "type": f["type"], "size": f["size"]} for f in data]

    
    if "content" in data:
        data["decoded_content"] = base64.b64decode(data["content"]).decode("utf-8")

    return data







def list_files(repo, path=""):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return {"error": res.json()}
    files = res.json()
    return [{"name": f["name"], "type": f["type"], "size": f["size"]} for f in files]

TOOLS = {
    "create_repo": create_repo,
    "push_file": push_file,
    "check_repo": check_repo,
    "list_repos": list_repos,
    "get_file": get_file,
    "list_files": list_files    # ✅ added
}

def handle_request(tool_name, args):
    if tool_name in TOOLS:
        try:
            return TOOLS[tool_name](**args)
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Tool not found"}

def main():
    for line in sys.stdin:
        try:
            request = json.loads(line)
            tool = request.get("tool")
            args = request.get("arguments", {})
            result = handle_request(tool, args)
            print(json.dumps(result))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()

if __name__ == "__main__":
    main()