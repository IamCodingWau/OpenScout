import asyncio
import time
import argparse
import logging
from app.database import SessionLocal, init_db
from app.models import UserProfile, Event, EventRelevance, NotificationLog
from app.events.collector import EventCollector
from app.ai.relevance import RelevanceEngine
from app.notifications.notifier import NotificationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("openscout.scheduler")

async def run_sync_cycle():
    """
    Executes a single end-to-end sync cycle:
    1. Fetch events & de-duplicate into SQLite.
    2. Retrieve active User Profile interests & locations.
    3. Run Open-Weight AI relevance scoring on all events.
    4. Trigger notification if relevance >= threshold.
    """
    logger.info("--- Starting OpenScout Sync Cycle ---")
    init_db()
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).first()
        if not profile:
            logger.warning("No user profile found. Run the web UI first to create a profile.")
            return

        # 1. Fetch & Store
        collector = EventCollector()
        new_added, total_fetched = await collector.collect_and_store(db)
        logger.info(f"Collector: Fetched {total_fetched} events ({new_added} new saved to DB).")

        # 2. AI Scoring
        engine = RelevanceEngine()
        notifier = NotificationService()
        events = db.query(Event).all()
        notified_count = 0

        for ev in events:
            relevance_data = await engine.evaluate_event(
                interests=profile.interests,
                locations=profile.locations,
                title=ev.title,
                description=ev.description,
                topics=ev.topics,
                event_location=ev.location,
                is_online=ev.is_online,
                threshold=profile.notification_threshold
            )

            # Upsert relevance
            rel = db.query(EventRelevance).filter(EventRelevance.event_id == ev.id).first()
            if rel:
                rel.relevance_score = relevance_data["relevance_score"]
                rel.matched_interests = relevance_data["matched_interests"]
                rel.reason = relevance_data["reason"]
                rel.should_notify = relevance_data["should_notify"]
                rel.model_name = relevance_data["model_name"]
            else:
                rel = EventRelevance(
                    event_id=ev.id,
                    relevance_score=relevance_data["relevance_score"],
                    reason=relevance_data["reason"],
                    should_notify=relevance_data["should_notify"],
                    model_name=relevance_data["model_name"]
                )
                rel.matched_interests = relevance_data["matched_interests"]
                db.add(rel)
            db.commit()

            # Check notification
            if rel.should_notify:
                prior_notif = db.query(NotificationLog).filter(NotificationLog.event_id == ev.id).first()
                if not prior_notif:
                    notifier.send_event_notification(db=db, event=ev, relevance=rel)
                    notified_count += 1

        logger.info(f"Sync Cycle Complete: Scored {len(events)} events. Dispatched {notified_count} notifications.")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="OpenScout Autonomous Event Scheduler")
    parser.add_argument("--once", action="store_true", help="Run a single sync cycle and exit")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds between sync runs (default 3600)")
    args = parser.parse_args()

    if args.once:
        asyncio.run(run_sync_cycle())
    else:
        logger.info(f"OpenScout Scheduler starting in loop mode (every {args.interval} seconds)...")
        while True:
            try:
                asyncio.run(run_sync_cycle())
            except Exception as e:
                logger.error(f"Error in sync cycle: {e}")
            time.sleep(args.interval)

if __name__ == "__main__":
    main()