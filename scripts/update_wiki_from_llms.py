import urllib.request
import os

def fetch_and_update_wiki():
    url = "https://open.longbridge.com/llms.txt"
    wiki_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "LLMsWiki.md")
    
    print(f"Downloading from {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
            
        print(f"Updating {wiki_path}...")
        with open(wiki_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("Wiki.md updated successfully.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_update_wiki()