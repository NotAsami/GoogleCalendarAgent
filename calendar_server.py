"""
Minimal Google Calendar HTTP API for an OpenClaw agent.

Exposes today's events, event creation and rescheduling on localhost so the
agent can call them with curl through its exec tool.
"""

import os
import datetime
from zoneinfo import ZoneInfo

from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = os.environ.get("CALENDAR_TZ", "Europe/Bratislava")
HOST = os.environ.get("CALENDAR_HOST", "127.0.0.1")
PORT = int(os.environ.get("CALENDAR_PORT", "5050"))
TOKEN_FILE = os.environ.get("GOOGLE_TOKEN_FILE", "token.json")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")

app = Flask(__name__)


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Opens a browser: run this once on a machine with a desktop,
            # then copy token.json to the server.
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


service = get_calendar_service()


def missing(data, fields):
    return not data or not all(k in data for k in fields)


@app.route("/events/today", methods=["GET"])
def today():
    try:
        tz = ZoneInfo(TIMEZONE)  # handles CET/CEST switch automatically
        now = datetime.datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        result = service.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])
        if not events:
            return jsonify({"result": "No events today."})
        lines = []
        for e in events:
            start_time = e["start"].get("dateTime", e["start"].get("date"))
            lines.append(f"[{e['id']}] {e.get('summary', '(no title)')} at {start_time}")
        return jsonify({"result": "\n".join(lines)})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@app.route("/events/create", methods=["POST"])
def create():
    try:
        data = request.json
        if missing(data, ["title", "start_time", "end_time"]):
            return jsonify({"error": "Missing required fields: title, start_time, end_time"}), 400
        event = {
            "summary": data["title"],
            "description": data.get("description", ""),
            "start": {"dateTime": data["start_time"], "timeZone": TIMEZONE},
            "end": {"dateTime": data["end_time"], "timeZone": TIMEZONE},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return jsonify({"result": f"Created: {created['summary']} (id: {created['id']})"})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@app.route("/events/reschedule", methods=["POST"])
def reschedule():
    try:
        data = request.json
        if missing(data, ["event_id", "new_start", "new_end"]):
            return jsonify({"error": "Missing required fields: event_id, new_start, new_end"}), 400
        event = service.events().get(calendarId="primary", eventId=data["event_id"]).execute()
        event["start"] = {"dateTime": data["new_start"], "timeZone": TIMEZONE}
        event["end"] = {"dateTime": data["new_end"], "timeZone": TIMEZONE}
        updated = service.events().update(
            calendarId="primary", eventId=data["event_id"], body=event
        ).execute()
        return jsonify({"result": f"Rescheduled: {updated['summary']} to {updated['start']['dateTime']}"})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Bind to localhost only: the API has no auth and must never be public.
    app.run(host=HOST, port=PORT)
