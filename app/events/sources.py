import re
import html
import httpx
import feedparser
import logging
from typing import List
from app.events.base import EventSource, EventItem

logger = logging.getLogger(__name__)

def clean_html(raw_html: str) -> str:
    """Completely strip HTML tags, unescape entities, and collapse whitespace."""
    if not raw_html:
        return ""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    # Unescape HTML entities (&amp;, &#39;, etc.)
    clean = html.unescape(clean)
    # Collapse multiple whitespaces
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

class DemoEventSource(EventSource):
    @property
    def name(self) -> str:
        return "Demo Event Source (Realistic Seed)"

    async def fetch_events(self) -> List[EventItem]:
        """Returns realistic developer and open-source events clearly tagged as Demo Event."""
        return [
            EventItem(
                title="Global Open Source AI Hackathon 2026",
                description="A 48-hour global hackathon building developer tools, autonomous agents, and open-source AI models using Gemma, PyTorch, and Hugging Face.",
                date="October 12, 2026",
                location="Online",
                is_online=True,
                url="https://openscout.dev/demo/open-source-ai-hackathon",
                source="Hacktoberfest / OpenSource Community",
                topics=["Open Source", "Hackathons", "Artificial Intelligence", "Machine Learning"],
                is_demo=True
            ),
            EventItem(
                title="Kubernetes & Cloud Native Pune Meetup #42",
                description="In-person meetup discussing production Kubernetes clusters, GitOps workflows with ArgoCD, and Docker container security in AWS.",
                date="October 18, 2026",
                location="Pune, India",
                is_online=False,
                url="https://openscout.dev/demo/k8s-pune-meetup-42",
                source="CNCF Community Group Pune",
                topics=["DevOps", "Kubernetes", "Docker", "Cloud", "Open Source"],
                is_demo=True
            ),
            EventItem(
                title="Mumbai Open Source Dev & DevOps Summit",
                description="Community gathering of FOSS maintainers, SREs, and cloud architects in Mumbai. Workshops on Linux kernel, OpenTelemetry, and CI/CD pipelines.",
                date="October 25, 2026",
                location="Mumbai, India",
                is_online=False,
                url="https://openscout.dev/demo/mumbai-devops-summit",
                source="Mumbai FOSS Guild",
                topics=["DevOps", "Open Source", "Docker", "Cloud"],
                is_demo=True
            ),
            EventItem(
                title="GenAI & LLM Edge Deployment Workshop",
                description="Hands-on session running open-weight LLMs locally with Ollama, llama.cpp, and vLLM. Exploring quantized inference and private agents.",
                date="November 02, 2026",
                location="Online",
                is_online=True,
                url="https://openscout.dev/demo/genai-edge-workshop",
                source="AI Engineers Global",
                topics=["Artificial Intelligence", "Machine Learning", "Open Source"],
                is_demo=True
            ),
            EventItem(
                title="Hacktoberfest Mumbai Hack Day & Sprint",
                description="Celebrate Hacktoberfest with fellow contributors in Mumbai! Mentors help you make your first pull request to open-source repositories.",
                date="October 28, 2026",
                location="Mumbai, India",
                is_online=False,
                url="https://openscout.dev/demo/hacktoberfest-mumbai-sprint",
                source="Hacktoberfest Local",
                topics=["Open Source", "Hackathons"],
                is_demo=True
            ),
            EventItem(
                title="Pune Cloud & Microservices Summit",
                description="Exploring Kubernetes operators, Terraform infrastructure as code, and distributed tracing in hybrid cloud environments.",
                date="November 15, 2026",
                location="Pune, India",
                is_online=False,
                url="https://openscout.dev/demo/pune-cloud-summit",
                source="Pune Cloud Community",
                topics=["Cloud", "Kubernetes", "DevOps"],
                is_demo=True
            )
        ]


class DevCommunityEventsSource(EventSource):
    @property
    def name(self) -> str:
        return "Dev Challenges & Hackathons (Live)"

    async def fetch_events(self) -> List[EventItem]:
        """
        Fetch developer events and challenge announcements.
        Filters out postmortems and retrospective project submissions.
        """
        events: List[EventItem] = []
        feed_url = "https://dev.to/feed/tag/devchallenge"
        
        # Keywords indicating project submission or postmortem rather than an event announcement
        exclusion_keywords = [
            "i built", "i made", "my submission", "my entry", 
            "postmortem", "one judge gave", "i wrote a justification",
            "same score", "the scoring bugs", "write-up", "retrospective"
        ]

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(feed_url)
                if res.status_code == 200:
                    feed = feedparser.parse(res.text)
                    for entry in feed.entries[:10]:
                        title = clean_html(entry.get("title", ""))
                        title_lower = title.lower()
                        
                        # Filter out past project submissions / retrospective articles
                        if any(kw in title_lower for kw in exclusion_keywords):
                            continue

                        summary = clean_html(entry.get("summary", ""))
                        if any(kw in summary.lower()[:80] for kw in ["my submission", "my entry", "built for the"]):
                            continue

                        if len(summary) > 280:
                            summary = summary[:280] + "..."

                        link = entry.get("link", "")
                        published = entry.get("published", "Upcoming 2026")
                        
                        events.append(EventItem(
                            title=title,
                            description=summary or "Community open-source developer event and challenge.",
                            date=published[:16] if published else "Upcoming 2026",
                            location="Online",
                            is_online=True,
                            url=link,
                            source="DEV Challenges (Live)",
                            topics=["Open Source", "Hackathons"],
                            is_demo=False
                        ))
        except Exception as e:
            logger.warning(f"Could not fetch live Dev.to events feed: {e}")
        return events