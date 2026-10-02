import logging
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.events.base import EventSource, EventItem
from app.events.sources import DemoEventSource, DevCommunityEventsSource
from app.models import Event
from app.config import settings

logger = logging.getLogger(__name__)

class EventCollector:
    def __init__(self, sources: List[EventSource] = None):
        if sources is None:
            sources = []
            if settings.DEMO_MODE:
                sources.append(DemoEventSource())
            # Always add live DevCommunityEventsSource adapter
            sources.append(DevCommunityEventsSource())
        self.sources = sources

    async def collect_and_store(self, db: Session) -> Tuple[int, int]:
        """
        Collects events from all configured sources, de-duplicates by URL,
        and saves new events to SQLite.
        Returns: (new_events_count, total_events_checked)
        """
        total_fetched = 0
        new_added = 0

        for source in self.sources:
            try:
                items = await source.fetch_events()
                total_fetched += len(items)
                for item in items:
                    # De-duplicate by URL
                    existing = db.query(Event).filter(Event.url == item.url).first()
                    if not existing:
                        event = Event(
                            title=item.title,
                            description=item.description,
                            date=item.date,
                            location=item.location,
                            is_online=item.is_online,
                            url=item.url,
                            source=item.source,
                            is_demo=item.is_demo
                        )
                        event.topics = item.topics
                        db.add(event)
                        new_added += 1
                db.commit()
            except Exception as e:
                logger.error(f"Error collecting events from source {source.name}: {e}")
                db.rollback()

        return new_added, total_fetched
