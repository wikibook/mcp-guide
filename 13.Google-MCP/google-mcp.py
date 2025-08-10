from fastmcp import FastMCP
from typing import Annotated, Dict, List, Optional
from pydantic import Field
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import base64
import pytz
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

mcp = FastMCP(
    "Google-MCP",
    dependencies=["fastmcp","pydantic","google-auth","google-auth-oauthlib", "google-api-python-client"
    ]
)

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

class GoogleAuth:
    def __init__(self, scopes=SCOPES, token_file=None, creds_file=None):
        try:
            self.token_file = Path(token_file) if token_file else Path(__file__).resolve().parent / "token.json"
        except NameError:
            self.token_file = Path(os.getcwd()) / "token.json"
        self.creds_file = creds_file or os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.scopes = scopes
        self.creds = None

    def load_token(self):
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    expires_at = datetime.fromisoformat(token_data['expires_at'])
                    if datetime.now() < expires_at:
                        return token_data['token'], expires_at
            except Exception as e:
                print(f"Error loading token: {e}")
        return None, None

    def save_token(self, token, expires_at):
        try:
            with open(self.token_file, 'w') as f:
                json.dump({'token': token, 'expires_at': expires_at.isoformat()}, f)
        except Exception as e:
            print(f"Error saving token: {e}")

    def get_credentials(self):
        token, expires_at = self.load_token()
        creds = None

        if token and expires_at and datetime.now() < expires_at:
            try:
                creds = Credentials(token=token, scopes=self.scopes)
            except Exception as e:
                print(f"Error creating credentials from token: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(self.creds_file, self.scopes)
                creds = flow.run_local_server(port=0)
                expires_at = datetime.now() + timedelta(hours=1)
                self.save_token(creds.token, expires_at)
        self.creds = creds
        return creds

    def build_calendar_service(self):
        creds = self.get_credentials()
        return build('calendar', 'v3', credentials=creds)

    def build_gmail_service(self):
        creds = self.get_credentials()
        return build('gmail', 'v1', credentials=creds)

# 인증 클래스 인스턴스 생성
# Create an instance of the authentication class
google_auth = GoogleAuth()

@mcp.tool(
    name="create_calendar_event",
    description="Create a Google Calendar event without a Google Meet link."
)
def create_calendar_event(
    summary: Annotated[str, Field(description="Event title")],
    start_time: Annotated[datetime, Field(description="Event start time (datetime)")],
    end_time: Annotated[datetime, Field(description="Event end time (datetime)")],
    attendees: Annotated[List[str], Field(description="List of attendee email addresses")] = [],
) -> dict:
    """
    Args:
        summary (str): Title of the event.
        start_time (datetime): Event start time.
        end_time (datetime): Event end time.
        attendees (List[str], optional): List of attendee email addresses.

    Returns:
        dict: Information about the created event (id, link, title, etc.).
    """
    service = google_auth.build_calendar_service()
    event_body = {
        'summary': summary,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Seoul'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Seoul'},
    }
    if attendees:
        event_body['attendees'] = [{'email': email} for email in attendees]
    event = service.events().insert(
        calendarId='primary',
        body=event_body
    ).execute()
    return {
        "event_id": event["id"],
        "calendar_link": event.get("htmlLink"),
        "summary": event.get("summary"),
        "start": event.get("start"),
        "end": event.get("end"),
    }

@mcp.tool(
    name="create_event_with_meet_link",
    description="Create a Google Calendar event with a Google Meet link."
)
def create_event_with_meet_link(
    summary: Annotated[str, Field(description="Event title")],
    start_time: Annotated[datetime, Field(description="Event start time (datetime)")],
    end_time: Annotated[datetime, Field(description="Event end time (datetime)")],
    attendees: Annotated[List[str], Field(description="List of attendee email addresses")] = [],
) -> dict:
    """
    Args:
        summary (str): Title of the event.
        start_time (datetime): Event start time.
        end_time (datetime): Event end time.
        attendees (List[str], optional): List of attendee email addresses.

    Returns:
        dict: Information about the created event (id, Meet link, calendar link, etc.).
    """
    service = google_auth.build_calendar_service()
    event_body = {
        'summary': summary,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Seoul'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Seoul'},
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet-{int(datetime.now().timestamp())}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
            }
        }
    }
    if attendees:
        event_body['attendees'] = [{'email': email} for email in attendees]
    event = service.events().insert(
        calendarId='primary',
        body=event_body,
        conferenceDataVersion=1
    ).execute()
    return {
        "event_id": event["id"],
        "meet_link": event.get("hangoutLink"),
        "calendar_link": event.get("htmlLink"),
        "summary": event.get("summary"),
        "start": event.get("start"),
        "end": event.get("end"),
    }

@mcp.tool(
    name="delete_event",
    description="Delete an event from Google Calendar."
)
def delete_event(
    event_id: Annotated[str, Field(description="The event_id of the event to delete")]
) -> str:
    """
    Args:
        event_id (str): The ID of the event to delete.

    Returns:
        str: Message indicating the deletion result.
    """
    service = google_auth.build_calendar_service()
    service.events().delete(calendarId='primary', eventId=event_id).execute()
    return f"Event deleted: {event_id}"

@mcp.tool(
    name="list_events",
    description="List Google Calendar events within a specified time range."
)
def list_events(
    start_time: Annotated[Optional[datetime], Field(description="Start datetime for event search (ISO format)")] = None,
    end_time: Annotated[Optional[datetime], Field(description="End datetime for event search (ISO format)")] = None,
    max_results: Annotated[int, Field(description="Maximum number of events to retrieve")] = 10
) -> list:
    """
    Args:
        start_time (datetime, optional): Start datetime for event search.
        end_time (datetime, optional): End datetime for event search.
        max_results (int): Maximum number of events to retrieve.

    Returns:
        list: List of event information dictionaries.
    """
    service = google_auth.build_calendar_service()
    time_min = start_time.isoformat() + 'Z' if start_time else datetime.utcnow().isoformat() + 'Z'
    time_max = end_time.isoformat() + 'Z' if end_time else None

    request_params = {
        'calendarId': 'primary',
        'timeMin': time_min,
        'maxResults': max_results,
        'singleEvents': True,
        'orderBy': 'startTime'
    }
    if time_max:
        request_params['timeMax'] = time_max

    events_result = service.events().list(**request_params).execute()
    events = events_result.get('items', [])

    result = []
    for event in events:
        result.append({
            "event_id": event.get("id"),
            "summary": event.get("summary"),
            "start": event.get("start"),
            "end": event.get("end"),
            "calendar_link": event.get("htmlLink"),
            "meet_link": event.get("hangoutLink"),
        })
    return result

@mcp.tool(
    name="send_gmail_api",
    description="Send an email via Gmail API (not SMTP)."
)
def send_gmail_api(
    to_email: Annotated[str, Field(description="Recipient email address")],
    subject: Annotated[str, Field(description="Email subject")],
    body: Annotated[str, Field(description="Plain text email body")]
) -> str:
    """
    Args:
        to_email (str): Recipient email address.
        subject (str): Email subject.
        body (str): Plain text email body.

    Returns:
        str: Success or failure message for sending the email.
    """
    service = google_auth.build_gmail_service()
    message = MIMEText(body)
    message['to'] = to_email
    message['from'] = "me"
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body_data = {'raw': raw}

    try:
        sent_message = service.users().messages().send(userId='me', body=body_data).execute()
        return f"Email sent successfully to {to_email}. Message Id: {sent_message['id']}"
    except Exception as e:
        return f"Failed to send email: {e}"

@mcp.tool(
    name="search_gmail_api",
    description="Search emails in Gmail via Gmail API using subject, date range, and mailbox (INBOX or SENT)."
)
def search_gmail_api(
    subject: Annotated[str, Field(description="Subject keyword to search for")],
    after: Annotated[Optional[str], Field(description="Start date (YYYY-MM-DD)")] = None,
    before: Annotated[Optional[str], Field(description="End date (YYYY-MM-DD)")] = None,
    inbox_or_sent: Annotated[str, Field(description="Mailbox to search: 'INBOX' (received) or 'SENT' (sent)")] = 'INBOX',
    max_results: Annotated[int, Field(description="Maximum number of emails to retrieve")] = 5
) -> list:
    """
    Args:
        subject (str): Subject keyword to search for.
        after (str, optional): Start date (YYYY-MM-DD).
        before (str, optional): End date (YYYY-MM-DD).
        inbox_or_sent (str): 'INBOX' for received mail, 'SENT' for sent mail.
        max_results (int): Maximum number of emails to retrieve. This is limited to 5.

    Returns:
        list: List of email information dictionaries or error message.
    """
    service = google_auth.build_gmail_service()
    query_parts = []
    if subject:
        query_parts.append(f"subject:{subject}")
    if after:
        dt = datetime.strptime(after, "%Y-%m-%d")
        tz = pytz.timezone('US/Pacific')
        ts = int(tz.localize(dt).timestamp())
        query_parts.append(f"after:{ts}")
    if before:
        dt = datetime.strptime(before, "%Y-%m-%d")
        tz = pytz.timezone('US/Pacific')
        ts = int(tz.localize(dt).timestamp())
        query_parts.append(f"before:{ts}")
    query = ' '.join(query_parts)

    # 받은편지함/보낸편지함 라벨 설정
    label_id = 'INBOX' if inbox_or_sent.upper() == 'INBOX' else 'SENT'

    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            labelIds=[label_id],
            maxResults=max_results
        ).execute()
        messages = results.get('messages', [])
        details = []
        for msg in messages:
            msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
            details.append({
                "id": msg_detail.get("id"),
                "snippet": msg_detail.get("snippet"),
                "from": next((h['value'] for h in msg_detail['payload']['headers'] if h['name'] == 'From'), None),
                "subject": next((h['value'] for h in msg_detail['payload']['headers'] if h['name'] == 'Subject'), None),
                "date": next((h['value'] for h in msg_detail['payload']['headers'] if h['name'] == 'Date'), None),
            })
        return details
    except Exception as e:
        return [{"error": str(e)}]


def main():
    token_path = google_auth.token_file if hasattr(google_auth, 'token_file') else "token.json"
    creds = None

    # 1. 토큰 파일이 있으면 로드
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, google_auth.scopes)
        # 2. 토큰이 유효하지 않으면 refresh 시도
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # refresh 성공 시 갱신된 토큰 저장
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"토큰 refresh 실패: {e}")
                    creds = None
            else:
                creds = None
    else:
        print("토큰 파일이 없습니다.")

    # 3. creds가 없으면 generate_token()으로 새로 생성
    if not creds or not creds.valid:
        print("유효한 토큰이 없어 generate_token()을 실행합니다.")
        generate_token()
        print("토큰 생성 후 MCP tool을 실행합니다.")
    else:
        print("유효한 토큰이 있어 바로 MCP tool을 실행합니다.")
    # 4. MCP tool 실행
    mcp.run()

if __name__ == "__main__":
    main()
