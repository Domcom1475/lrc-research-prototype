#!/usr/bin/env python3
"""
Scans recent iMessages for event-like content and outputs calendar commands.
"""
import sqlite3
import shutil
import os
import json
import re
import subprocess
from datetime import datetime, timedelta

# Copy DB to avoid lock
src = os.path.expanduser("~/Library/Messages/chat.db")
dst = "/tmp/chat_scan.db"
shutil.copy2(src, dst)

con = sqlite3.connect(dst)
cur = con.cursor()

# Get messages from the last 24 hours
cur.execute('''
    SELECT
        datetime(m.date/1000000000 + strftime("%s","2001-01-01"), "unixepoch", "localtime") as date,
        h.id as sender,
        m.text,
        m.is_from_me
    FROM message m
    LEFT JOIN handle h ON m.handle_id = h.ROWID
    WHERE m.text IS NOT NULL
      AND m.date > (strftime("%s", "now") - strftime("%s", "2001-01-01") - 86400) * 1000000000
    ORDER BY m.date DESC
    LIMIT 100
''')
rows = cur.fetchall()
con.close()

if not rows:
    print("No recent messages found.")
    exit(0)

# Format messages for analysis
messages_text = ""
for date, sender, text, is_from_me in rows:
    who = "Me" if is_from_me else (sender or "Unknown")
    messages_text += f"[{date}] {who}: {text}\n"

# Use a simple heuristic to find event-like messages
# Look for time patterns, day names, words like "meet", "hang", "at", etc.
time_patterns = [
    r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    r'\b(tonight|tomorrow|this weekend|next week)\b',
    r'\b\d{1,2}(:\d{2})?\s*(am|pm)\b',
    r'\b(meet|hang|come over|pick you up|let\'s|lets|dinner|lunch|breakfast|party|study|game)\b',
]

event_messages = []
for date, sender, text, is_from_me in rows:
    if not text:
        continue
    text_lower = text.lower()
    matches = sum(1 for p in time_patterns if re.search(p, text_lower))
    if matches >= 2:
        who = "Me" if is_from_me else (sender or "Unknown")
        event_messages.append((date, who, text))

# Write results to output file
output_path = os.path.expanduser("~/Library/Calendars/message_events.txt")
with open(output_path, "w") as f:
    if event_messages:
        f.write(f"Found {len(event_messages)} potential events in recent messages:\n\n")
        for date, who, text in event_messages:
            f.write(f"Date: {date}\n")
            f.write(f"From: {who}\n")
            f.write(f"Message: {text}\n")
            f.write("---\n")
    else:
        f.write("No event-like messages found in the last 24 hours.\n")
    f.write(f"\nScanned {len(rows)} messages at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print(f"Done. Found {len(event_messages)} potential events from {len(rows)} messages.")
