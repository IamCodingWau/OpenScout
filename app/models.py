import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="Friend")
    _interests = Column("interests", Text, default="[]")
    _locations = Column("locations", Text, default="[]")
    notification_threshold = Column(Float, default=0.80)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def interests(self):
        try:
            return json.loads(self._interests or "[]")
        except Exception:
            return []

    @interests.setter
    def interests(self, value):
        self._interests = json.dumps(value)

    @property
    def locations(self):
        try:
            return json.loads(self._locations or "[]")
        except Exception:
            return []

    @locations.setter
    def locations(self, value):
        self._locations = json.dumps(value)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    date = Column(String(100), nullable=False)
    location = Column(String(255), nullable=False)
    is_online = Column(Boolean, default=False)
    url = Column(String(500), unique=True, index=True)
    source = Column(String(100), nullable=False)
    _topics = Column("topics", Text, default="[]")
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    relevance = relationship("EventRelevance", back_populates="event", uselist=False, cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="event", uselist=False, cascade="all, delete-orphan")

    @property
    def topics(self):
        try:
            return json.loads(self._topics or "[]")
        except Exception:
            return []

    @topics.setter
    def topics(self, value):
        self._topics = json.dumps(value)


class EventRelevance(Base):
    __tablename__ = "event_relevance"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), unique=True, nullable=False)
    relevance_score = Column(Float, nullable=False)
    _matched_interests = Column("matched_interests", Text, default="[]")
    reason = Column(Text, nullable=False)
    should_notify = Column(Boolean, default=False)
    model_name = Column(String(100), nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="relevance")

    @property
    def matched_interests(self):
        try:
            return json.loads(self._matched_interests or "[]")
        except Exception:
            return []

    @matched_interests.setter
    def matched_interests(self, value):
        self._matched_interests = json.dumps(value)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), unique=True, nullable=False)
    status = Column(String(50), nullable=False) # 'interested' or 'not_interested'
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="feedback")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(50), default="log")
    sent_at = Column(DateTime, default=datetime.utcnow)
