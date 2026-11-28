import os
import requests
from requests.exceptions import HTTPError
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml
import pprint
from db import get_connection, init_db, save_clips
import yt_dlp
from download import get_clips_to_download, download_clip, mark_clip, download_clips

ROOT = Path(__file__).resolve().parents[1]
CREATORS_FILE = ROOT / "config" / "creators.yaml"

# Remove later (move to run.py or config.py)
load_dotenv()

def get_token():
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET missing from .env")

    url = "https://id.twitch.tv/oauth2/token"

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    try:
        res = requests.post(url, data=params, timeout=10)
        res.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except requests.exceptions.RequestException as err:
        print(f"Network or connection error: {err}")
        raise

    data = res.json()
    return data["access_token"]

def get_user_id(token, login):
    client_id = os.getenv("TWITCH_CLIENT_ID")
    url = "https://api.twitch.tv/helix/users"
    headers = {
        "Authorization":  f"Bearer {token}",
        "Client-Id": client_id
    }
    params = {
        "login": login
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except requests.exceptions.RequestException as err:
        print(f"Network or connection error: {err}")
        raise

    data = res.json()

    if not data["data"]:
        raise ValueError(f"No Twitch user called {login}")

    user_id = data["data"][0]["id"]

    return user_id

def get_clips(token, broadcaster_id, hours=24):
    client_id = os.getenv("TWITCH_CLIENT_ID")
    url = "https://api.twitch.tv/helix/clips"
    headers = {
        "Authorization":  f"Bearer {token}",
        "Client-Id": client_id
    }
    now = datetime.now(timezone.utc)
    end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    start_time = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "broadcaster_id": broadcaster_id,
        "started_at": start_time,
        "ended_at": end_time,
        "first": 20
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except requests.exceptions.RequestException as err:
        print(f"Network or connection error: {err}")
        raise

    data = res.json()

    clips = []

    for clip in data["data"]:
        clips.append({
            "title": clip["title"],
            "view_count": clip["view_count"],
            "duration": clip["duration"],
            "vod_offset": clip["vod_offset"],
            "url": clip["url"],
            "video_id": clip["video_id"],
            "id": clip["id"],
            "created_at": clip["created_at"]
        })

    clips.sort(key=lambda c: c["view_count"], reverse=True)

    return clips

def load_creators():
    with open(CREATORS_FILE, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    creators_list = data["creators"]
    active_creators = [c for c in creators_list if c["active"]]
    return active_creators


if __name__ == "__main__":
    token = get_token()
    clips = {}
    creators = load_creators()

    conn = get_connection()
    init_db(conn)

    # get recent clips and save them into db
    for creator in creators:
        try:
            broadcaster_id = get_user_id(token, creator["twitch"])
            creator_clips = get_clips(token, broadcaster_id)
            clips[creator["name"]] = creator_clips

            # save clip details into db
            new = save_clips(conn, creator["name"], creator_clips)
            print(f"{creator["name"]}: {len(creator_clips)} clips, {new} new")
        except (requests.exceptions.RequestException, ValueError) as err:
            print(f"Skipping {creator["name"]}: {err}")

    # lookup clips in db and download them
    download_clips(conn)

    conn.close()
    
    # show the clips
    for name, creator_clips in clips.items():
        print(f"\n=== {name} ({len(creator_clips)} clips) ===")

        if not creator_clips:
            print("  No clips")
            continue

        for c in creator_clips:
            print(f'{c["view_count"]:>7} views | {c["duration"]:>4}s | {c["title"]}')
            print(f'        {c["url"]}')
