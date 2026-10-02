from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class UserProfileBase(BaseModel):
    name: str = "Friend"
    interests: List[str] = [
        "Open Source",
        "Hackathons",
        "Artificial Intelligence",
        "Machine Learning",
        "DevOps",
        "Docker",
        "Kubernetes",
        "Cloud"
    ]
    locations: List[str] = ["Pune", "Mumbai", "Online"]
    notification_threshold: float = 0.80

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EventRelevanceResponse(BaseModel):
    relevance_score: float
    matched_interests: List[str]
    reason: str
    should_notify: bool
    model_name: str
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FeedbackCreate(BaseModel):
    event_id: int
    status: str # 'interested' or 'not_interested'

class FeedbackResponse(BaseModel):
    id: int
    event_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class FeedbackStats(BaseModel):
    interested: int
    not_interested: int

class EventResponse(BaseModel):
    id: int
    title: str
    description: str
    date: str
    location: str
    is_online: bool
    url: str
    source: str
    topics: List[str]
    is_demo: bool
    created_at: datetime
    relevance: Optional[EventRelevanceResponse] = None
    feedback: Optional[FeedbackResponse] = None

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    event_id: Optional[int]
    recipient: str
    subject: str
    message: str
    channel: str
    sent_at: datetime

    class Config:
        from_attributes = True
