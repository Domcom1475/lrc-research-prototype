#!/bin/bash
TITLE="${1:-Jarvis}"
MESSAGE="${2:-Reminder}"
SOUND="${3:-default}"
# Run osascript in the logged-in user's GUI session so notifications show up
launchctl asuser $(id -u dominic) osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\" sound name \"$SOUND\""
