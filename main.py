#!/usr/bin/env python3
import os
import json
import subprocess
import shutil
from pathlib import Path
from sys import exit

PLAYLIST_URL = ""
DB_PATH = Path.home() / ".youtube" / "database.json"
MUSIC_DIR = Path("""Final output path""")
TMP_DIR = Path.home() / "tmp"
MAX_ITEMS = 10

TMP_OUT = TMP_DIR / "%(title)s.%(ext)s"
YTDLP_OPTS = [
    "yt-dlp",
    "--extract-audio",
    "--audio-format", "mp3",
    "--audio-quality", "128K",
    "-o", str(TMP_OUT),
    "--quiet",
    "--no-warnings"
]

def load_db():
    if DB_PATH.exists():
        with open(DB_PATH, "r") as f:
            return json.load(f)
    else:
        return {"entries": []}

def save_db(db):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)

def fetch_playlist_entries():
    try:
        cmd = ["yt-dlp", "--flat-playlist", "-J", PLAYLIST_URL]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        data = json.loads(output)
        return data.get("entries", [])[:MAX_ITEMS]
    except Exception as e:
        print(f"[!] Critical Error fetching playlist: {e}")
        exit(1)

def main():
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    db = load_db()
    seen = {e["id"]: e for e in db["entries"]}

    print("[*] Fetching playlist...")
    entries = fetch_playlist_entries()

    new_db_entries = []
    for e in entries:
        vid_id = e["id"]
        title = e.get("title", "")
        downloaded = seen.get(vid_id, {}).get("downloaded", False)
        new_db_entries.append({
            "id": vid_id,
            "title": title,
            "downloaded": downloaded
        })

    db["entries"] = new_db_entries
    save_db(db)

    to_download = [e for e in db["entries"] if not e["downloaded"]]
    if not to_download:
        print("[*] All up to date.")
        TMP_DIR.rmdir()
        exit(0)

    for entry in to_download:
        url = f"https://youtu.be/{entry['id']}"
        print(f"[+] Downloading: {entry['title']} ({entry['id']})")
        try:
            subprocess.check_call(YTDLP_OPTS + [url], stderr=subprocess.DEVNULL)
            tmp_file = next(TMP_DIR.glob(f"{entry['title']}*.mp3"), None)
            if tmp_file and tmp_file.exists():
                dest_file = MUSIC_DIR / tmp_file.name
                shutil.move(str(tmp_file), str(dest_file))
                print(f"[+] Moved to: {dest_file}")
                entry["downloaded"] = True
                save_db(db)
            else:
                print(f"[!] File not found in tmp: {entry['title']}")

        except subprocess.CalledProcessError:
            print(f"[!] Failed to download {entry['id']}")
    try:
        TMP_DIR.rmdir()
        print("[*] Cleanup complete.")
    except OSError:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("[*] Force cleanup complete.")

    print("[*] Done.")
    exit(0)

if __name__ == "__main__":
    main()
