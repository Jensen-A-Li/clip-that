import os
import requests
from requests.exceptions import HTTPError
from dotenv import load_dotenv

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
        res = requests.post(url, data=params)
        res.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise
    except requests.exceptions.RequestException as err:
        print(f"Network or connection error: {err}")
        raise

    data = res.json()
    return data["access_token"]

if __name__ == "__main__":
    print(get_token())
    