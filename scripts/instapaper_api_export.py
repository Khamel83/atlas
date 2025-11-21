import csv
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
INSTAPAPER_USERNAME = os.getenv("INSTAPAPER_USERNAME")
INSTAPAPER_PASSWORD = os.getenv("INSTAPAPER_PASSWORD")
INSTAPAPER_API_BASE = os.getenv(
    "INSTAPAPER_API_BASE", "https://www.instapaper.com/api/1"
)

# --- Paths ---
RAW_DIR = "inputs/instapaper/raw"
CLEAN_DIR = "inputs/instapaper/clean"
HASHES_DIR = "inputs/instapaper/hashes"
HASH_FILE = os.path.join(HASHES_DIR, "instapaper_hashes.txt")


# --- Functions ---
def get_bookmarks():
    """Fetches all bookmarks from the Instapaper API."""
    if not INSTAPAPER_USERNAME or not INSTAPAPER_PASSWORD:
        print("Error: Instapaper username and password not found in .env file.")
        return None

    auth = (INSTAPAPER_USERNAME, INSTAPAPER_PASSWORD)
    url = f"{INSTAPAPER_API_BASE}/bookmarks/list"

    try:
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching bookmarks: {e}")
        return None


def save_raw_data(data):
    """Saves the raw JSON data from the Instapaper API."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"instapaper_full_{timestamp}.json"
    filepath = os.path.join(RAW_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Raw data saved to {filepath}")


def load_seen_hashes():
    """Loads the set of previously seen bookmark hashes."""
    if not os.path.exists(HASH_FILE):
        return set()

    with open(HASH_FILE, "r") as f:
        return {line.strip() for line in f}


def save_new_hashes(hashes):
    """Appends new bookmark hashes to the hash file."""
    with open(HASH_FILE, "a") as f:
        for h in hashes:
            f.write(f"{h}\n")


def process_bookmarks(data):
    """Processes the raw bookmark data, deduplicates it, and saves it to a clean CSV file."""
    seen_hashes = load_seen_hashes()
    new_hashes = set()
    new_bookmarks = []

    for item in data.get("bookmarks", []):
        if item["hash"] not in seen_hashes:
            new_hashes.add(item["hash"])
            new_bookmarks.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "hash": item.get("hash"),
                    "time": datetime.fromtimestamp(item.get("time")).isoformat(),
                    "starred": item.get("starred"),
                    "folder_id": item.get("folder_id"),
                }
            )

    if not new_bookmarks:
        print("No new bookmarks found.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"clean_instapaper_{timestamp}.csv"
    filepath = os.path.join(CLEAN_DIR, filename)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_bookmarks[0].keys())
        writer.writeheader()
        writer.writerows(new_bookmarks)

    print(f"{len(new_bookmarks)} new bookmarks saved to {filepath}")
    save_new_hashes(new_hashes)


if __name__ == "__main__":
    bookmarks = get_bookmarks()
    if bookmarks:
        save_raw_data(bookmarks)
        process_bookmarks(bookmarks)
