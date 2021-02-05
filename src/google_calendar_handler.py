#!/usr/bin/env python3

import datetime
import json
import logging
from googleapiclient.discovery import build
from google_calendar_event import GoogleCalendarEvent

logger = logging.getLogger(__name__)


class GoogleCalendarHandler(object):

    def __init__(self, credentials, classroom_calendar_id, registration_calendar_id, streaming_keywords=["[streaming]"], private_keywords=["[private]"]):
        self.credentials = credentials
        self.service = build('calendar', 'v3', credentials=self.credentials)
        self.classroom_calendar_id = classroom_calendar_id
        self.registration_calendar_id = registration_calendar_id
        self.streaming_keywords = streaming_keywords
        self.private_keywords = private_keywords
        self.registered_events = None

    def get_classroom_events(self, previous_days=0, future_days=30, max_results=100):
        time_min = (datetime.datetime.utcnow() - datetime.timedelta(days=previous_days)).isoformat() + 'Z'
        time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=future_days)).isoformat() + 'Z'

        events_result = self.service.events().list(calendarId=self.classroom_calendar_id, 
                                        timeMin=time_min, timeMax=time_max,
                                        maxResults=max_results, singleEvents=True,
                                        orderBy='startTime').execute()
        __events = events_result.get('items', [])
        events = [GoogleCalendarEvent(__event, self.streaming_keywords, self.private_keywords) for __event in __events]

        logger.debug("Number of events found: {}".format(len(events)))
        return events

    def get_classroom_streaming_events(self, previous_days=0, future_days=30, max_results=100):
        events = self.get_classroom_events(previous_days, future_days)
        streaming_events = list(filter(lambda e: e.is_streaming(), events))
        streaming_events_accepted = streaming_events[:max_results]
        logger.debug("Number of streaming events accepted: {} ({})".format(len(streaming_events_accepted), len(streaming_events)))
        return streaming_events_accepted

    def get_classroom_next_streaming_event(self):
        events = self.get_classroom_streaming_events(0, 7, 1)

        if not events:
            logger.info("No events for the next week")
            return
        elif len(events) == 1:
            event = events[0]
            logger.debug("One event for the next week: '{}'".format(event.title))
            return event
        else:
            logger.error("Something really wrong has happened with Google Calendar API")
            return