import os
import requests
import sys

# Configuration
REPO_OWNER = "fastapi"
REPO_NAME = "fastapi"
BRANCH = "master"
REMOTE_DIR = "docs/en/docs"
LOCAL_DIR = "data/devdocs"

def get_github_tree(session):
    """Fetches the recursive tree of the repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"

    # Use GITHUB_TOKEN if available to increase rate limits
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    print(f"Fetching tree from {url}...")
    response = session.get(url, headers=headers)

    if response.status_code == 403:
        print("Error: GitHub API rate limit exceeded. Please set the GITHUB_TOKEN environment variable.")
        sys.exit(1)
    elif response.status_code != 200:
        print(f"Error fetching tree: {response.status_code} - {response.text}")
        sys.exit(1)

    return response.json().get("tree", [])

def download_file(session, file_path):
    """Downloads a single file via the raw content URL."""
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{file_path}"

    # Determine local path by removing the remote directory prefix
    # e.g., docs/en/docs/tutorial/index.md -> backend/data/devdocs/tutorial/index.md
    relative_path = file_path[len(REMOTE_DIR):].lstrip('/')
    local_path = os.path.join(LOCAL_DIR, relative_path)

    # Create directory structure
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    try:
        response = session.get(url, stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"Failed to download {file_path}: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Network error downloading {file_path}: {e}")
        return False

def main():
    # Ensure the local base directory exists
    os.makedirs(LOCAL_DIR, exist_ok=True)

    with requests.Session() as session:
        tree = get_github_tree(session)

        # Filter for files (blobs) within the target directory, excluding images
        files_to_download = [
            item["path"] for item in tree
            if item["type"] == "blob"
            and item["path"].startswith(REMOTE_DIR)
            and "/img/" not in item["path"]
        ]

        total = len(files_to_download)
        print(f"Found {total} files to download in {REMOTE_DIR}...")

        success_count = 0
        for i, file_path in enumerate(files_to_download, 1):
            print(f"[{i}/{total}] Downloading {file_path}...", end="\r")
            if download_file(session, file_path):
                success_count += 1

        print(f"\nFinished! Successfully downloaded {success_count}/{total} files to {LOCAL_DIR}.")

if __name__ == "__main__":
    main()
