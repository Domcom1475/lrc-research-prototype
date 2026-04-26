#!/bin/bash
# Export Apple Calendar events for next 14 days using AppleScript
OUTPUT="/Users/dominic/Library/Calendars/calendar_export.txt"

launchctl asuser $(id -u dominic) osascript << 'OSASCRIPT' > "$OUTPUT" 2>&1
set outputLines to {}
set now to current date
set futureDate to now + (14 * 24 * 60 * 60)

tell application "Calendar"
    repeat with cal in every calendar
        set calName to name of cal
        set allEvents to every event of cal
        repeat with evt in allEvents
            try
                set evtStart to start date of evt
                set evtEnd to end date of evt
                if evtStart >= now and evtStart <= futureDate then
                    set evtTitle to summary of evt
                    set evtLoc to ""
                    try
                        set evtLoc to location of evt
                        if evtLoc is missing value then set evtLoc to ""
                    end try
                    set evtNotes to ""
                    try
                        set evtNotes to description of evt
                        if evtNotes is missing value then set evtNotes to ""
                    end try
                    set evtLine to "Title: " & evtTitle & "\nCalendar: " & calName & "\nStart: " & (evtStart as string) & "\nEnd: " & (evtEnd as string) & "\nLocation: " & evtLoc & "\nNotes: " & evtNotes & "\n---"
                    set end of outputLines to evtLine
                end if
            end try
        end repeat
    end repeat
end tell

set AppleScript's text item delimiters to "\n"
return outputLines as string
OSASCRIPT

echo "Calendar export done at $(date)" >> /tmp/calendar-export.log
