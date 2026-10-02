import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.events.sources import DemoEventSource
from app.events.collector import EventCollector
from app.models import Event

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

@pytest.mark.asyncio
async def test_demo_event_source_content():
    source = DemoEventSource()
    items = await source.fetch_events()
    assert len(items) >= 4
    for it in items:
        assert it.is_demo is True
        assert it.title
        assert it.url
        assert len(it.topics) > 0

@pytest.mark.asyncio
async def test_duplicate_detection(test_db):
    collector = EventCollector(sources=[DemoEventSource()])
    new_1, total_1 = await collector.collect_and_store(test_db)
    assert new_1 > 0
    assert total_1 == new_1

    # Second run with same source should detect 0 new
    new_2, total_2 = await collector.collect_and_store(test_db)
    assert new_2 == 0
    assert total_2 == total_1