from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class EventItem(BaseModel):
    title: str
    description: str
    date: str
    location: str
    is_online: bool
    url: str
    source: str
    topics: List[str]
    is_demo: bool = False

class EventSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the event source adapter."""
        pass

    @abstractmethod
    async def fetch_events(self) -> List[EventItem]:
        """Fetch and return normalized EventItems."""
        pass
