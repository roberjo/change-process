"""
Unified notification system for change-process automation.
Supports multiple notification channels with consistent interface.
"""

import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Supported notification types."""
    TEAMS = "teams"
    SLACK = "slack"
    EMAIL = "email"
    SMS = "sms"  # Future enhancement

@dataclass
class NotificationMessage:
    """Standardized notification message format."""
    title: str
    body: str
    priority: str = "normal"  # low, normal, high, urgent
    recipients: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class NotificationChannel:
    """Base class for notification channels."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
    
    def send(self, message: NotificationMessage) -> bool:
        """Send notification message."""
        if not self.enabled:
            logger.warning(f"Channel {self.__class__.__name__} is disabled")
            return False
        
        try:
            return self._send_impl(message)
        except Exception as e:
            logger.error(f"Failed to send notification via {self.__class__.__name__}: {str(e)}")
            return False
    
    def _send_impl(self, message: NotificationMessage) -> bool:
        """Implementation specific to each channel."""
        raise NotImplementedError

class TeamsNotification(NotificationChannel):
    """Microsoft Teams notification channel."""
    
    def __init__(self, webhook_url: str):
        super().__init__(None)
        self.webhook_url = webhook_url
    
    def _send_impl(self, message: NotificationMessage) -> bool:
        """Send notification to Microsoft Teams."""
        if not self.webhook_url:
            logger.error("Teams webhook URL not configured")
            return False
        
        # Create Teams message card
        teams_message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": self._get_theme_color(message.priority),
            "summary": message.title,
            "sections": [{
                "activityTitle": message.title,
                "activitySubtitle": f"Priority: {message.priority.upper()}",
                "text": message.body,
                "markdown": True
            }]
        }
        
        # Add metadata if available
        if message.metadata:
            facts = []
            for key, value in message.metadata.items():
                facts.append({"name": key, "value": str(value)})
            teams_message["sections"][0]["facts"] = facts
        
        try:
            response = requests.post(
                self.webhook_url,
                json=teams_message,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Teams notification sent successfully: {message.title}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Teams notification: {str(e)}")
            return False
    
    def _get_theme_color(self, priority: str) -> str:
        """Get theme color based on priority."""
        colors = {
            'low': '00FF00',      # Green
            'normal': '0078D4',   # Blue
            'high': 'FF8C00',     # Orange
            'urgent': 'D13438'    # Red
        }
        return colors.get(priority.lower(), colors['normal'])

class SlackNotification(NotificationChannel):
    """Slack notification channel."""
    
    def _send_impl(self, message: NotificationMessage) -> bool:
        """Send notification to Slack."""
        webhook_url = self.config.get('webhook_url')
        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
        
        # Create Slack message
        slack_message = {
            "text": message.title,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": message.title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message.body
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Priority: {message.priority.upper()}"
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=slack_message,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Slack notification sent successfully: {message.title}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False

class EmailNotification(NotificationChannel):
    """Email notification channel."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get('email_smtp_server')
        self.smtp_port = config.get('email_smtp_port', 587)
        self.username = config.get('email_username')
        self.password = config.get('email_password')
    
    def _send_impl(self, message: NotificationMessage) -> bool:
        """Send notification via email."""
        if not self.enabled:
            logger.warning(f"Email channel is disabled")
            return False
        
        if not self.smtp_server or not self.username or not self.password:
            logger.error("Email configuration incomplete")
            return False
        
        if not message.recipients:
            logger.error("No email recipients specified")
            return False
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ', '.join(message.recipients)
        msg['Subject'] = f"[{message.priority.upper()}] {message.title}"
        
        # Add body
        body = f"""
{message.body}

---
Priority: {message.priority.upper()}
        """
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent successfully: {message.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False

class NotificationManager:
    """Manages multiple notification channels."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize notification manager with configuration."""
        self.config = config
        self.channels = {}
        self._setup_channels()
    
    def _setup_channels(self) -> None:
        """Setup notification channels based on configuration."""
        # Teams
        if self.config.get('teams_webhook_url'):
            self.channels[NotificationType.TEAMS] = TeamsNotification(
                self.config['teams_webhook_url']
            )
        
        # Email
        if self.config.get('email_smtp_server'):
            self.channels[NotificationType.EMAIL] = EmailNotification(
                self.config
            )
    
    def send_notification(
        self,
        message: NotificationMessage,
        channels: Optional[List[NotificationType]] = None
    ) -> Dict[NotificationType, bool]:
        """Send notification to specified channels."""
        if channels is None:
            channels = list(self.channels.keys())
        
        results = {}
        for channel_type in channels:
            if channel_type in self.channels:
                results[channel_type] = self.channels[channel_type].send(message)
            else:
                logger.warning(f"Channel {channel_type.value} not configured")
                results[channel_type] = False
        
        return results
    
    def send_change_notification(
        self,
        change_number: str,
        status: str,
        title: str,
        description: str,
        priority: str = "normal",
        channels: Optional[List[NotificationType]] = None
    ) -> Dict[NotificationType, bool]:
        """Send standardized change notification."""
        message = NotificationMessage(
            title=f"Change Request {change_number}: {title}",
            body=f"""
Status: {status}
Description: {description}

Change Number: {change_number}
            """,
            priority=priority,
            metadata={
                "Change Number": change_number,
                "Status": status,
                "Timestamp": str(datetime.now())
            }
        )
        
        return self.send_notification(message, channels)
    
    def send_deployment_notification(
        self,
        version: str,
        environment: str,
        status: str,
        details: str,
        priority: str = "normal",
        channels: Optional[List[NotificationType]] = None
    ) -> Dict[NotificationType, bool]:
        """Send standardized deployment notification."""
        message = NotificationMessage(
            title=f"Deployment {status}: {version} to {environment}",
            body=f"""
Version: {version}
Environment: {environment}
Status: {status}
Details: {details}
            """,
            priority=priority,
            metadata={
                "Version": version,
                "Environment": environment,
                "Status": status,
                "Timestamp": str(datetime.now())
            }
        )
        
        return self.send_notification(message, channels) 