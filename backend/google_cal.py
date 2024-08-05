import datetime
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_credentials():
    creds = None
    token_path = "token.json"
    credentials_path = "credentials.json"

    # Load existing credentials from file
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(redirect_uri_trailing_slash=False, port=3000)
        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds

def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)
        
        # Example of creating a new event (for testing using terminal)
        print("Creating a new event")
        title = input("Enter a title: ")
        location = input("Enter a location: ")
        description = input("Enter a description: ")
        date = input("Enter a date (YYYY-MM-DD): ")

        event = {
            "summary": title,
            "location": location,
            "description": description,
            "start": {
                "date": date,
                "timeZone": "America/Los_Angeles",
            },
            "end": {
                "date": date,
                "timeZone": "America/Los_Angeles",
            },
            "recurrence": ["RRULE:FREQ=YEARLY"],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 7 * 24 * 60},
                    {"method": "email", "minutes": 0},
                ],
            },
        }
        
        event = service.events().insert(calendarId='primary', body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))
    
    except HttpError as error:
        print(f"An error occurred: {error}")
        print(f"Error details: {error.resp.reason}")
        print(f"Error content: {error.content}")

if __name__ == "__main__":
    main()
