#!/bin/bash
# Send an iMessage to Dominic's phone
NUMBER="YOUR_PHONE_NUMBER"
MESSAGE="$1"

launchctl asuser $(id -u dominic) osascript << EOF
tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "$NUMBER" of targetService
    send "$MESSAGE" to targetBuddy
end tell
EOF
