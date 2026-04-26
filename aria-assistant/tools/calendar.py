import os
import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Path to the OAuth client secrets file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRETS_FILE = os.path.join(
    PROJECT_ROOT,
    "client_secret_1017784643133-e1p3bn523m2m9k9euf94ednou4mlo308.apps.googleusercontent.com.json",
)
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")


def _get_calendar_service():
    """Authenticate and return a Google Calendar API service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def _format_event(event: dict) -> dict:
    """Format a calendar event into a clean summary."""
    start = event["start"].get("dateTime", event["start"].get("date", ""))
    end = event["end"].get("dateTime", event["end"].get("date", ""))
    return {
        "id": event["id"],
        "summary": event.get("summary", "No title"),
        "start": start,
        "end": end,
        "location": event.get("location", ""),
        "description": event.get("description", ""),
        "attendees": [
            a.get("email", "") for a in event.get("attendees", [])
        ],
        "meeting_link": event.get("hangoutLink", ""),
    }


def get_todays_events() -> dict:
    """Gets all calendar events for today.

    Returns a list of today's events including their times, titles, and attendees.
    """
    try:
        service = _get_calendar_service()
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + datetime.timedelta(days=1)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return {"status": "success", "message": "No events scheduled for today.", "events": []}

        return {
            "status": "success",
            "events": [_format_event(e) for e in events],
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_upcoming_events(days: int = 7) -> dict:
    """Gets calendar events for the next several days.

    Args:
        days: Number of days to look ahead. Defaults to 7.
    """
    try:
        service = _get_calendar_service()
        now = datetime.datetime.now(datetime.timezone.utc)
        end_time = now + datetime.timedelta(days=days)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return {"status": "success", "message": f"No events in the next {days} days.", "events": []}

        return {
            "status": "success",
            "events": [_format_event(e) for e in events],
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_event_details(event_id: str) -> dict:
    """Gets full details of a specific calendar event.

    Args:
        event_id: The Google Calendar event ID.
    """
    try:
        service = _get_calendar_service()
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        return {"status": "success", "event": _format_event(event)}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def create_event(summary: str, start_time: str, end_time: str, description: str = "", attendee_emails: str = "") -> dict:
    """Creates a new Google Calendar event.

    Args:
        summary: Title of the event (e.g., 'Team Standup').
        start_time: Start time in ISO format like '2026-03-28T14:00:00-05:00'. Include timezone offset.
        end_time: End time in ISO format like '2026-03-28T14:30:00-05:00'. Include timezone offset.
        description: Optional description for the event.
        attendee_emails: Optional comma-separated email addresses to invite (e.g., 'alice@company.com,bob@company.com').
    """
    try:
        service = _get_calendar_service()

        event_body = {
            "summary": summary,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
        }

        if description:
            event_body["description"] = description

        if attendee_emails:
            emails = [e.strip() for e in attendee_emails.split(",") if e.strip()]
            event_body["attendees"] = [{"email": email} for email in emails]

        event = service.events().insert(calendarId="primary", body=event_body).execute()

        return {
            "status": "success",
            "event_id": event["id"],
            "summary": event.get("summary", ""),
            "start": event["start"].get("dateTime", ""),
            "link": event.get("htmlLink", ""),
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
