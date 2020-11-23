#!/usr/bin/env python3

import datetime
import iso8601
import logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class YouTubeHandler(object):

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("youtube", 'v3', credentials=credentials)
        self.stream_title = None
        self.stream_id = None

    def set_stream_title(self, title):
        self.stream_title = title
        self.stream_id = self.get_stream_id_by_title(self.stream_title)

    def get_next_youtube_event(self):
        live_broadcasts_result = self.service.liveBroadcasts().list(
                                                part="snippet,contentDetails,status",
                                                broadcastType="all", mine=True
                                            ).execute()

        live_broadcasts = live_broadcasts_result.get('items', [])

        if not live_broadcasts:
            logger.debug("No YouTube events scheduled")
            return
        elif len(live_broadcasts) == 1:
            live_broadcast = live_broadcasts[0]
            logger.debug("One event scheduled: '{}'".format(live_broadcast.get("id")))
            return live_broadcast
        else:
            # We only allow a single scheduled event
            logger.debug("More than one YouTube event scheduled, delete all of them")
            for live_broadcast in live_broadcasts:
                self.delete_youtube_event(live_broadcast.get("id"))
            return

    def compare_and_set_event(self, calendar_event, youtube_event):
        # No Calendar and no YouTube event present
        if not youtube_event and not calendar_event:
            logger.debug("Nothing to do, no events")
            return

        # YouTube event created, but deleted in Google Calendar
        if youtube_event and not calendar_event:
            logger.info("Non existing YouTube event created, delete it")
            y_id = youtube_event.get("id")
            self.delete_youtube_event(y_id)
            return
        
        # Google Calendar present, but not created in YouTube
        if calendar_event and not youtube_event:
            logger.info("Existing event not created, create it")
            self.create_youtube_event(calendar_event)
            return

        # Both present, check if they are the same
        g_title = calendar_event.get("summary", "")
        g_start = calendar_event.get("start", {}).get("dateTime")
        g_end = calendar_event.get("end", {}).get("dateTime")

        y_id = youtube_event.get("id")
        y_title = youtube_event.get("snippet", {}).get("title", "")
        y_start = youtube_event.get("snippet", {}).get("scheduledStartTime", None)
        y_end = youtube_event.get("snippet", {}).get("scheduledEndTime", None)

        if g_title != y_title or \
            iso8601.parse_date(g_start) != iso8601.parse_date(y_start) or \
                iso8601.parse_date(g_end) != iso8601.parse_date(y_end):
            logger.warn("Both events are not synchronized, recreate it")
            self.delete_youtube_event(y_id)
            self.create_youtube_event(calendar_event)
        else:
            logger.debug("Everything is synchronized")

    def create_youtube_event(self, calendar_event):
        title = calendar_event.get("summary")
        start = calendar_event.get("start").get("dateTime")
        end = calendar_event.get("end").get("dateTime")

        broadcast_id = self.create_broadcast(title, start, end)
        self.bind_broadcast(broadcast_id, self.stream_id)

    def delete_youtube_event(self, broadcast_id):
        delete_broadcast_response = self.service.liveBroadcasts().delete(
                                                    id=broadcast_id
                                                ).execute()

    def get_stream_id_by_title(self, title):
        live_streams_result = self.service.liveStreams().list(
                                                part="snippet,cdn,contentDetails,status", mine=True
                                            ).execute()
        live_streams = live_streams_result.get('items', [])

        if not live_streams:
            logger.warn('No live streams')
            return None
        logger.debug("Number of live streams registered: {}".format(len(live_streams)))

        for live_stream in live_streams:
            stream_snippet = live_stream.get('snippet')
            if not stream_snippet:
                continue
            stream_title = stream_snippet.get("title")
            if stream_title == title:
                stream_id = live_stream.get("id")
                logger.debug("Id: '{}' for stream '{}'".format(stream_id, title))
                return stream_id

    def create_broadcast(self, title, start_time, end_time):
        create_broadcast_response = self.service.liveBroadcasts().insert(
                                    part="snippet,status,contentDetails",
                                    body={
                                        "snippet": {
                                            "title": title,
                                            "scheduledStartTime": start_time,
                                            "scheduledEndTime": end_time
                                        },
                                        "status": {
                                            "selfDeclaredMadeForKids": False,
                                            "privacyStatus": "public"
                                            
                                        },
                                        "contentDetails": {
                                            "enableAutoStart": True
                                        }
                                    }
                                ).execute()

        broadcast_id = create_broadcast_response.get('id')
        if not broadcast_id:
            logger.error("Broadcast could not be create")
            return

        broadcast_title = create_broadcast_response.get("snippet").get("title")
        broadcast_published = create_broadcast_response.get("snippet").get("publishedAt")

        logger.info("Broadcast '{}' ('{}') created ('{}')".format(broadcast_title, broadcast_id, broadcast_published))
        return broadcast_id

    def bind_broadcast(self, broadcast_id, stream_id):
        bind_broadcast_response = self.service.liveBroadcasts().bind(
                                            part="id,contentDetails",
                                            id=broadcast_id,
                                            streamId=stream_id
                                        ).execute()

        bind_id = bind_broadcast_response.get("id")
        if not bind_id:
            logger.error("Bind could not be creaded")
            return None
        
        return bind_id