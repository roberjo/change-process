"""
Tests for notification security features.
"""

import pytest
from unittest.mock import Mock, patch
from scripts.communications.notification_manager import (
    URLSecurityValidator,
    URLValidationError,
    TeamsNotification,
    SlackNotification
)

def test_valid_teams_url():
    """Test valid Teams webhook URL."""
    url = "https://webhook.office.com/webhookb2/12345678-1234-1234-1234-123456789012@12345678-1234-1234-1234-123456789012/IncomingWebhook/12345678901234567890123456789012/12345678-1234-1234-1234-123456789012"
    validated_url = URLSecurityValidator.validate_webhook_url(url, 'teams')
    assert validated_url == url

def test_invalid_scheme():
    """Test URL with invalid scheme."""
    url = "http://webhook.office.com/webhook"
    with pytest.raises(URLValidationError, match="Only HTTPS URLs are allowed"):
        URLSecurityValidator.validate_webhook_url(url, 'teams')

def test_ip_address_not_allowed():
    """Test that IP addresses are not allowed."""
    url = "https://192.168.1.1/webhook"
    with pytest.raises(URLValidationError, match="IP addresses are not allowed"):
        URLSecurityValidator.validate_webhook_url(url, 'teams')

def test_unauthorized_domain():
    """Test unauthorized domain."""
    url = "https://malicious-site.com/webhook"
    with pytest.raises(URLValidationError, match="Domain.*is not in the allowed list"):
        URLSecurityValidator.validate_webhook_url(url, 'teams')

def test_suspicious_patterns():
    """Test URLs with suspicious patterns."""
    suspicious_urls = [
        "https://webhook.office.com/file:///etc/passwd",
        "https://webhook.office.com/javascript:alert('xss')",
        "https://webhook.office.com/data:text/html,<script>alert('xss')</script>",
    ]
    
    for url in suspicious_urls:
        with pytest.raises(URLValidationError, match="URL contains suspicious patterns"):
            URLSecurityValidator.validate_webhook_url(url, 'teams')

def test_empty_url():
    """Test empty URL."""
    with pytest.raises(URLValidationError, match="URL cannot be empty"):
        URLSecurityValidator.validate_webhook_url("", 'teams')

def test_invalid_url_format():
    """Test invalid URL format."""
    with pytest.raises(URLValidationError, match="Invalid URL format"):
        URLSecurityValidator.validate_webhook_url("not-a-url", 'teams')

class TestTeamsNotificationSecurity:
    """Test Teams notification security features."""
    
    def test_constructor_with_valid_url(self):
        """Test constructor with valid URL."""
        url = "https://webhook.office.com/webhookb2/12345678-1234-1234-1234-123456789012@12345678-1234-1234-1234-123456789012/IncomingWebhook/12345678901234567890123456789012/12345678-1234-1234-1234-123456789012"
        notification = TeamsNotification(url)
        assert notification.webhook_url == url
    
    def test_constructor_with_invalid_url(self):
        """Test constructor with invalid URL."""
        url = "http://malicious-site.com/webhook"
        with pytest.raises(URLValidationError):
            TeamsNotification(url)
    
    @patch('requests.Session')
    def test_send_with_security_headers(self, mock_session):
        """Test that security headers are set."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.history = []
        mock_session.return_value.post.return_value = mock_response
        
        url = "https://webhook.office.com/webhookb2/12345678-1234-1234-1234-123456789012@12345678-1234-1234-1234-123456789012/IncomingWebhook/12345678901234567890123456789012/12345678-1234-1234-1234-123456789012"
        notification = TeamsNotification(url)
        
        from scripts.communications.notification_manager import NotificationMessage
        message = NotificationMessage(
            title="Test",
            body="Test message",
            priority="normal"
        )
        
        notification._send_impl(message)
        
        # Verify security headers were set
        mock_session.return_value.headers.update.assert_called_with({
            'User-Agent': 'ChangeProcessAutomation/1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Verify security parameters were used
        mock_session.return_value.post.assert_called_with(
            url,
            json=mock_session.return_value.post.call_args[1]['json'],
            timeout=30,
            allow_redirects=False,
            verify=True
        )

class TestSlackNotificationSecurity:
    """Test Slack notification security features."""
    
    def test_constructor_with_valid_url(self):
        """Test constructor with valid URL."""
        url = "https://hooks.slack.com/services/T1234567890/B1234567890/123456789012345678901234"
        notification = SlackNotification(url)
        assert notification.webhook_url == url
    
    def test_constructor_with_invalid_url(self):
        """Test constructor with invalid URL."""
        url = "http://malicious-site.com/webhook"
        with pytest.raises(URLValidationError):
            SlackNotification(url)
    
    @patch('requests.Session')
    def test_send_with_security_headers(self, mock_session):
        """Test that security headers are set."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.history = []
        mock_session.return_value.post.return_value = mock_response
        
        url = "https://hooks.slack.com/services/T1234567890/B1234567890/123456789012345678901234"
        notification = SlackNotification(url)
        
        from scripts.communications.notification_manager import NotificationMessage
        message = NotificationMessage(
            title="Test",
            body="Test message",
            priority="normal"
        )
        
        notification._send_impl(message)
        
        # Verify security headers were set
        mock_session.return_value.headers.update.assert_called_with({
            'User-Agent': 'ChangeProcessAutomation/1.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Verify security parameters were used
        mock_session.return_value.post.assert_called_with(
            url,
            json=mock_session.return_value.post.call_args[1]['json'],
            timeout=30,
            allow_redirects=False,
            verify=True
        ) 