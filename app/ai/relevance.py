import json
import re
import logging
from typing import Dict, Any, List, Optional
from app.ai.client import OllamaClient
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are OpenScout's event relevance engine powered by an open-weight AI model.
Your task is to analyze developer and open-source events for a user and determine semantic relevance.

Return ONLY a valid JSON object with the following fields:
{
  "relevance_score": <float between 0.00 and 1.00>,
  "matched_interests": [<list of user interests that matched the event>],
  "reason": "<clear concise explanation of WHY this event is relevant or irrelevant>",
  "should_notify": <boolean true if relevance_score >= notification_threshold and matches location/online, false otherwise>
}

Do not include any conversational preamble or markdown code blocks outside of the JSON."""

def build_prompt(
    interests: List[str],
    locations: List[str],
    title: str,
    description: str,
    topics: List[str],
    event_location: str,
    is_online: bool,
    threshold: float
) -> str:
    return f"""Analyze this event against the user's profile:

[USER PROFILE]
- Interests: {json.dumps(interests)}
- Preferred Locations: {json.dumps(locations)} (Include 'Online' events if requested)
- Notification Relevance Threshold: {threshold}

[EVENT DETAILS]
- Title: {title}
- Description: {description}
- Topics / Tags: {json.dumps(topics)}
- Location: {event_location}
- Online / Virtual: {'Yes' if is_online else 'No'}

Carefully evaluate semantic relevance:
1. Does the event topic match the user's technical interests (e.g. Open Source, Hackathons, AI/ML, DevOps, Cloud, Kubernetes)?
2. Does the event location align with preferred locations (Pune, Mumbai, or Online)?
3. Assign an accurate relevance_score between 0.0 and 1.0.
4. Set should_notify to true ONLY if relevance_score >= {threshold} and the location matches user preferences (or is Online).
"""

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Strip markdown backticks or extra text and parse json safely."""
    text = text.strip()
    # Match json markdown blocks `json ... ` or ` ... `
    match = re.search(r"`(?:json)?\s*(\{.*?\})\s*`", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # Match first opening brace to last closing brace
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    data = json.loads(text)
    
    score = float(data.get("relevance_score", 0.0))
    score = max(0.0, min(1.0, score)) # clamp 0.0 - 1.0
    
    matched = data.get("matched_interests", [])
    if not isinstance(matched, list):
        matched = []
        
    reason = str(data.get("reason", "No reason provided."))
    should_notify = bool(data.get("should_notify", False))
    
    return {
        "relevance_score": round(score, 2),
        "matched_interests": matched,
        "reason": reason,
        "should_notify": should_notify
    }

def simulated_open_weight_fallback(
    interests: List[str],
    locations: List[str],
    title: str,
    description: str,
    topics: List[str],
    event_location: str,
    is_online: bool,
    threshold: float
) -> Dict[str, Any]:
    """
    Transparent local open-weight heuristic simulation.
    Used ONLY when Ollama / local inference daemon is temporarily not running,
    ensuring full demonstrability without relying on closed proprietary APIs.
    """
    all_text = f"{title} {description} {' '.join(topics)}".lower()
    
    matched_interests = []
    for interest in interests:
        interest_lower = interest.lower()
        # Word boundary or substring search
        if interest_lower in all_text or any(part in all_text for part in interest_lower.split()):
            matched_interests.append(interest)
            
    # Location matching
    loc_match = is_online or any(
        loc.lower() in event_location.lower() or (loc.lower() == "online" and is_online)
        for loc in locations
    )

    if not matched_interests:
        score = 0.20
        reason = f"The event '{title}' does not closely align with your listed interests ({', '.join(interests[:3])})."
    else:
        # Base match score
        ratio = len(matched_interests) / max(len(interests), 1)
        base = 0.60 + min(0.35, ratio * 0.5)
        if loc_match:
            base += 0.05
        score = min(0.98, base)
        reason = (
            f"This event directly aligns with your interests in {', '.join(matched_interests[:3])}. "
            f"Held {'online' if is_online else f'in {event_location}'}, matching your location preferences."
        )

    score = round(score, 2)
    should_notify = (score >= threshold) and loc_match

    return {
        "relevance_score": score,
        "matched_interests": matched_interests,
        "reason": reason,
        "should_notify": should_notify,
        "is_simulated": True
    }

class RelevanceEngine:
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    async def evaluate_event(
        self,
        interests: List[str],
        locations: List[str],
        title: str,
        description: str,
        topics: List[str],
        event_location: str,
        is_online: bool,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Evaluate event relevance with open-weight model or fallback simulation."""
        target_threshold = threshold if threshold is not None else settings.NOTIFICATION_THRESHOLD
        prompt = build_prompt(
            interests=interests,
            locations=locations,
            title=title,
            description=description,
            topics=topics,
            event_location=event_location,
            is_online=is_online,
            threshold=target_threshold
        )

        try:
            raw_response = await self.client.generate(prompt=prompt, system=SYSTEM_PROMPT)
            parsed = clean_and_parse_json(raw_response)
            parsed["model_name"] = self.client.model
            parsed["is_simulated"] = False
            return parsed
        except Exception as e:
            logger.warning(f"Ollama local model '{self.client.model}' not reachable ({e}). Using local open-weight engine fallback.")
            fallback = simulated_open_weight_fallback(
                interests=interests,
                locations=locations,
                title=title,
                description=description,
                topics=topics,
                event_location=event_location,
                is_online=is_online,
                threshold=target_threshold
            )
            fallback["model_name"] = f"{self.client.model} (local-fallback)"
            return fallback
