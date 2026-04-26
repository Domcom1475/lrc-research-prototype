#!/usr/bin/env python3
"""Exports recent 24h messages to a readable text file for Jarvis tasks."""
import sqlite3, shutil, re

SKIP_STRINGS = {
    'streamtyped', 'NSString', 'NSMutableString', 'NSAttributedString',
    'NSMutableAttributedString', 'NSColor', 'NSFont', 'NSObject', 'NSArray',
    'NSDictionary', 'NSParagraphStyle', 'NSValue', 'NSNumber', 'NSDate',
    'NSData', 'NSURL', 'NSNull', '$null', 'NSArchiver', 'NSUnarchiver',
    '__kIMMessagePartAttributeName', '__kIMFileTransferGUIDAttributeName',
    'IMMessagePartAttributeName', 'IMLinkAttributeName', 'i', '+', '-',
}

def decode_attributed_body(blob):
    """Extract plain text from iMessage attributedBody binary blob."""
    if blob is None:
        return None
    try:
        # Scan for all UTF-8 readable strings of 2+ chars
        candidates = re.findall(rb'[\x20-\x7E\xC0-\xFE]{2,}', blob)
        for c in candidates:
            try:
                s = c.decode('utf-8', errors='ignore').strip()
                if (len(s) >= 2 and
                    s not in SKIP_STRINGS and
                    not s.startswith('NS') and
                    not s.startswith('$') and
                    not s.startswith('__') and
                    not s.startswith('IM') and
                    not s.startswith('+1') and
                    not all(c in '0123456789.-+' for c in s)):
                    return s
            except Exception:
                continue
    except Exception:
        pass
    return None

shutil.copy2('/Users/dominic/Library/Messages/chat.db', '/tmp/chat_export.db')
con = sqlite3.connect('/tmp/chat_export.db')
cur = con.cursor()
cur.execute('''
    SELECT datetime(m.date/1000000000 + strftime("%s","2001-01-01"), "unixepoch", "localtime") as dt,
           COALESCE(h.id, "ME") as sender,
           m.text,
           m.attributedBody,
           m.is_from_me,
           COALESCE(chat.chat_identifier, h.id, "unknown") as thread
    FROM message m
    LEFT JOIN handle h ON m.handle_id = h.ROWID
    LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
    LEFT JOIN chat ON cmj.chat_id = chat.ROWID
    WHERE m.date > (strftime("%s","now") - strftime("%s","2001-01-01") - 86400) * 1000000000
    ORDER BY thread, m.date ASC
''')

current_thread = None
lines = []
for r in cur.fetchall():
    dt, sender, text, attributed_body, is_from_me, thread = r
    content = text or decode_attributed_body(attributed_body)
    if not content or content.strip() == '':
        continue
    if thread != current_thread:
        current_thread = thread
        lines.append(f'\n--- Thread: {thread} ---')
    who = 'ME' if is_from_me else sender
    lines.append(f'[{dt}] {who}: {content}')

con.close()

with open('/Users/dominic/Library/Calendars/recent_messages.txt', 'w') as f:
    f.write('\n'.join(lines))
print(f'Exported {len(lines)} lines')
