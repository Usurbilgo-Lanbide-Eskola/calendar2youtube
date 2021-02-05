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
        all_live_broadcasts_result = self.service.liveBroadcasts().list(
                                                part="snippet,contentDetails,status",
                                                broadcastType="all", mine=True
                                            ).execute()

        all_live_broadcasts = all_live_broadcasts_result.get('items', [])
        live_broadcasts = [broadcast for broadcast in all_live_broadcasts if not self.is_event_completed(broadcast)]

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
                self.delete_youtube_event(live_broadcast)
            return

    def compare_and_set_event(self, calendar_event, youtube_event):
        # No Calendar and no YouTube event present
        if not youtube_event and not calendar_event:
            logger.debug("Nothing to do, no events")
            return

        # YouTube event created, but deleted in Google Calendar
        if youtube_event and not calendar_event:
            logger.info("Non existing YouTube event created, perhaps we should delete it")
            self.delete_youtube_event(youtube_event)
            return
        
        # Google Calendar present, but not created in YouTube
        if calendar_event and not youtube_event:
            logger.info("Existing event not created, create it")
            self.create_youtube_event(calendar_event)
            return

        # Both present, check if they are the same
        g_title = calendar_event.title
        g_start = calendar_event.start_date
        g_end = calendar_event.end_date

        y_title = youtube_event.get("snippet", {}).get("title", "")
        y_start = youtube_event.get("snippet", {}).get("scheduledStartTime")
        y_end = youtube_event.get("snippet", {}).get("scheduledEndTime")

        if g_title != y_title or \
            iso8601.parse_date(g_start) != iso8601.parse_date(y_start) or \
                iso8601.parse_date(g_end) != iso8601.parse_date(y_end):
            logger.warn("Both events are not synchronized, recreate it")
            if self.delete_youtube_event(youtube_event):
                self.create_youtube_event(calendar_event)
        else:
            logger.debug("Everything is synchronized")

    def create_youtube_event(self, calendar_event):
        title = calendar_event.title
        start = calendar_event.start_date
        end = calendar_event.end_date
        privacy_status = "unlisted" if calendar_event.is_private() else "public"

        broadcast_id = self.create_broadcast(title, start, end, privacy_status)
        self.bind_broadcast(broadcast_id, self.stream_id)

    def delete_youtube_event(self, youtube_event):
        event_title = youtube_event.get("snippet", {}).get("title", "")
        event_id = youtube_event.get("id")

        if self.is_event_removable(youtube_event):
            logger.info(f"The YouTube event '{event_title}' must be deleted")
            self.delete_youtube_event_by_id(event_id)
            return True
        else:
            logger.debug(f"The YouTube event '{event_title}' should not be deleted")

    def delete_youtube_event_by_id(self, broadcast_id):
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

    def create_broadcast(self, title, start_time, end_time, privacy_status="public"):
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
                                            "privacyStatus": privacy_status
                                            
                                        },
                                        "contentDetails": {
                                            "enableAutoStart": True,
                                            "enableAutoStop": True
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

    def is_event_removable(self, youtube_event):
        event_status = youtube_event.get("status", {}).get("lifeCycleStatus")
        event_title = youtube_event.get("snippet", {}).get("title", "")

        if event_status in ["ready"]:
            return True          
        elif event_status in ["complete", "live"]:
            return False
        else:
            logger.warn(f"The YouTube event '{event_title}' has an unknown state: '{event_status}'")
            return False

    def is_event_completed(self, youtube_event):
        event_status = youtube_event.get("status", {}).get("lifeCycleStatus")

        return True if event_status == "complete" else False