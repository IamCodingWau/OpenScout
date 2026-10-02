import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from sqlalchemy.orm import Session
from app.models import NotificationLog, Event, EventRelevance
from app.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, channel: Optional[str] = None):
        self.channel = channel or settings.NOTIFICATION_CHANNEL

    def send_event_notification(
        self,
        db: Session,
        event: Event,
        relevance: EventRelevance,
        recipient: Optional[str] = None
    ) -> NotificationLog:
        """
        Dispatches notification for highly relevant events and logs to SQLite.
        Only triggers if relevance.should_notify is True.
        """
        if not relevance.should_notify:
            logger.info(f"Skipping notification for '{event.title}' (should_notify is False)")
            return None

        to_email = recipient or settings.NOTIFY_EMAIL_TO
        pct_match = int(relevance.relevance_score * 100)
        subject = f"OpenScout found an event for you: {event.title}"
        
        body = f"""Hello,

OpenScout found an upcoming open-source event that matches your interests!

==================================================
{event.title}
==================================================
Match Score: {pct_match}%
Date: {event.date}
Location: {event.location} ({'Online' if event.is_online else 'In-Person'})

Why this matches:
{relevance.reason}

Matched Interests:
{', '.join(relevance.matched_interests) if relevance.matched_interests else 'Open Source & Developer Opportunities'}

View Event:
{event.url}
==================================================
— Generated autonomously by OpenScout with {relevance.model_name}
"""

        # Dispatch via selected channel
        if self.channel == "email" and settings.SMTP_USER and settings.SMTP_HOST:
            try:
                msg = MIMEMultipart()
                msg["From"] = settings.SMTP_USER
                msg["To"] = to_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    server.send_message(msg)
                logger.info(f"Notification email sent to {to_email} for event {event.title}")
            except Exception as e:
                logger.error(f"Failed to send email via SMTP: {e}. Falling back to log record.")

        # Always print to console/log as well
        logger.info(f"\n[OPENSCOUT NOTIFICATION DISPATCHED]\nRecipient: {to_email}\nSubject: {subject}\n{body}\n")

        # Persist notification log
        log_entry = NotificationLog(
            event_id=event.id,
            recipient=to_email,
            subject=subject,
            message=body,
            channel=self.channel
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
