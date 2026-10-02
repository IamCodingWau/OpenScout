import os
import logging
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db, init_db
from app.models import UserProfile, Event, EventRelevance, Feedback, NotificationLog
from app.schemas import (
    UserProfileCreate,
    UserProfileResponse,
    EventResponse,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackStats,
    NotificationResponse,
)
from app.ai.client import OllamaClient
from app.ai.relevance import RelevanceEngine
from app.events.collector import EventCollector
from app.notifications.notifier import NotificationService
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("openscout")

app = FastAPI(
    title="OpenScout API",
    description="Personal Open Source Event Notifier powered by Open-Weight AI (Gemma/Ollama)",
    version="1.0.0"
)

# Initialize Database and seed default Profile
@app.on_event("startup")
def on_startup():
    init_db()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).first()
        if not profile:
            profile = UserProfile(
                name="Friend",
                notification_threshold=0.80
            )
            profile.interests = [
                "Open Source",
                "Hackathons",
                "Artificial Intelligence",
                "Machine Learning",
                "DevOps",
                "Docker",
                "Kubernetes",
                "Cloud"
            ]
            profile.locations = ["Pune", "Mumbai", "Online"]
            db.add(profile)
            db.commit()
            logger.info("Default user profile initialized.")
    finally:
        db.close()

# Mount Static directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "OpenScout API is running. Web UI not found."}

# ==================== Health & Model Endpoints ====================

@app.get("/api/health")
async def health_check():
    client = OllamaClient()
    ollama_status = await client.check_health()
    return {
        "status": "healthy",
        "demo_mode": settings.DEMO_MODE,
        "ai_engine": ollama_status
    }

# ==================== User Profile Endpoints ====================

@app.get("/api/profile", response_model=UserProfileResponse)
def get_user_profile(db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.put("/api/profile", response_model=UserProfileResponse)
def update_user_profile(profile_in: UserProfileCreate, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile()
        db.add(profile)
    
    profile.name = profile_in.name
    profile.interests = profile_in.interests
    profile.locations = profile_in.locations
    profile.notification_threshold = profile_in.notification_threshold
    db.commit()
    db.refresh(profile)
    return profile

# ==================== Events & AI Analysis Endpoints ====================

@app.get("/api/events", response_model=List[EventResponse])
def get_events(
    sort_by_relevance: bool = True,
    filter_status: Optional[str] = None, # 'all', 'interested', 'not_interested', 'unreviewed'
    db: Session = Depends(get_db)
):
    query = db.query(Event)
    events = query.all()

    if filter_status == "interested":
        events = [e for e in events if e.feedback and e.feedback.status == "interested"]
    elif filter_status == "not_interested":
        events = [e for e in events if e.feedback and e.feedback.status == "not_interested"]
    elif filter_status == "unreviewed":
        events = [e for e in events if not e.feedback]

    if sort_by_relevance:
        # Sort by relevance_score descending, None at bottom
        events = sorted(
            events,
            key=lambda e: (e.relevance.relevance_score if e.relevance else -1.0),
            reverse=True
        )
    return events

@app.post("/api/events/fetch")
async def fetch_events(db: Session = Depends(get_db)):
    collector = EventCollector()
    new_added, total_fetched = await collector.collect_and_store(db)
    return {
        "message": f"Event collection complete. Fetched {total_fetched} items ({new_added} new).",
        "new_added": new_added,
        "total_fetched": total_fetched
    }

@app.post("/api/events/analyze")
async def analyze_events_relevance(db: Session = Depends(get_db)):
    """
    Run open-weight AI relevance analysis on all stored events
    against current user profile. Also dispatches notifications for qualifying events.
    """
    profile = db.query(UserProfile).first()
    if not profile:
        raise HTTPException(status_code=400, detail="User profile must exist first.")

    events = db.query(Event).all()
    if not events:
        # Auto-fetch if DB is empty
        collector = EventCollector()
        await collector.collect_and_store(db)
        events = db.query(Event).all()

    engine = RelevanceEngine()
    notifier = NotificationService()
    analyzed_count = 0
    notifications_sent = 0

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

        # Update or create relevance record
        existing_rel = db.query(EventRelevance).filter(EventRelevance.event_id == ev.id).first()
        if existing_rel:
            existing_rel.relevance_score = relevance_data["relevance_score"]
            existing_rel.matched_interests = relevance_data["matched_interests"]
            existing_rel.reason = relevance_data["reason"]
            existing_rel.should_notify = relevance_data["should_notify"]
            existing_rel.model_name = relevance_data["model_name"]
            db.commit()
            rel_obj = existing_rel
        else:
            rel_obj = EventRelevance(
                event_id=ev.id,
                relevance_score=relevance_data["relevance_score"],
                reason=relevance_data["reason"],
                should_notify=relevance_data["should_notify"],
                model_name=relevance_data["model_name"]
            )
            rel_obj.matched_interests = relevance_data["matched_interests"]
            db.add(rel_obj)
            db.commit()

        # Check notification
        if rel_obj.should_notify:
            # Check if already notified for this event
            prior_notif = db.query(NotificationLog).filter(NotificationLog.event_id == ev.id).first()
            if not prior_notif:
                notifier.send_event_notification(db=db, event=ev, relevance=rel_obj)
                notifications_sent += 1

        analyzed_count += 1

    return {
        "message": f"Successfully analyzed {analyzed_count} events using open AI model.",
        "analyzed_count": analyzed_count,
        "notifications_sent": notifications_sent
    }

# ==================== Feedback Endpoints ====================

@app.post("/api/feedback", response_model=FeedbackResponse)
def submit_feedback(fb_in: FeedbackCreate, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == fb_in.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if fb_in.status not in ["interested", "not_interested"]:
        raise HTTPException(status_code=400, detail="Status must be 'interested' or 'not_interested'")

    feedback = db.query(Feedback).filter(Feedback.event_id == fb_in.event_id).first()
    if feedback:
        feedback.status = fb_in.status
    else:
        feedback = Feedback(event_id=fb_in.event_id, status=fb_in.status)
        db.add(feedback)

    db.commit()
    db.refresh(feedback)
    return feedback

@app.get("/api/feedback/stats", response_model=FeedbackStats)
def get_feedback_stats(db: Session = Depends(get_db)):
    interested = db.query(Feedback).filter(Feedback.status == "interested").count()
    not_interested = db.query(Feedback).filter(Feedback.status == "not_interested").count()
    return FeedbackStats(interested=interested, not_interested=not_interested)

# ==================== Notification History Endpoints ====================

@app.get("/api/notifications", response_model=List[NotificationResponse])
def get_notifications(db: Session = Depends(get_db)):
    logs = db.query(NotificationLog).order_by(desc(NotificationLog.sent_at)).all()
    return logs
