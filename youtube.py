import datetime
import feedparser
import logging
import re
import requests
from bs4 import BeautifulSoup

import os, json

def get_channel_id_from_url(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        return f"❌ Error loading page: {e}"

    # Try to find channelId in the HTML source
    match = re.search(r'"channelId":"(UC[\w-]{22})"', response.text)
    if match:
        return match.group(1)

    return None

# ==== 🔧 Example URLs you can test ====
# url = "https://www.youtube.com/watch?v=Hs8CzJ0Rz1M"
# url = "https://www.youtube.com/shorts/FZrmYVWo5X4"
# url = "https://www.youtube.com/@MrBeast"
# url = "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw"


import requests
from xml.etree import ElementTree as ET

def get_channel_name_from_rss(channel_id):
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        response = requests.get(rss_url)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        title_tag = root.find('{http://www.w3.org/2005/Atom}title')
        
        if title_tag is not None:
            return (title_tag.text).strip()
        else:
            return channel_id

    except Exception as e:
        return (None, f"❌ Error fetching RSS feed: {e}")

import json
import os

import json
import os

def append_channel_to_json_file(channel_info, alias=None, filename="channels.json", force=False):
    alias = str(alias or channel_info["channel_name"])  # fallback to channel_name if alias not given

    data = {}

    # Load existing JSON
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return "⚠️ JSON is broken. Starting fresh."

    # Check if alias exists
    if alias in data and not force:
        return f"⚠️ Alias '{alias}' already exists." # Use force=True to overwrite.

    # Check if channel_id already exists
    for existing_alias, ch in data.items():
        if ch.get("channel_id") == channel_info["channel_id"]:
            return f"⚠️ Channel ID already exists under alias '{existing_alias}'." 
            

    # Add or overwrite
    data[alias] = channel_info

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return f"✅ Channel saved under alias: {alias}"


def latest_video(rss_url):
    feed = feedparser.parse(rss_url)
    latest_video = feed.entries[0]
    date_published = datetime.datetime(*latest_video['published_parsed'][:6]).strftime('%Y-%m-%d')
    video_id = latest_video['yt_videoid']
    return video_id, date_published