import requests
import base64
import json
import sys
import os

from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")


HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}



# ---------------- TOOLS ---------------- #

def create_repo(name):
    url = "https://api.github.com/user/repos"
    data = {"name": name}

    res = requests.post(url, json=data, headers=HEADERS)

    if res.status_code != 201:
        return {"error": res.json()}
    return res.json()


def push_file(repo, path, content, message):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{path}"

    encoded = base64.b64encode(content.encode()).decode()

    data = {
        "message": message,
        "content": encoded
    }

    res = requests.put(url, json=data, headers=HEADERS)

    if res.status_code != 201:
        return {"error": res.json()}
    return res.json()


# ------------- TOOL REGISTRY ------------ #

TOOLS = {
    "create_repo": create_repo,
    "push_file": push_file,
    "list_repos": list_repos,
    "get_file": get_file

}


#list repositories:
def list_repos():
    url = "https://api.github.com/user/repos"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 201:
        return {"error": res.json()}
    return res.json()


#read file from repo

def get_file(repo, path):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 201:
        return {"error": res.json()}
    return res.json()



def handle_request(tool_name, args):
    if tool_name in TOOLS:
        try:
            return TOOLS[tool_name](**args)
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Tool not found"}


# ------------- MCP LOOP ---------------- #

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