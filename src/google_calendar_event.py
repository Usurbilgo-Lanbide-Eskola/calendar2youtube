#!/usr/bin/env python3

import logging

logger = logging.getLogger(__name__)


class GoogleCalendarEvent(object):

    def __init__(self, event_details, streaming_keywords=["[streaming]"], private_status_keywords=["[private]"]):
        self.details = event_details
        self.title = self.details.get("summary", "")
        self.start_date = self.details.get("start").get("dateTime")
        self.end_date = self.details.get("end").get("dateTime")
        self.description = self.details.get("description")
        self.streaming_keywords = streaming_keywords
        self.private_status_keywords = private_status_keywords

    def is_streaming(self):
        if not self.description:
            return False
        description = self.description.lower()
        for keyword in self.streaming_keywords:
            if keyword in description:
                return True
        return False

    def is_private(self):
        if not self.description:
            return False
        description = self.description.lower()
        for keyword in self.private_status_keywords:
            if keyword in description:
                return True
        return False