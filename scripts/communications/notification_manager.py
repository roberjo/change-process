"""
Unified notification system for change-process automation.
Supports multiple notification channels with consistent interface.
"""

import logging
import smtplib
import requests
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from email.utils import formataddr, formatdate
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from ipaddress import ip_address, IPv4Address, IPv6Address
import ssl
import socket
import time
import os
import hashlib
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)

class URLValidationError(Exception):
    """Exception raised for URL validation errors."""
    pass

class URLSecurityValidator:
    """Validates URLs for security to prevent SSRF attacks."""
    
    # Whitelist of allowed domains for webhook URLs
    ALLOWED_DOMAINS = {
        'teams': [
            'webhook.office.com',
            'outlook.office.com',
            'outlook.office365.com'
        ],
        'slack': [
            'hooks.slack.com',
            'slack.com'
        ]
    }
    
    # Blocked IP ranges (private, localhost, etc.)
    BLOCKED_IP_RANGES = [
        '127.0.0.0/8',      # localhost
        '10.0.0.0/8',       # private network
        '172.16.0.0/12',    # private network
        '192.168.0.0/16',   # private network
        '169.254.0.0/16',   # link-local
        '::1/128',          # IPv6 localhost
        'fe80::/10',        # IPv6 link-local
        'fc00::/7',         # IPv6 unique local
    ]
    
    @classmethod
    def validate_webhook_url(cls, url: str, service_type: str) -> str:
        """
        Validate webhook URL for security.
        
        Args:
            url: The URL to validate
            service_type: Type of service ('teams', 'slack', etc.)
            
        Returns:
            The validated URL
            
        Raises:
            URLValidationError: If URL is invalid or not allowed
        """
        if not url:
            raise URLValidationError("URL cannot be empty")
        
        # Parse URL
        try:
            parsed_url = urlparse(url)
        except Exception as e:
            raise URLValidationError(f"Invalid URL format: {str(e)}")
        
        # Validate scheme (must be HTTPS)
        if parsed_url.scheme.lower() != 'https':
            raise URLValidationError("Only HTTPS URLs are allowed for security")
        
        # Validate domain
        if not parsed_url.netloc:
            raise URLValidationError("URL must have a valid domain")
        
        # Check if domain is in whitelist
        allowed_domains = cls.ALLOWED_DOMAINS.get(service_type, [])
        if not cls._is_domain_allowed(parsed_url.netloc, allowed_domains):
            raise URLValidationError(
                f"Domain '{parsed_url.netloc}' is not in the allowed list for {service_type}"
            )
        
        # Check for IP addresses (potential SSRF)
        if cls._is_ip_address(parsed_url.netloc):
            raise URLValidationError("IP addresses are not allowed for security reasons")
        
        # Validate URL structure
        if not parsed_url.path:
            raise URLValidationError("URL must have a valid path")
        
        # Check for suspicious patterns
        if cls._contains_suspicious_patterns(url):
            raise URLValidationError("URL contains suspicious patterns")
        
        return url
    
    @classmethod
    def _is_domain_allowed(cls, domain: str, allowed_domains: List[str]) -> bool:
        """Check if domain is in the allowed list."""
        domain_lower = domain.lower()
        return any(
            domain_lower == allowed.lower() or 
            domain_lower.endswith('.' + allowed.lower())
            for allowed in allowed_domains
        )
    
    @classmethod
    def _is_ip_address(cls, host: str) -> bool:
        """Check if host is an IP address."""
        try:
            ip_address(host)
            return True
        except ValueError:
            return False
    
    @classmethod
    def _contains_suspicious_patterns(cls, url: str) -> bool:
        """Check for suspicious patterns in URL."""
        suspicious_patterns = [
            r'file://',
            r'ftp://',
            r'gopher://',
            r'data:',
            r'javascript:',
            r'vbscript:',
            r'about:',
            r'chrome://',
            r'chrome-extension://',
            r'moz-extension://',
            r'view-source:',
            r'blob:',
            r'mediasource:',
            r'filesystem:',
        ]
        
        url_lower = url.lower()
        return any(re.search(pattern, url_lower) for pattern in suspicious_patterns)

class NotificationType(Enum):
    """Supported notification types."""
    TEAMS = "teams"
    SLACK = "slack"
    EMAIL = "email"
    SMS = "sms"  # Future enhancement

class NotificationMessageValidationError(Exception):
    """Exception raised for notification message validation errors."""
    pass

class NotificationMessageValidator:
    """Validates notification message data for integrity and security."""
    
    # Valid priority levels
    VALID_PRIORITIES = {'low', 'normal', 'high', 'urgent'}
    
    # Maximum lengths for various fields
    MAX_TITLE_LENGTH = 200
    MAX_BODY_LENGTH = 4000
    MAX_RECIPIENT_LENGTH = 100
    MAX_ATTACHMENT_LENGTH = 500
    MAX_METADATA_KEY_LENGTH = 50
    MAX_METADATA_VALUE_LENGTH = 500
    
    # Maximum counts
    MAX_RECIPIENTS = 50
    MAX_ATTACHMENTS = 10
    MAX_METADATA_ENTRIES = 20
    
    @classmethod
    def validate_message(cls, message: 'NotificationMessage') -> None:
        """
        Validate a notification message.
        
        Args:
            message: The notification message to validate
            
        Raises:
            NotificationMessageValidationError: If validation fails
        """
        cls._validate_title(message.title)
        cls._validate_body(message.body)
        cls._validate_priority(message.priority)
        cls._validate_recipients(message.recipients)
        cls._validate_attachments(message.attachments)
        cls._validate_metadata(message.metadata)
    
    @classmethod
    def _validate_title(cls, title: str) -> None:
        """Validate message title."""
        if not title:
            raise NotificationMessageValidationError("Title cannot be empty")
        
        if not isinstance(title, str):
            raise NotificationMessageValidationError("Title must be a string")
        
        if len(title.strip()) == 0:
            raise NotificationMessageValidationError("Title cannot be whitespace only")
        
        if len(title) > cls.MAX_TITLE_LENGTH:
            raise NotificationMessageValidationError(
                f"Title too long (max {cls.MAX_TITLE_LENGTH} characters)"
            )
        
        # Check for potentially dangerous characters
        dangerous_chars = ['<script>', '</script>', 'javascript:', 'vbscript:', 'data:']
        title_lower = title.lower()
        for char in dangerous_chars:
            if char in title_lower:
                raise NotificationMessageValidationError(
                    f"Title contains potentially dangerous content: {char}"
                )
    
    @classmethod
    def _validate_body(cls, body: str) -> None:
        """Validate message body."""
        if not body:
            raise NotificationMessageValidationError("Body cannot be empty")
        
        if not isinstance(body, str):
            raise NotificationMessageValidationError("Body must be a string")
        
        if len(body.strip()) == 0:
            raise NotificationMessageValidationError("Body cannot be whitespace only")
        
        if len(body) > cls.MAX_BODY_LENGTH:
            raise NotificationMessageValidationError(
                f"Body too long (max {cls.MAX_BODY_LENGTH} characters)"
            )
        
        # Check for potentially dangerous content
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'data:text/html',
            r'data:application/x-javascript'
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                raise NotificationMessageValidationError(
                    f"Body contains potentially dangerous content matching pattern: {pattern}"
                )
    
    @classmethod
    def _validate_priority(cls, priority: str) -> None:
        """Validate priority level."""
        if not priority:
            raise NotificationMessageValidationError("Priority cannot be empty")
        
        if not isinstance(priority, str):
            raise NotificationMessageValidationError("Priority must be a string")
        
        if priority.lower() not in cls.VALID_PRIORITIES:
            raise NotificationMessageValidationError(
                f"Invalid priority '{priority}'. Must be one of: {', '.join(cls.VALID_PRIORITIES)}"
            )
    
    @classmethod
    def _validate_recipients(cls, recipients: Optional[List[str]]) -> None:
        """Validate recipients list."""
        if recipients is None:
            return  # Optional field
        
        if not isinstance(recipients, list):
            raise NotificationMessageValidationError("Recipients must be a list")
        
        if len(recipients) > cls.MAX_RECIPIENTS:
            raise NotificationMessageValidationError(
                f"Too many recipients (max {cls.MAX_RECIPIENTS})"
            )
        
        for i, recipient in enumerate(recipients):
            if not recipient:
                raise NotificationMessageValidationError(f"Recipient {i+1} cannot be empty")
            
            if not isinstance(recipient, str):
                raise NotificationMessageValidationError(f"Recipient {i+1} must be a string")
            
            if len(recipient) > cls.MAX_RECIPIENT_LENGTH:
                raise NotificationMessageValidationError(
                    f"Recipient {i+1} too long (max {cls.MAX_RECIPIENT_LENGTH} characters)"
                )
            
            # Basic email validation for recipients
            if '@' in recipient:
                cls._validate_email_format(recipient, f"Recipient {i+1}")
    
    @classmethod
    def _validate_attachments(cls, attachments: Optional[List[str]]) -> None:
        """Validate attachments list."""
        if attachments is None:
            return  # Optional field
        
        if not isinstance(attachments, list):
            raise NotificationMessageValidationError("Attachments must be a list")
        
        if len(attachments) > cls.MAX_ATTACHMENTS:
            raise NotificationMessageValidationError(
                f"Too many attachments (max {cls.MAX_ATTACHMENTS})"
            )
        
        for i, attachment in enumerate(attachments):
            if not attachment:
                raise NotificationMessageValidationError(f"Attachment {i+1} cannot be empty")
            
            if not isinstance(attachment, str):
                raise NotificationMessageValidationError(f"Attachment {i+1} must be a string")
            
            if len(attachment) > cls.MAX_ATTACHMENT_LENGTH:
                raise NotificationMessageValidationError(
                    f"Attachment {i+1} too long (max {cls.MAX_ATTACHMENT_LENGTH} characters)"
                )
            
            # Validate attachment path/URL format
            cls._validate_attachment_format(attachment, f"Attachment {i+1}")
    
    @classmethod
    def _validate_metadata(cls, metadata: Optional[Dict[str, Any]]) -> None:
        """Validate metadata dictionary."""
        if metadata is None:
            return  # Optional field
        
        if not isinstance(metadata, dict):
            raise NotificationMessageValidationError("Metadata must be a dictionary")
        
        if len(metadata) > cls.MAX_METADATA_ENTRIES:
            raise NotificationMessageValidationError(
                f"Too many metadata entries (max {cls.MAX_METADATA_ENTRIES})"
            )
        
        for key, value in metadata.items():
            if not key:
                raise NotificationMessageValidationError("Metadata key cannot be empty")
            
            if not isinstance(key, str):
                raise NotificationMessageValidationError("Metadata key must be a string")
            
            if len(key) > cls.MAX_METADATA_KEY_LENGTH:
                raise NotificationMessageValidationError(
                    f"Metadata key '{key}' too long (max {cls.MAX_METADATA_KEY_LENGTH} characters)"
                )
            
            # Validate metadata value
            cls._validate_metadata_value(value, f"Metadata key '{key}'")
    
    @classmethod
    def _validate_email_format(cls, email: str, field_name: str) -> None:
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise NotificationMessageValidationError(
                f"{field_name} has invalid email format: {email}"
            )
    
    @classmethod
    def _validate_attachment_format(cls, attachment: str, field_name: str) -> None:
        """Validate attachment format."""
        # Check for potentially dangerous file paths
        dangerous_patterns = [
            r'\.\./',  # Directory traversal
            r'\.\.\\',  # Windows directory traversal
            r'file://',  # File protocol
            r'data:',   # Data URLs
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, attachment, re.IGNORECASE):
                raise NotificationMessageValidationError(
                    f"{field_name} contains potentially dangerous path: {attachment}"
                )
    
    @classmethod
    def _validate_metadata_value(cls, value: Any, field_name: str) -> None:
        """Validate metadata value."""
        if isinstance(value, str):
            if len(value) > cls.MAX_METADATA_VALUE_LENGTH:
                raise NotificationMessageValidationError(
                    f"{field_name} value too long (max {cls.MAX_METADATA_VALUE_LENGTH} characters)"
                )
        elif isinstance(value, (int, float, bool)):
            # Numeric and boolean values are fine
            pass
        elif value is None:
            # None values are fine
            pass
        else:
            raise NotificationMessageValidationError(
                f"{field_name} has unsupported value type: {type(value).__name__}"
            )

@dataclass
class NotificationMessage:
    """Standardized notification message format."""
    title: str
    body: str
    priority: str = "normal"  # low, normal, high, urgent
    recipients: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate the notification message after initialization."""
        try:
            NotificationMessageValidator.validate_message(self)
        except NotificationMessageValidationError as e:
            logger.error(f"Notification message validation failed: {str(e)}")
            raise
    
    def validate(self) -> None:
        """Validate the notification message."""
        NotificationMessageValidator.validate_message(self)
    
    def sanitize(self) -> 'NotificationMessage':
        """Create a sanitized copy of the message."""
        # Remove leading/trailing whitespace
        sanitized_title = self.title.strip() if self.title else ""
        sanitized_body = self.body.strip() if self.body else ""
        sanitized_priority = self.priority.lower().strip() if self.priority else "normal"
        
        # Sanitize recipients
        sanitized_recipients = None
        if self.recipients:
            sanitized_recipients = [r.strip() for r in self.recipients if r and r.strip()]
        
        # Sanitize attachments
        sanitized_attachments = None
        if self.attachments:
            sanitized_attachments = [a.strip() for a in self.attachments if a and a.strip()]
        
        # Sanitize metadata
        sanitized_metadata = None
        if self.metadata:
            sanitized_metadata = {}
            for key, value in self.metadata.items():
                if key and isinstance(key, str):
                    sanitized_key = key.strip()
                    if sanitized_key:
                        if isinstance(value, str):
                            sanitized_metadata[sanitized_key] = value.strip()
                        else:
                            sanitized_metadata[sanitized_key] = value
        
        return NotificationMessage(
            title=sanitized_title,
            body=sanitized_body,
            priority=sanitized_priority,
            recipients=sanitized_recipients,
            attachments=sanitized_attachments,
            metadata=sanitized_metadata
        )

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
        # Validate webhook URL for security
        try:
            validated_url = URLSecurityValidator.validate_webhook_url(webhook_url, 'teams')
        except URLValidationError as e:
            logger.error(f"Invalid Teams webhook URL: {str(e)}")
            raise
        
        config = {'webhook_url': validated_url, 'enabled': True}
        super().__init__(config)
        self.webhook_url = validated_url
    
    def _send_impl(self, message: NotificationMessage) -> bool:
        """Send notification to Microsoft Teams."""
        if not self.webhook_url:
            logger.error("Teams webhook URL not configured")
            return False
        
        # Re-validate URL before each request for additional security
        try:
            URLSecurityValidator.validate_webhook_url(self.webhook_url, 'teams')
        except URLValidationError as e:
            logger.error(f"Teams webhook URL validation failed: {str(e)}")
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
            # Create session with security settings
            session = requests.Session()
            
            # Configure security headers
            session.headers.update({
                'User-Agent': 'ChangeProcessAutomation/1.0',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            # Make request with security measures
            response = session.post(
                self.webhook_url,
                json=teams_message,
                timeout=30,
                allow_redirects=False,  # Prevent redirects
                verify=True  # Verify SSL certificates
            )
            
            # Check for redirects (should not happen due to allow_redirects=False)
            if response.history:
                logger.warning(f"Unexpected redirect detected: {response.history}")
                return False
            
            response.raise_for_status()
            logger.info(f"Teams notification sent successfully: {message.title}")
            return True
            
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL verification failed for Teams webhook: {str(e)}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for Teams webhook: {str(e)}")
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for Teams webhook: {str(e)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Teams notification: {str(e)}")
            return False
        finally:
            session.close()
    
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
    
    def __init__(self, webhook_url: str):
        # Validate webhook URL for security
        try:
            validated_url = URLSecurityValidator.validate_webhook_url(webhook_url, 'slack')
        except URLValidationError as e:
            logger.error(f"Invalid Slack webhook URL: {str(e)}")
            raise
        
        config = {'webhook_url': validated_url, 'enabled': True}
        super().__init__(config)
        self.webhook_url = validated_url
    
    def _send_impl(self, message: NotificationMessage) -> bool:
        """Send notification to Slack."""
        if not self.webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
        
        # Re-validate URL before each request for additional security
        try:
            URLSecurityValidator.validate_webhook_url(self.webhook_url, 'slack')
        except URLValidationError as e:
            logger.error(f"Slack webhook URL validation failed: {str(e)}")
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
            # Create session with security settings
            session = requests.Session()
            
            # Configure security headers
            session.headers.update({
                'User-Agent': 'ChangeProcessAutomation/1.0',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            # Make request with security measures
            response = session.post(
                self.webhook_url,
                json=slack_message,
                timeout=30,
                allow_redirects=False,  # Prevent redirects
                verify=True  # Verify SSL certificates
            )
            
            # Check for redirects (should not happen due to allow_redirects=False)
            if response.history:
                logger.warning(f"Unexpected redirect detected: {response.history}")
                return False
            
            response.raise_for_status()
            logger.info(f"Slack notification sent successfully: {message.title}")
            return True
            
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL verification failed for Slack webhook: {str(e)}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for Slack webhook: {str(e)}")
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for Slack webhook: {str(e)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
        finally:
            session.close()

class EmailValidationError(Exception):
    """Exception raised for email validation errors."""
    pass

class SMTPConfigurationError(Exception):
    """Exception raised for SMTP configuration errors."""
    pass

class EmailSecurityError(Exception):
    """Exception raised for email security violations."""
    pass

class EmailValidator:
    """Validates email addresses and SMTP configurations for security."""
    
    # RFC 5322 compliant email regex
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$')
    
    # Maximum email length (RFC 5321)
    MAX_EMAIL_LENGTH = 254
    
    # Blocked domains (example - customize as needed)
    BLOCKED_DOMAINS = {
        'example.com',
        'test.com',
        'localhost',
        '127.0.0.1'
    }
    
    # Maximum recipients per email
    MAX_RECIPIENTS = 50
    
    # Maximum attachment size (10MB)
    MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
    
    # Allowed attachment extensions
    ALLOWED_ATTACHMENT_EXTENSIONS = {
        '.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx',
        '.png', '.jpg', '.jpeg', '.gif', '.csv', '.log'
    }
    
    @classmethod
    def validate_email_address(cls, email: str) -> str:
        """Validate a single email address."""
        if not email or not isinstance(email, str):
            raise EmailValidationError("Email address cannot be empty")
        
        email = email.strip().lower()
        
        if len(email) > cls.MAX_EMAIL_LENGTH:
            raise EmailValidationError(f"Email address too long (max {cls.MAX_EMAIL_LENGTH} characters)")
        
        if not cls.EMAIL_REGEX.match(email):
            raise EmailValidationError("Invalid email format")
        
        # Extract domain
        domain = email.split('@')[1]
        
        if domain in cls.BLOCKED_DOMAINS:
            raise EmailValidationError(f"Domain {domain} is not allowed")
        
        # Check for suspicious patterns
        if cls._contains_suspicious_patterns(email):
            raise EmailValidationError("Email contains suspicious patterns")
        
        return email
    
    @classmethod
    def validate_email_list(cls, emails: List[str]) -> List[str]:
        """Validate a list of email addresses."""
        if not emails:
            raise EmailValidationError("Email list cannot be empty")
        
        if len(emails) > cls.MAX_RECIPIENTS:
            raise EmailValidationError(f"Too many recipients (max {cls.MAX_RECIPIENTS})")
        
        validated_emails = []
        for email in emails:
            validated_email = cls.validate_email_address(email)
            if validated_email not in validated_emails:  # Prevent duplicates
                validated_emails.append(validated_email)
        
        return validated_emails
    
    @classmethod
    def validate_smtp_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SMTP configuration."""
        required_fields = ['email_smtp_server', 'email_username', 'email_password']
        
        for field in required_fields:
            if not config.get(field):
                raise SMTPConfigurationError(f"Missing required SMTP field: {field}")
        
        # Validate SMTP server
        smtp_server = config['email_smtp_server']
        if not isinstance(smtp_server, str) or len(smtp_server.strip()) == 0:
            raise SMTPConfigurationError("Invalid SMTP server address")
        
        # Validate port
        port = config.get('email_smtp_port', 587)
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise SMTPConfigurationError("Invalid SMTP port (must be 1-65535)")
        
        # Validate credentials
        username = config['email_username']
        password = config['email_password']
        
        if not cls.validate_email_address(username):
            raise SMTPConfigurationError("Invalid sender email address")
        
        if not password or len(password.strip()) == 0:
            raise SMTPConfigurationError("SMTP password cannot be empty")
        
        return {
            'smtp_server': smtp_server.strip(),
            'smtp_port': port,
            'username': username.strip().lower(),
            'password': password,
            'use_tls': config.get('email_use_tls', True),
            'use_ssl': config.get('email_use_ssl', False),
            'timeout': config.get('email_timeout', 30),
            'max_retries': config.get('email_max_retries', 3),
            'retry_delay': config.get('email_retry_delay', 5)
        }
    
    @classmethod
    def validate_attachment(cls, file_path: str) -> Dict[str, Any]:
        """Validate and analyze attachment file."""
        if not file_path or not isinstance(file_path, str):
            raise EmailValidationError("Invalid attachment path")
        
        path = Path(file_path)
        
        if not path.exists():
            raise EmailValidationError(f"Attachment file not found: {file_path}")
        
        if not path.is_file():
            raise EmailValidationError(f"Attachment path is not a file: {file_path}")
        
        # Check file size
        file_size = path.stat().st_size
        if file_size > cls.MAX_ATTACHMENT_SIZE:
            raise EmailValidationError(f"Attachment too large: {file_size} bytes (max {cls.MAX_ATTACHMENT_SIZE})")
        
        # Check file extension
        extension = path.suffix.lower()
        if extension not in cls.ALLOWED_ATTACHMENT_EXTENSIONS:
            raise EmailValidationError(f"File type not allowed: {extension}")
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        return {
            'path': str(path),
            'name': path.name,
            'size': file_size,
            'mime_type': mime_type,
            'extension': extension
        }
    
    @classmethod
    def _contains_suspicious_patterns(cls, email: str) -> bool:
        """Check for suspicious patterns in email address."""
        suspicious_patterns = [
            r'\.\.',  # Double dots
            r'^\.',   # Starts with dot
            r'\.$',   # Ends with dot
            r'[<>"\']',  # Special characters
            r'[^\x00-\x7F]',  # Non-ASCII characters
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, email):
                return True
        
        return False

class EmailRateLimiter:
    """Rate limiter for email sending to prevent abuse."""
    
    def __init__(self, max_emails_per_hour: int = 100, max_emails_per_minute: int = 10):
        self.max_emails_per_hour = max_emails_per_hour
        self.max_emails_per_minute = max_emails_per_minute
        self.hourly_emails = []
        self.minute_emails = []
    
    def can_send_email(self) -> bool:
        """Check if email can be sent based on rate limits."""
        now = datetime.now()
        
        # Clean old entries
        self.hourly_emails = [t for t in self.hourly_emails if now - t < timedelta(hours=1)]
        self.minute_emails = [t for t in self.minute_emails if now - t < timedelta(minutes=1)]
        
        # Check limits
        if len(self.hourly_emails) >= self.max_emails_per_hour:
            return False
        
        if len(self.minute_emails) >= self.max_emails_per_minute:
            return False
        
        return True
    
    def record_email_sent(self) -> None:
        """Record that an email was sent."""
        now = datetime.now()
        self.hourly_emails.append(now)
        self.minute_emails.append(now)
    
    def get_wait_time(self) -> int:
        """Get wait time in seconds before next email can be sent."""
        now = datetime.now()
        
        # Clean old entries
        self.hourly_emails = [t for t in self.hourly_emails if now - t < timedelta(hours=1)]
        self.minute_emails = [t for t in self.minute_emails if now - t < timedelta(minutes=1)]
        
        if len(self.minute_emails) >= self.max_emails_per_minute:
            oldest = min(self.minute_emails)
            wait_seconds = 60 - (now - oldest).total_seconds()
            return max(0, int(wait_seconds))
        
        return 0

class SecureSMTPConnection:
    """Secure SMTP connection manager with connection pooling and error handling."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self.last_used = None
        self.connection_timeout = 300  # 5 minutes
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def connect(self) -> None:
        """Establish secure SMTP connection."""
        try:
            if self.config['use_ssl']:
                context = ssl.create_default_context()
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
                
                self.connection = smtplib.SMTP_SSL(
                    self.config['smtp_server'],
                    self.config['smtp_port'],
                    timeout=self.config['timeout'],
                    context=context
                )
            else:
                self.connection = smtplib.SMTP(
                    self.config['smtp_server'],
                    self.config['smtp_port'],
                    timeout=self.config['timeout']
                )
                
                if self.config['use_tls']:
                    context = ssl.create_default_context()
                    context.check_hostname = True
                    context.verify_mode = ssl.CERT_REQUIRED
                    self.connection.starttls(context=context)
            
            # Authenticate
            self.connection.login(self.config['username'], self.config['password'])
            self.last_used = datetime.now()
            
            logger.info(f"SMTP connection established to {self.config['smtp_server']}:{self.config['smtp_port']}")
            
        except smtplib.SMTPAuthenticationError as e:
            raise SMTPConfigurationError(f"SMTP authentication failed: {str(e)}")
        except smtplib.SMTPConnectError as e:
            raise SMTPConfigurationError(f"SMTP connection failed: {str(e)}")
        except smtplib.SMTPException as e:
            raise SMTPConfigurationError(f"SMTP error: {str(e)}")
        except socket.timeout as e:
            raise SMTPConfigurationError(f"SMTP connection timeout: {str(e)}")
        except socket.gaierror as e:
            raise SMTPConfigurationError(f"SMTP server resolution failed: {str(e)}")
        except Exception as e:
            raise SMTPConfigurationError(f"Unexpected SMTP error: {str(e)}")
    
    def disconnect(self) -> None:
        """Close SMTP connection."""
        if self.connection:
            try:
                self.connection.quit()
            except Exception as e:
                logger.warning(f"Error closing SMTP connection: {str(e)}")
            finally:
                self.connection = None
    
    def is_connected(self) -> bool:
        """Check if connection is still valid."""
        if not self.connection:
            return False
        
        # Check if connection has timed out
        if self.last_used and datetime.now() - self.last_used > timedelta(seconds=self.connection_timeout):
            return False
        
        try:
            # Test connection with NOOP command
            self.connection.noop()
            self.last_used = datetime.now()
            return True
        except Exception:
            return False
    
    def send_message(self, message: MIMEMultipart) -> None:
        """Send email message."""
        if not self.is_connected():
            self.connect()
        
        try:
            self.connection.send_message(message)
            self.last_used = datetime.now()
        except smtplib.SMTPRecipientsRefused as e:
            raise EmailValidationError(f"Recipient refused: {str(e)}")
        except smtplib.SMTPDataError as e:
            raise EmailSecurityError(f"Message data error: {str(e)}")
        except smtplib.SMTPException as e:
            raise SMTPConfigurationError(f"SMTP send error: {str(e)}")

class EmailNotification(NotificationChannel):
    """Secure email notification channel with comprehensive error handling."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Validate SMTP configuration
        try:
            self.smtp_config = EmailValidator.validate_smtp_config(config)
        except (SMTPConfigurationError, EmailValidationError) as e:
            logger.error(f"Email configuration validation failed: {str(e)}")
            raise
        
        # Initialize rate limiter
        self.rate_limiter = EmailRateLimiter(
            max_emails_per_hour=config.get('email_max_per_hour', 100),
            max_emails_per_minute=config.get('email_max_per_minute', 10)
        )
        
        # Initialize connection manager
        self.connection_manager = SecureSMTPConnection(self.smtp_config)
        
        # Track failed sends for monitoring
        self.failed_sends = []
        self.successful_sends = 0
    
    def _send_impl(self, message: NotificationMessage) -> bool:
        """Send notification via secure email."""
        if not self.enabled:
            logger.warning("Email channel is disabled")
            return False
        
        # Validate recipients
        try:
            validated_recipients = EmailValidator.validate_email_list(message.recipients or [])
        except EmailValidationError as e:
            logger.error(f"Email recipient validation failed: {str(e)}")
            return False
        
        # Check rate limits
        if not self.rate_limiter.can_send_email():
            wait_time = self.rate_limiter.get_wait_time()
            logger.warning(f"Email rate limit exceeded. Wait {wait_time} seconds before retry.")
            return False
        
        # Validate and process attachments
        attachments = []
        if message.attachments:
            for attachment_path in message.attachments:
                try:
                    attachment_info = EmailValidator.validate_attachment(attachment_path)
                    attachments.append(attachment_info)
                except EmailValidationError as e:
                    logger.error(f"Attachment validation failed: {str(e)}")
                    return False
        
        # Create email message
        try:
            email_message = self._create_email_message(message, validated_recipients, attachments)
        except Exception as e:
            logger.error(f"Failed to create email message: {str(e)}")
            return False
        
        # Send email with retry logic
        max_retries = self.smtp_config['max_retries']
        retry_delay = self.smtp_config['retry_delay']
        
        for attempt in range(max_retries + 1):
            try:
                with self.connection_manager as smtp:
                    smtp.send_message(email_message)
                
                # Record successful send
                self.rate_limiter.record_email_sent()
                self.successful_sends += 1
                
                logger.info(f"Email notification sent successfully to {len(validated_recipients)} recipients: {message.title}")
                return True
                
            except (SMTPConfigurationError, EmailValidationError, EmailSecurityError) as e:
                logger.error(f"Email send failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                self._record_failed_send(message, str(e))
                return False
                
            except Exception as e:
                logger.error(f"Unexpected email error (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    self._record_failed_send(message, str(e))
                    return False
        
        return False
    
    def _create_email_message(self, message: NotificationMessage, recipients: List[str], attachments: List[Dict[str, Any]]) -> MIMEMultipart:
        """Create secure email message with proper headers and content."""
        # Create message
        email_msg = MIMEMultipart()
        
        # Set headers with proper formatting
        email_msg['From'] = formataddr(('Change Process Automation', self.smtp_config['username']))
        email_msg['To'] = ', '.join(recipients)
        email_msg['Subject'] = self._sanitize_subject(f"[{message.priority.upper()}] {message.title}")
        email_msg['Date'] = formatdate(localtime=True)
        email_msg['Message-ID'] = self._generate_message_id()
        
        # Add security headers
        email_msg['X-Mailer'] = 'ChangeProcessAutomation/1.0'
        email_msg['X-Priority'] = self._get_priority_header(message.priority)
        email_msg['X-MSMail-Priority'] = self._get_ms_priority_header(message.priority)
        
        # Create email body
        body = self._create_email_body(message)
        email_msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Add attachments
        for attachment_info in attachments:
            try:
                attachment_part = self._create_attachment_part(attachment_info)
                email_msg.attach(attachment_part)
            except Exception as e:
                logger.error(f"Failed to attach file {attachment_info['name']}: {str(e)}")
                raise
        
        return email_msg
    
    def _sanitize_subject(self, subject: str) -> str:
        """Sanitize email subject line."""
        # Remove or escape potentially dangerous characters
        sanitized = re.sub(r'[\r\n\t]', ' ', subject)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length
        if len(sanitized) > 998:  # RFC 2822 limit
            sanitized = sanitized[:995] + "..."
        
        return sanitized
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = hashlib.md5(f"{timestamp}{os.getpid()}".encode()).hexdigest()[:8]
        return f"<{timestamp}.{random_part}@changeprocess>"
    
    def _get_priority_header(self, priority: str) -> str:
        """Get X-Priority header value."""
        priority_map = {
            'low': '5',
            'normal': '3',
            'high': '1',
            'urgent': '1'
        }
        return priority_map.get(priority.lower(), '3')
    
    def _get_ms_priority_header(self, priority: str) -> str:
        """Get X-MSMail-Priority header value."""
        priority_map = {
            'low': 'Low',
            'normal': 'Normal',
            'high': 'High',
            'urgent': 'High'
        }
        return priority_map.get(priority.lower(), 'Normal')
    
    def _create_email_body(self, message: NotificationMessage) -> str:
        """Create formatted email body."""
        body_lines = [
            message.body,
            "",
            "---",
            f"Priority: {message.priority.upper()}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            ""
        ]
        
        # Add metadata if available
        if message.metadata:
            body_lines.append("Additional Information:")
            for key, value in message.metadata.items():
                body_lines.append(f"  {key}: {value}")
            body_lines.append("")
        
        body_lines.extend([
            "This is an automated notification from the Change Process Automation system.",
            "Please do not reply to this email."
        ])
        
        return "\n".join(body_lines)
    
    def _create_attachment_part(self, attachment_info: Dict[str, Any]) -> MIMEBase:
        """Create MIME attachment part."""
        with open(attachment_info['path'], 'rb') as file:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file.read())
        
        # Encode attachment
        encoders.encode_base64(part)
        
        # Set headers
        part.add_header(
            'Content-Disposition',
            'attachment',
            filename=attachment_info['name']
        )
        
        return part
    
    def _record_failed_send(self, message: NotificationMessage, error: str) -> None:
        """Record failed email send for monitoring."""
        failed_record = {
            'timestamp': datetime.now(),
            'title': message.title,
            'recipients': message.recipients,
            'error': error
        }
        
        self.failed_sends.append(failed_record)
        
        # Keep only last 100 failed sends
        if len(self.failed_sends) > 100:
            self.failed_sends = self.failed_sends[-100:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get email sending statistics."""
        return {
            'successful_sends': self.successful_sends,
            'failed_sends': len(self.failed_sends),
            'recent_failures': self.failed_sends[-10:] if self.failed_sends else [],
            'rate_limit_status': {
                'can_send': self.rate_limiter.can_send_email(),
                'wait_time': self.rate_limiter.get_wait_time()
            }
        }

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
            try:
                self.channels[NotificationType.TEAMS] = TeamsNotification(
                    self.config['teams_webhook_url']
                )
            except URLValidationError as e:
                logger.error(f"Failed to setup Teams notification: {str(e)}")
        
        # Slack
        if self.config.get('slack_webhook_url'):
            try:
                self.channels[NotificationType.SLACK] = SlackNotification(
                    self.config['slack_webhook_url']
                )
            except URLValidationError as e:
                logger.error(f"Failed to setup Slack notification: {str(e)}")
        
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