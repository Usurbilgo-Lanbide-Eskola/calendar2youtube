#!/usr/bin/env python3

import datetime
import json
import pickle
from dotenv import load_dotenv
import logging
import os.path

from google_calendar_handler import GoogleCalendarHandler
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from youtube_handler import YouTubeHandler

logging.basicConfig(format='%(asctime)s %(levelname)-6s - %(name)-16s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/youtube']


def load_credentials(credentials_path='credentials.json', token_path='token.pickle'):
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    credentials = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            credentials = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)
    return credentials


def main():
    logger.info("Starting calendar2youtube app...")

    load_dotenv()
    CLASSROOM_CALENDAR_ID = os.getenv("CLASSROOM_CALENDAR_ID", "")
    CALENDAR2YOUTUBE_CALENDAR_ID = os.getenv("CALENDAR2YOUTUBE_CALENDAR_ID", "")
    LIVE_STREAM_TITLE = os.getenv("LIVE_STREAM_TITLE", "")
    STREAMING_KEYWORDS = json.loads(os.getenv("STREAMING_KEYWORDS", '["[streaming]"]'))
    PRIVATE_KEYWORDS = json.loads(os.getenv("PRIVATE_KEYWORDS", '["[private]"]'))

    if not CLASSROOM_CALENDAR_ID or not CALENDAR2YOUTUBE_CALENDAR_ID or not LIVE_STREAM_TITLE:
        logger.error("There is a missing configuration parameter")
        return

    credentials = load_credentials()
    
    # Create handlers
    g_cal_handler = GoogleCalendarHandler(credentials, CLASSROOM_CALENDAR_ID, CALENDAR2YOUTUBE_CALENDAR_ID, STREAMING_KEYWORDS, PRIVATE_KEYWORDS)
    youtube_handler = YouTubeHandler(credentials)
    youtube_handler.set_stream_title(LIVE_STREAM_TITLE)

    # Get next classroom and youtube events
    next_registered_event = g_cal_handler.get_classroom_next_streaming_event()
    next_youtube_event = youtube_handler.get_next_youtube_event()

    youtube_handler.compare_and_set_event(next_registered_event, next_youtube_event)


if __name__ == '__main__':
    main()