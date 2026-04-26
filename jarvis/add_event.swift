import EventKit
import Foundation

// Usage: swift add_event.swift "Title" "Calendar" "2026-04-20 14:00" "2026-04-20 15:00" "Location" "Notes"
let args = CommandLine.arguments
guard args.count >= 5 else {
    print("Usage: swift add_event.swift \"Title\" \"Calendar\" \"YYYY-MM-DD HH:MM\" \"YYYY-MM-DD HH:MM\" \"Location (optional)\" \"Notes (optional)\"")
    exit(1)
}

let title    = args[1]
let calName  = args[2]
let startStr = args[3]
let endStr   = args[4]
let location = args.count > 5 ? args[5] : ""
let notes    = args.count > 6 ? args[6] : ""

let formatter = DateFormatter()
formatter.dateFormat = "yyyy-MM-dd HH:mm"

guard let startDate = formatter.date(from: startStr),
      let endDate   = formatter.date(from: endStr) else {
    print("Error: Invalid date format. Use YYYY-MM-DD HH:MM")
    exit(1)
}

let store = EKEventStore()
let semaphore = DispatchSemaphore(value: 0)
var accessGranted = false

store.requestFullAccessToEvents { granted, _ in
    accessGranted = granted
    semaphore.signal()
}
semaphore.wait()

guard accessGranted else {
    print("Calendar access denied.")
    exit(1)
}

// Find the calendar by name
let calendars = store.calendars(for: .event)
guard let calendar = calendars.first(where: { $0.title == calName }) else {
    let names = calendars.map { $0.title }.joined(separator: ", ")
    print("Calendar '\(calName)' not found. Available: \(names)")
    exit(1)
}

let event = EKEvent(eventStore: store)
event.title    = title
event.startDate = startDate
event.endDate   = endDate
event.calendar  = calendar
if !location.isEmpty { event.location = location }
if !notes.isEmpty    { event.notes    = notes }

do {
    try store.save(event, span: .thisEvent)
    print("✅ Event '\(title)' added to '\(calName)' on \(startStr)")
} catch {
    print("Error saving event: \(error)")
    exit(1)
}
