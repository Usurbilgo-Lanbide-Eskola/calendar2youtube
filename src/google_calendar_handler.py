#!/usr/bin/env python3

import datetime
import json
import logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GoogleCalendarHandler(object):

    def __init__(self, credentials, classroom_calendar_id, registration_calendar_id, keyword="[Streaming]"):
        self.credentials = credentials
        self.service = build('calendar', 'v3', credentials=self.credentials)
        self.classroom_calendar_id = classroom_calendar_id
        self.registration_calendar_id = registration_calendar_id
        self.keyword = keyword
        self.registered_events = None

    def build_registered_events(self):
        events_result = self.service.events().list(calendarId=self.registration_calendar_id,
                                        maxResults=100, singleEvents=True,
                                        orderBy='startTime').execute()
        
        events = events_result.get('items', [])

        registered_events = {}
        for event in events:
            description = json.loads(event.get("description"))
            original_id = description.get("original-id")
            last_update = description.get("last_update")
            registered_events[original_id] = { "last_update": last_update, "event": event, "processed": False}
        return registered_events

    def create_register_event(self, event):
        new_event = {
            'summary': event.get('summary'),
            'start': event.get('start'),
            'end': event.get('end'),
            'description': json.dumps({"original-id": event.get("id"),
                                       "last-update": event.get("updated"),
                                       "creator": event.get("organizer").get("email")})
        }

        insert_result = self.service.events().insert(calendarId=self.registration_calendar_id, body=new_event).execute()

    def update_register_event(self, event_id, event):
        new_event = {
            'summary': event.get('summary'),
            'start': event.get('start'),
            'end': event.get('end'),
            'description': json.dumps({"original-id": event.get("id"),
                                       "last-update": event.get("updated"),
                                       "creator": event.get("organizer").get("email")})
        }
        update_result = self.service.events().update(calendarId=self.registration_calendar_id, eventId=event_id, body=new_event).execute()

    def delete_register_event(self, event_id):
        delete_result = self.service.events().delete(calendarId=self.registration_calendar_id, eventId=event_id).execute()

    def get_classroom_events(self, previous_days=0, future_days=30, max_results=100):
        time_min = (datetime.datetime.utcnow() - datetime.timedelta(days=previous_days)).isoformat() + 'Z'
        time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=future_days)).isoformat() + 'Z'

        events_result = self.service.events().list(calendarId=self.classroom_calendar_id, 
                                        timeMin=time_min, timeMax=time_max,
                                        maxResults=max_results, singleEvents=True,
                                        orderBy='startTime').execute()
        events = events_result.get('items', [])

        logger.debug("Number of events found: {}".format(len(events)))
        return events

    def get_classroom_streaming_events(self, previous_days=0, future_days=30, max_results=100):
        events = self.get_classroom_events(previous_days, future_days, max_results)
        streaming_events = [event for event in events if event.get("description") and self.keyword in event.get("description")]
        logger.debug("Number of streaming events: {}".format(len(streaming_events)))
        return streaming_events

    def get_classroom_next_streaming_event(self):
        events = self.get_classroom_streaming_events(0, 7, 1)

        if not events:
            logger.info("No events for the next week")
            return
        elif len(events) == 1:
            event = events[0]
            logger.debug("One event for the next week: '{}'".format(event.get('summary')))
            return event
        else:
            logger.error("Something really wrong has happened with Google Calendar API")
            return

    def synchronize_events(self, events):
        self.registered_events = self.build_registered_events()
        for event in events:
            event_id = event.get("id")
            if not event_id in self.registered_events:
                logger.info("New event must be created: '{}'".format(event_id))
                self.create_register_event(event)
                self.registered_events.update({event_id: {"processed": True}})
                continue
            registered_event = self.registered_events[event_id]
            new_last_update = event.get("updated")
            registered_last_update = registered_event.get("last_update")
            if new_last_update != registered_last_update:
                logger.warn("The event '{}' has changed".format(event_id))
                self.update_register_event(registered_event.get("event").get("id"), event)
                self.registered_events[event_id].update({"processed": True})
                continue
            else:
                logger.info("The event '{}' remains the same".format(event_id))
                self.registered_events[event_id].update({"processed": True})

        # Check deleted events
        events_to_delete = [event_info.get("event") for event_info in self.registered_events.values() if not event_info.get("processed")]
        events_id_to_delete = [event.get("id") for event in events_to_delete]
        for event_id in events_id_to_delete:
            logger.info("The registered event '{}' has been deleted or it is too old".format(event_id))
            self.delete_register_event(event_id)

    def get_next_registered_event(self):
        now = datetime.datetime.utcnow()
        timeMin = now.isoformat() + 'Z'
        timeMax = (now + datetime.timedelta(days=7)).isoformat() + 'Z'
        events_result = self.service.events().list(calendarId=self.registration_calendar_id,
                                        timeMin=timeMin, timeMax=timeMax,
                                        maxResults=1, singleEvents=True,
                                        orderBy='startTime').execute()
        
        events = events_result.get('items', [])

        if not events:
            logger.info("No events for the next week")
            return
        elif len(events) == 1:
            event = events[0]
            logger.debug("One event for the next week: '{}'".format(event.get('summary')))
            return event
        else:
            logger.error("Something really wrong has happened with Google Calendar API")
            return
        
