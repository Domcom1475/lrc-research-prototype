#!/bin/bash
WATCH_DIR="/Users/dominic/Library/Calendars"
COMMAND_FILE="$WATCH_DIR/run_command.sh"
OUTPUT_FILE="$WATCH_DIR/command_output.txt"

echo "bridge ran at $(date)" >> "$WATCH_DIR/bridge.log"
echo "checking for: $COMMAND_FILE" >> "$WATCH_DIR/bridge.log"

if [ -f "$COMMAND_FILE" ]; then
    echo "found command file, executing..." >> "$WATCH_DIR/bridge.log"
    echo "=== Run at $(date) ===" > "$OUTPUT_FILE"
    bash "$COMMAND_FILE" >> "$OUTPUT_FILE" 2>&1
    echo "=== Done ===" >> "$OUTPUT_FILE"
    rm -f "$COMMAND_FILE"
    echo "done and cleaned up" >> "$WATCH_DIR/bridge.log"
else
    echo "no command file found" >> "$WATCH_DIR/bridge.log"
fi
