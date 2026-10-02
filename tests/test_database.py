import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import UserProfile, Event, EventRelevance, Feedback, NotificationLog

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_user_profile_create_and_update(test_db):
    profile = UserProfile(name="Test Friend", notification_threshold=0.85)
    profile.interests = ["Open Source", "Kubernetes"]
    profile.locations = ["Pune", "Online"]
    test_db.add(profile)
    test_db.commit()

    saved = test_db.query(UserProfile).first()
    assert saved.name == "Test Friend"
    assert "Kubernetes" in saved.interests
    assert "Pune" in saved.locations
    assert saved.notification_threshold == 0.85

def test_feedback_stats(test_db):
    event = Event(
        title="Sample Meetup",
        description="A great open source meetup",
        date="Oct 20, 2026",
        location="Online",
        is_online=True,
        url="https://example.com/meetup1",
        source="Test"
    )
    test_db.add(event)
    test_db.commit()

    fb = Feedback(event_id=event.id, status="interested")
    test_db.add(fb)
    test_db.commit()

    interested_count = test_db.query(Feedback).filter(Feedback.status == "interested").count()
    not_interested_count = test_db.query(Feedback).filter(Feedback.status == "not_interested").count()

    assert interested_count == 1
    assert not_interested_count == 0