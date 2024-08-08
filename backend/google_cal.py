# Google Calendar API
# This file should be regarded as a reference and is not used in the actual project
import os.path

from flask import Flask, redirect, request, url_for
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(redirect_uri_trailing_slash=False, port=3000)
    # Save the credentials for the next run

    with open("token.json", "w") as token:
      token.write(creds.to_json())
  
  try:
    service = build("calendar", "v3", credentials=creds)
    # testing using terminal
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
      # reminders 1 week before and on the day of the event
      "reminders": {
        "useDefault": False,
        "overrides": [
          {"method": "email", "minutes": 7 * 24 * 60},
          {"method": "email", "minutes": 0},
        ],
      },
    }
    try:
      event = service.events().insert(calendarId='primary', body=event).execute()
      print('Event created: %s' % (event.get('htmlLink')))
      return redirect(url_for('base'))
    except HttpError as error:
      print(f"An error occurred: {error}")
      print(f"Error details: {error.resp.reason}")
      print(f"Error content: {error.content}")
    
  except HttpError as error:
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()