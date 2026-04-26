#!/bin/bash
# Send an email via Apple Mail
TO="$1"
SUBJECT="$2"
BODY="$3"

launchctl asuser $(id -u dominic) osascript << EOF
tell application "Mail"
    set newMsg to make new outgoing message with properties {subject:"$SUBJECT", content:"$BODY", visible:false}
    tell newMsg
        make new to recipient at end of to recipients with properties {address:"$TO"}
    end tell
    send newMsg
end tell
EOF

echo "Email sent to $TO"
