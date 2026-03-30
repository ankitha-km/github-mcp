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
    
    data = {
        "message": message,
        "content": encoded
    }

    existing = requests.get(url, headers=HEADERS)
    if existing.status_code == 200:
        data["sha"] = existing.json()["sha"]

    res = requests.put(url, json=data, headers=HEADERS)
    
    if res.status_code not in [200, 201]:
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


def rename_file(repo, old_path, new_path, message="renamed file"):
    # get file content + sha first
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{old_path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return {"error": res.json()}
    
    data = res.json()
    content = data["content"]  # already base64
    sha = data["sha"]

    # create new file
    new_url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{new_path}"
    create_res = requests.put(new_url, json={
        "message": message,
        "content": content
    }, headers=HEADERS)
    
    if create_res.status_code != 201:
        return {"error": create_res.json()}

    # delete old file
    delete_res = requests.delete(url, json={
        "message": f"deleted {old_path} after rename",
        "sha": sha
    }, headers=HEADERS)

    return {"renamed": True, "from": old_path, "to": new_path}


def edit_file(repo, path, new_content, message="updated file"):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{path}"
    
    # get current sha
    res = requests.get(url, headers=HEADERS)
    
    # try case-insensitive match if 404
    if res.status_code == 404:
        root = requests.get(
            f"https://api.github.com/repos/{USERNAME}/{repo}/contents/",
            headers=HEADERS
        )
        if root.status_code == 200:
            for f in root.json():
                if f["name"].lower() == path.lower():
                    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{f['name']}"
                    res = requests.get(url, headers=HEADERS)
                    break

    if res.status_code != 200:
        return {"error": res.json()}

    sha = res.json()["sha"]
    encoded = base64.b64encode(new_content.encode()).decode()

    update_res = requests.put(url, json={
        "message": message,
        "content": encoded,
        "sha": sha
    }, headers=HEADERS)

    if update_res.status_code not in [200, 201]:
        return {"error": update_res.json()}

    data = update_res.json()
    return {
        "content": data["content"],
        "commit": data["commit"]
    }


def rename_repo(old_name, new_name):
    url = f"https://api.github.com/repos/{USERNAME}/{old_name}"
    res = requests.patch(url, json={"name": new_name}, headers=HEADERS)
    if res.status_code != 200:
        return {"error": res.json()}
    return {
        "renamed": True,
        "from": old_name,
        "to": new_name,
        "url": res.json()["html_url"]
    }


def delete_file(repo, path, message="deleted file"):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return {"error": res.json()}
    sha = res.json()["sha"]
    delete_res = requests.delete(url, json={
        "message": message,
        "sha": sha
    }, headers=HEADERS)
    if delete_res.status_code != 200:
        return {"error": delete_res.json()}
    return {"deleted": True, "file": path, "repo": repo}


def delete_repo(name):
    url = f"https://api.github.com/repos/{USERNAME}/{name}"
    res = requests.delete(url, headers=HEADERS)
    if res.status_code != 204:
        return {"error": res.json()}
    return {"deleted": True, "repo": name}


def create_branch(repo, branch_name, from_branch="main"):
    # get sha of base branch
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/git/ref/heads/{from_branch}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return {"error": res.json()}
    sha = res.json()["object"]["sha"]

    # create new branch
    create_url = f"https://api.github.com/repos/{USERNAME}/{repo}/git/refs"
    create_res = requests.post(create_url, json={
        "ref": f"refs/heads/{branch_name}",
        "sha": sha
    }, headers=HEADERS)
    if create_res.status_code != 201:
        return {"error": create_res.json()}
    return {
        "created": True,
        "branch": branch_name,
        "repo": repo,
        "from": from_branch
    }



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
    "list_files": list_files,  
    "rename_file": rename_file,  
    "edit_file": edit_file,       
    "rename_repo": rename_repo,
    "delete_file": delete_file,
    "delete_repo": delete_repo,
    "create_branch": create_branch
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