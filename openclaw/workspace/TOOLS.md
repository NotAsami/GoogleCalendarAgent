# Calendar tools

You have access to the user's Google Calendar via a local HTTP API at http://localhost:5050.
IMPORTANT: Always use the exec tool with curl. Never use fetch, wget or any other method.

## Get today's events
```bash
curl -s http://localhost:5050/events/today
```

## Create an event
```bash
curl -s -X POST http://localhost:5050/events/create \
  -H "Content-Type: application/json" \
  -d '{"title": "Meeting", "start_time": "2026-01-15T09:00:00", "end_time": "2026-01-15T10:00:00"}'
```
Required: title, start_time, end_time (ISO 8601). Optional: description.

## Reschedule an event
```bash
curl -s -X POST http://localhost:5050/events/reschedule \
  -H "Content-Type: application/json" \
  -d '{"event_id": "EVENT_ID", "new_start": "2026-01-15T14:00:00", "new_end": "2026-01-15T15:00:00"}'
```
Required: event_id (from today's events), new_start, new_end.

Always check today's events before creating or rescheduling.
Timezone is Europe/Bratislava. Times in ISO 8601 format.
