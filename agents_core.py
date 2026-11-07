"""Intent detection and the task / event / note / memory agents (SQLite, stdlib only).

Every handler takes (user_id, text) and returns a short, speakable string.
Data lives in aura.db next to this file.
"""
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aura.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, text TEXT, done INTEGER DEFAULT 0, created TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, title TEXT, when_text TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, text TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, user_input TEXT, intent TEXT, emotion TEXT, created TEXT);
"""


def _q(sql, args=(), write=False):
    with closing(sqlite3.connect(DB)) as con:
        con.row_factory = sqlite3.Row
        con.executescript(_SCHEMA)
        cur = con.execute(sql, args)
        if write:
            con.commit()
            return cur.lastrowid if cur.lastrowid else cur.rowcount
        return cur.fetchall()


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- helpers
LEAD = r"^(?:(?:hey |ok |okay )?jarvis[,\s]+)?(?:please\s+|can you\s+|could you\s+)?"
LIST_START = r"^(?:show|list|read|what|whats|what's|view|display|do i have|how many|tell me)\b"


def _strip_lead(text):
    return re.sub(LEAD, "", text.strip(), flags=re.I).strip()


def _clean(text, nouns):
    """Remove 'add a task to ...' style scaffolding and keep the actual content."""
    t = _strip_lead(text)
    t = re.sub(r"^(?:add|create|make|set|new|take|write|save|put|schedule|book|remember|jot)\s+(?:down\s+)?"
               r"(?:a |an |the |my |new )*(?:%s)?\s*(?:to|for|that|about|called|named|:|,|-)?\s+" % nouns,
               "", t + " ", flags=re.I)
    t = re.sub(r"^(?:%s)\s*[:,-]?\s*" % nouns, "", t.strip(), flags=re.I)
    t = re.sub(r"\s+(?:to|in|on|into)\s+(?:my\s+)?(?:%s)(?:\s+list)?$" % nouns, "", t, flags=re.I)
    return t.strip(" .")


def _number(t):
    m = re.search(r"\b(\d+)\b", t)
    return int(m.group(1)) if m else None


def _delete(table, uid, t, label):
    n = _number(t)
    if re.search(r"\ball\b", t):
        _q(f"DELETE FROM {table} WHERE user_id=?", (uid,), write=True)
        return f"All your {label}s are cleared."
    if n is None:
        return f"Which {label} number should I remove?"
    gone = _q(f"DELETE FROM {table} WHERE id=? AND user_id=?", (n, uid), write=True)
    return f"{label.capitalize()} {n} removed." if gone else f"I couldn't find {label} {n}."


# ---------------------------------------------------------------- intent
def detect_intent(text):
    t = text.lower()
    if re.search(r"\b(task|tasks|todo|to-do|to do)\b", t):
        return "task"
    if re.search(r"\b(note|notes|jot|remember that|write down)\b", t):
        return "note"
    if re.search(r"\b(event|events|meeting|meetings|appointment|appointments|schedule|calendar)\b", t):
        return "event"
    return "chat"


# ---------------------------------------------------------------- tasks
def handle_task(user_id, text):
    uid, t = str(user_id), _strip_lead(text).lower()
    if re.search(r"\b(delete|remove|clear|cancel)\b", t):
        return _delete("tasks", uid, t, "task")
    if re.search(r"\b(add|create|make)\b", t):
        item = _clean(text, "tasks?|to-?do|to do")
        if not item:
            return "What should the task be?"
        _q("INSERT INTO tasks(user_id,text,created) VALUES(?,?,?)", (uid, item, _now()), write=True)
        return f"Task added: {item}."
    if not re.match(LIST_START, t) and re.search(r"\b(done|complete|completed|finish|finished|mark|tick)\b", t):
        n = _number(t)
        rows = _q("SELECT * FROM tasks WHERE user_id=? AND done=0", (uid,))
        if n is None:
            words = {w for w in re.findall(r"[a-z]+", t) if len(w) > 2}
            best = max(rows, key=lambda r: len(words & set(re.findall(r"[a-z]+", r["text"].lower()))), default=None)
            if best and words & set(re.findall(r"[a-z]+", best["text"].lower())):
                n = best["id"]
        if n is None:
            return "Which task number is done?"
        ok = _q("UPDATE tasks SET done=1 WHERE id=? AND user_id=?", (n, uid), write=True)
        return f"Marked task {n} as done." if ok else f"I couldn't find task {n}."
    rows = _q("SELECT * FROM tasks WHERE user_id=? AND done=0 ORDER BY id", (uid,))
    if not rows:
        return "You have no pending tasks."
    shown = ". ".join(f"Task {r['id']}: {r['text']}" for r in rows[:5])
    more = f", and {len(rows) - 5} more" if len(rows) > 5 else ""
    return f"You have {len(rows)} pending task{'s' if len(rows) != 1 else ''}. {shown}{more}."


# ---------------------------------------------------------------- events
DAYS = (r"day after tomorrow|today|tomorrow|tonight|"
        r"(?:next |this )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)")
TIME = r"(?:at|by)\s+\d{1,2}(?::\d{2})?\s*(?:[ap]\.?m\.?)?"


def handle_event(user_id, text):
    uid, t = str(user_id), _strip_lead(text).lower()
    if re.search(r"\b(cancel|delete|remove)\b", t):
        return _delete("events", uid, t, "event")
    if re.search(r"\b(add|create|book|set up|put|new)\b", t) or t.startswith("schedule"):
        title = re.sub(r"^(?:add|create|schedule|book|set up|set|put|new)\s+(?:a |an |the |my )*(?:new )?"
                       r"(?:calendar )?(?:event )?(?:called |named |for |: )?", "", _strip_lead(text), flags=re.I)
        day = re.search(DAYS, title, re.I)
        tm = re.search(TIME, title, re.I)
        when = " ".join(x.group(0) for x in (day, tm) if x)
        for x in (day, tm):
            if x:
                title = title.replace(x.group(0), " ")
        title = re.sub(r"\s+(?:on|at|by)\s*$", "", re.sub(r"\s+", " ", title).strip(" .,"), flags=re.I)
        if not title:
            return "What should I call the event?"
        _q("INSERT INTO events(user_id,title,when_text,created) VALUES(?,?,?,?)",
           (uid, title, when, _now()), write=True)
        return f"Event added: {title}{', ' + when if when else ''}."
    rows = _q("SELECT * FROM events WHERE user_id=? ORDER BY id", (uid,))
    if not rows:
        return "Your calendar is empty."
    shown = ". ".join(f"Event {r['id']}: {r['title']}{', ' + r['when_text'] if r['when_text'] else ''}" for r in rows[:5])
    return f"You have {len(rows)} event{'s' if len(rows) != 1 else ''}. {shown}."


# ---------------------------------------------------------------- notes
def handle_notes(user_id, text):
    uid, t = str(user_id), _strip_lead(text).lower()
    if re.search(r"\b(delete|remove|clear)\b", t):
        return _delete("notes", uid, t, "note")
    item = _clean(text, "notes?")
    wants_list = re.match(LIST_START, t) or re.fullmatch(r"(?:my |all )*notes?|", item.lower())
    if not wants_list:
        _q("INSERT INTO notes(user_id,text,created) VALUES(?,?,?)", (uid, item, _now()), write=True)
        return f"Noted: {item}."
    rows = _q("SELECT * FROM notes WHERE user_id=? ORDER BY id DESC", (uid,))
    if not rows:
        return "You have no notes yet."
    shown = ". ".join(f"Note {r['id']}: {r['text']}" for r in rows[:5])
    return f"You have {len(rows)} note{'s' if len(rows) != 1 else ''}. Latest first. {shown}."


# ---------------------------------------------------------------- memory
def save_memory(user_id, user_input, intent, emotion):
    _q("INSERT INTO memory(user_id,user_input,intent,emotion,created) VALUES(?,?,?,?,?)",
       (str(user_id), user_input, intent, emotion, _now()), write=True)