"""Instant 'skills' Jarvis handles without calling an LLM.

Each skill returns {"text": reply, "action": optional browser action} or None.
Browser actions are executed by jarvis.html, never by the server, so nothing
on the host machine is ever launched remotely.
"""
import os
import re
from datetime import datetime
from urllib.parse import quote_plus

import requests

SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "maps": "https://maps.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "linkedin": "https://www.linkedin.com",
    "spotify": "https://open.spotify.com",
    "calendar": "https://calendar.google.com",
}
UNITS = {"second": 1, "sec": 1, "minute": 60, "min": 60, "hour": 3600}


def _time(t):
    if re.search(r"\bwhat('?s| is)? the time\b|\bcurrent time\b|\btime now\b", t):
        return {"text": datetime.now().strftime("It's %I:%M %p.")}
    if re.search(r"\b(today'?s )?date\b|\bwhat day\b", t):
        return {"text": datetime.now().strftime("Today is %A, %d %B %Y.")}


def _weather(t):
    m = re.search(r"weather (?:in|at|for) ([a-z ]+)", t)
    if not m:
        return None
    city = m.group(1).strip()
    key = os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")
    if not key:
        return {"text": "My weather feed has no API key yet."}
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": key, "units": "metric"},
            timeout=8,
        )
        j = r.json()
        if r.status_code != 200:
            return {"text": f"I couldn't find weather for {city}."}
        return {"text": f"{city.title()}: {j['weather'][0]['description']}, "
                        f"{round(j['main']['temp'])} degrees, feels like "
                        f"{round(j['main']['feels_like'])}."}
    except requests.RequestException:
        return {"text": "The weather service isn't responding right now."}


def _open(t):
    m = re.search(r"\b(?:open|launch|go to)\s+([a-z]+)", t)
    if m and m.group(1) in SITES:
        name = m.group(1)
        return {"text": f"Opening {name}.", "action": {"type": "open_url", "url": SITES[name]}}


def _search(t):
    m = re.search(r"\b(?:search|google|look up)(?: for)?\s+(.+)", t)
    if m:
        q = m.group(1).strip()
        return {"text": f"Searching for {q}.",
                "action": {"type": "open_url", "url": "https://www.google.com/search?q=" + quote_plus(q)}}


def _timer(t):
    m = re.search(r"(?:timer|remind me).*?(\d+)\s*(second|sec|minute|min|hour)", t)
    if m:
        secs = int(m.group(1)) * UNITS[m.group(2)]
        return {"text": f"Timer set for {m.group(1)} {m.group(2)}{'s' if m.group(1) != '1' else ''}.",
                "action": {"type": "timer", "seconds": secs}}


SKILLS = [_time, _weather, _open, _search, _timer]


def run(text):
    t = text.lower().strip()
    for skill in SKILLS:
        res = skill(t)
        if res:
            return res
    return None
