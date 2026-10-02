import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.models import UserProfile

# In-memory shared SQLite with StaticPool so all connections share the memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    profile = UserProfile(name="Friend", notification_threshold=0.80)
    profile.interests = ["Open Source", "Hackathons", "DevOps", "Kubernetes"]
    profile.locations = ["Pune", "Mumbai", "Online"]
    db.add(profile)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ai_engine" in data

def test_profile_get_and_put(client):
    get_res = client.get("/api/profile")
    assert get_res.status_code == 200
    profile = get_res.json()
    assert profile["name"] == "Friend"
    assert len(profile["interests"]) > 0

    # Update profile
    updated_payload = {
        "name": "Friend Updated",
        "interests": ["Open Source", "Artificial Intelligence", "DevOps"],
        "locations": ["Pune", "Online"],
        "notification_threshold": 0.85
    }
    put_res = client.put("/api/profile", json=updated_payload)
    assert put_res.status_code == 200
    updated_profile = put_res.json()
    assert updated_profile["name"] == "Friend Updated"
    assert updated_profile["notification_threshold"] == 0.85

def test_event_fetch_and_analyze(client):
    # Fetch demo events
    fetch_res = client.post("/api/events/fetch")
    assert fetch_res.status_code == 200
    assert fetch_res.json()["total_fetched"] >= 4

    # Run AI analysis
    analyze_res = client.post("/api/events/analyze")
    assert analyze_res.status_code == 200
    assert analyze_res.json()["analyzed_count"] >= 4

    # Retrieve events
    events_res = client.get("/api/events")
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 4
    # Highest relevance score should be at top
    assert events[0]["relevance"]["relevance_score"] >= events[-1]["relevance"]["relevance_score"]

def test_feedback_submission(client):
    events_res = client.get("/api/events")
    event_id = events_res.json()[0]["id"]

    fb_res = client.post("/api/feedback", json={"event_id": event_id, "status": "interested"})
    assert fb_res.status_code == 200
    assert fb_res.json()["status"] == "interested"

    stats_res = client.get("/api/feedback/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["interested"] >= 1