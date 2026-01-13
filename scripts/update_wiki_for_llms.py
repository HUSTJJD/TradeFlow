import urllib.request
import os

SAVE_DIR = "llms"
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fetch_and_update_longbridge_wiki():
    url = "https://open.longbridge.com/llms.txt"
    wiki_path = os.path.join(
        ROOT_DIR,
        SAVE_DIR,
        "Longbridge_LLMs.md",
    )
    with urllib.request.urlopen(url) as response:
        content = response.read().decode("utf-8")

    print(f"Updating {wiki_path}...")
    with open(wiki_path, "w", encoding="utf-8") as f:
        f.write(content)


def fetch_and_update_akshare_wiki():
    url = "https://akshare.akfamily.xyz/"
    wiki_path = os.path.join(
        ROOT_DIR,
        SAVE_DIR,
        "AkShare_LLMs.md"
    )
    content = f"DOC: {url}"
    print(f"Updating {wiki_path}...")
    with open(wiki_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    fetch_and_update_longbridge_wiki()
    fetch_and_update_akshare_wiki()
