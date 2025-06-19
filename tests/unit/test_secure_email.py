"""
Tests for secure email functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from scripts.communications.notification_manager import (
    EmailValidator,
    EmailRateLimiter,
    SecureSMTPConnection,
    EmailNotification,
    EmailValidationError,
    SMTPConfigurationError,
    EmailSecurityError,
    NotificationMessage
)


class TestEmailValidator:
    """Test email validation functionality."""
    
    def test_validate_email_address_valid(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com",
            "test@sub.domain.com"
        ]
        
        for email in valid_emails:
            result = EmailValidator.validate_email_address(email)
            assert result == email.lower().strip()
    
    def test_validate_email_address_invalid(self):
        """Test validation of invalid email addresses."""
        invalid_emails = [
            "",  # Empty
            "invalid",  # No @
            "@domain.com",  # No local part
            "user@",  # No domain
            "user@.com",  # No domain name
            "user..name@domain.com",  # Double dots
            ".user@domain.com",  # Starts with dot
            "user.@domain.com",  # Ends with dot
            "user@domain..com",  # Double dots in domain
            "user@domain.com.",  # Ends with dot
            "user@localhost",  # Blocked domain
            "user@127.0.0.1",  # Blocked domain
            "user@example.com" + "a" * 300,  # Too long
        ]
        
        for email in invalid_emails:
            with pytest.raises(EmailValidationError):
                EmailValidator.validate_email_address(email)
    
    def test_validate_email_list_valid(self):
        """Test validation of valid email lists."""
        emails = ["user1@example.com", "user2@domain.org"]
        result = EmailValidator.validate_email_list(emails)
        assert result == ["user1@example.com", "user2@domain.org"]
    
    def test_validate_email_list_duplicates(self):
        """Test that duplicates are removed from email lists."""
        emails = ["user@example.com", "USER@EXAMPLE.COM", "user@example.com"]
        result = EmailValidator.validate_email_list(emails)
        assert result == ["user@example.com"]
    
    def test_validate_email_list_too_many(self):
        """Test validation fails with too many recipients."""
        emails = [f"user{i}@example.com" for i in range(51)]
        with pytest.raises(EmailValidationError, match="Too many recipients"):
            EmailValidator.validate_email_list(emails)
    
    def test_validate_smtp_config_valid(self):
        """Test validation of valid SMTP configuration."""
        config = {
            'email_smtp_server': 'smtp.example.com',
            'email_smtp_port': 587,
            'email_username': 'user@example.com',
            'email_password': 'password123',
            'email_use_tls': True,
            'email_timeout': 30
        }
        
        result = EmailValidator.validate_smtp_config(config)
        assert result['smtp_server'] == 'smtp.example.com'
        assert result['smtp_port'] == 587
        assert result['username'] == 'user@example.com'
        assert result['password'] == 'password123'
        assert result['use_tls'] is True
        assert result['timeout'] == 30
    
    def test_validate_smtp_config_missing_fields(self):
        """Test validation fails with missing required fields."""
        config = {
            'email_smtp_server': 'smtp.example.com',
            # Missing username and password
        }
        
        with pytest.raises(SMTPConfigurationError, match="Missing required SMTP field"):
            EmailValidator.validate_smtp_config(config)
    
    def test_validate_smtp_config_invalid_port(self):
        """Test validation fails with invalid port."""
        config = {
            'email_smtp_server': 'smtp.example.com',
            'email_smtp_port': 70000,  # Invalid port
            'email_username': 'user@example.com',
            'email_password': 'password123'
        }
        
        with pytest.raises(SMTPConfigurationError, match="Invalid SMTP port"):
            EmailValidator.validate_smtp_config(config)
    
    def test_validate_attachment_valid(self):
        """Test validation of valid attachment."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"Test content")
            f.flush()
            
            try:
                result = EmailValidator.validate_attachment(f.name)
                assert result['path'] == f.name
                assert result['name'] == os.path.basename(f.name)
                assert result['size'] > 0
                assert result['mime_type'] == 'text/plain'
                assert result['extension'] == '.txt'
            finally:
                os.unlink(f.name)
    
    def test_validate_attachment_file_not_found(self):
        """Test validation fails for non-existent file."""
        with pytest.raises(EmailValidationError, match="Attachment file not found"):
            EmailValidator.validate_attachment("/nonexistent/file.txt")
    
    def test_validate_attachment_disallowed_extension(self):
        """Test validation fails for disallowed file extensions."""
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            f.write(b"Test content")
            f.flush()
            
            try:
                with pytest.raises(EmailValidationError, match="File type not allowed"):
                    EmailValidator.validate_attachment(f.name)
            finally:
                os.unlink(f.name)
    
    def test_validate_attachment_too_large(self):
        """Test validation fails for files that are too large."""
        # Create a file larger than the limit
        large_content = b"x" * (EmailValidator.MAX_ATTACHMENT_SIZE + 1024)
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(large_content)
            f.flush()
            
            try:
                with pytest.raises(EmailValidationError, match="Attachment too large"):
                    EmailValidator.validate_attachment(f.name)
            finally:
                os.unlink(f.name)


class TestEmailRateLimiter:
    """Test email rate limiting functionality."""
    
    def test_can_send_email_initially(self):
        """Test that emails can be sent initially."""
        limiter = EmailRateLimiter(max_emails_per_hour=10, max_emails_per_minute=2)
        assert limiter.can_send_email() is True
    
    def test_rate_limit_minute(self):
        """Test minute-based rate limiting."""
        limiter = EmailRateLimiter(max_emails_per_hour=100, max_emails_per_minute=2)
        
        # Send 2 emails (at limit)
        limiter.record_email_sent()
        limiter.record_email_sent()
        
        # Should not be able to send more
        assert limiter.can_send_email() is False
    
    def test_rate_limit_hour(self):
        """Test hour-based rate limiting."""
        limiter = EmailRateLimiter(max_emails_per_hour=2, max_emails_per_minute=10)
        
        # Send 2 emails (at limit)
        limiter.record_email_sent()
        limiter.record_email_sent()
        
        # Should not be able to send more
        assert limiter.can_send_email() is False
    
    def test_get_wait_time(self):
        """Test wait time calculation."""
        limiter = EmailRateLimiter(max_emails_per_hour=100, max_emails_per_minute=1)
        
        # Send one email
        limiter.record_email_sent()
        
        # Should have to wait
        assert limiter.can_send_email() is False
        wait_time = limiter.get_wait_time()
        assert wait_time > 0
        assert wait_time <= 60


class TestSecureSMTPConnection:
    """Test secure SMTP connection management."""
    
    def test_connection_context_manager(self):
        """Test connection context manager."""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'password123',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp_instance = Mock()
            mock_smtp.return_value = mock_smtp_instance
            
            with SecureSMTPConnection(config) as connection:
                assert connection.connection is not None
                mock_smtp.assert_called_once()
                mock_smtp_instance.starttls.assert_called_once()
                mock_smtp_instance.login.assert_called_once()
            
            # Should be disconnected after context exit
            mock_smtp_instance.quit.assert_called_once()
    
    def test_connection_ssl(self):
        """Test SSL connection."""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 465,
            'username': 'user@example.com',
            'password': 'password123',
            'use_tls': False,
            'use_ssl': True,
            'timeout': 30
        }
        
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_smtp_instance = Mock()
            mock_smtp_ssl.return_value = mock_smtp_instance
            
            with SecureSMTPConnection(config) as connection:
                mock_smtp_ssl.assert_called_once()
                mock_smtp_instance.login.assert_called_once()
    
    def test_connection_authentication_error(self):
        """Test authentication error handling."""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'wrong_password',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp_instance = Mock()
            mock_smtp.return_value = mock_smtp_instance
            mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
            
            with pytest.raises(SMTPConfigurationError, match="SMTP authentication failed"):
                with SecureSMTPConnection(config):
                    pass
    
    def test_connection_timeout_error(self):
        """Test connection timeout error handling."""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'password123',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = socket.timeout("Connection timeout")
            
            with pytest.raises(SMTPConfigurationError, match="SMTP connection timeout"):
                with SecureSMTPConnection(config):
                    pass
    
    def test_is_connected(self):
        """Test connection status checking."""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'password123',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30
        }
        
        connection = SecureSMTPConnection(config)
        
        # Initially not connected
        assert connection.is_connected() is False
        
        # Mock connection
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp_instance = Mock()
            mock_smtp.return_value = mock_smtp_instance
            mock_smtp_instance.noop.return_value = (250, "OK")
            
            connection.connect()
            assert connection.is_connected() is True
    
    def test_send_message(self):
        """Test sending message through connection."""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'user@example.com',
            'password': 'password123',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp_instance = Mock()
            mock_smtp.return_value = mock_smtp_instance
            mock_smtp_instance.noop.return_value = (250, "OK")
            
            with SecureSMTPConnection(config) as connection:
                message = Mock()
                connection.send_message(message)
                mock_smtp_instance.send_message.assert_called_once_with(message)


class TestEmailNotification:
    """Test secure email notification functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'email_smtp_server': 'smtp.example.com',
            'email_smtp_port': 587,
            'email_username': 'user@example.com',
            'email_password': 'password123',
            'email_use_tls': True,
            'email_use_ssl': False,
            'email_timeout': 30,
            'email_max_retries': 3,
            'email_retry_delay': 5,
            'email_max_per_hour': 100,
            'email_max_per_minute': 10,
            'enabled': True
        }
        
        self.message = NotificationMessage(
            title="Test Email",
            body="This is a test email",
            priority="normal",
            recipients=["recipient@example.com"],
            metadata={"test": "value"}
        )
    
    def test_email_notification_init(self):
        """Test email notification initialization."""
        notification = EmailNotification(self.config)
        assert notification.enabled is True
        assert notification.smtp_config['smtp_server'] == 'smtp.example.com'
        assert notification.rate_limiter is not None
    
    def test_email_notification_init_invalid_config(self):
        """Test initialization with invalid configuration."""
        invalid_config = {
            'email_smtp_server': 'smtp.example.com',
            # Missing required fields
        }
        
        with pytest.raises(SMTPConfigurationError):
            EmailNotification(invalid_config)
    
    @patch('scripts.communications.notification_manager.SecureSMTPConnection')
    def test_send_email_success(self, mock_connection_class):
        """Test successful email sending."""
        mock_connection = Mock()
        mock_connection_class.return_value.__enter__.return_value = mock_connection
        
        notification = EmailNotification(self.config)
        result = notification._send_impl(self.message)
        
        assert result is True
        mock_connection.send_message.assert_called_once()
    
    def test_send_email_no_recipients(self):
        """Test email sending with no recipients."""
        message = NotificationMessage(
            title="Test Email",
            body="This is a test email",
            priority="normal",
            recipients=[]  # No recipients
        )
        
        notification = EmailNotification(self.config)
        result = notification._send_impl(message)
        
        assert result is False
    
    def test_send_email_invalid_recipients(self):
        """Test email sending with invalid recipients."""
        message = NotificationMessage(
            title="Test Email",
            body="This is a test email",
            priority="normal",
            recipients=["invalid-email"]  # Invalid email
        )
        
        notification = EmailNotification(self.config)
        result = notification._send_impl(message)
        
        assert result is False
    
    def test_send_email_rate_limited(self):
        """Test email sending when rate limited."""
        # Create rate limiter that's already at limit
        with patch.object(EmailRateLimiter, 'can_send_email', return_value=False):
            notification = EmailNotification(self.config)
            result = notification._send_impl(self.message)
            
            assert result is False
    
    @patch('scripts.communications.notification_manager.SecureSMTPConnection')
    def test_send_email_with_attachments(self, mock_connection_class):
        """Test email sending with attachments."""
        mock_connection = Mock()
        mock_connection_class.return_value.__enter__.return_value = mock_connection
        
        # Create temporary file for attachment
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"Test attachment content")
            f.flush()
            
            try:
                message = NotificationMessage(
                    title="Test Email",
                    body="This is a test email with attachment",
                    priority="normal",
                    recipients=["recipient@example.com"],
                    attachments=[f.name]
                )
                
                notification = EmailNotification(self.config)
                result = notification._send_impl(message)
                
                assert result is True
                mock_connection.send_message.assert_called_once()
                
                # Check that attachment was processed
                sent_message = mock_connection.send_message.call_args[0][0]
                assert len(sent_message.get_payload()) > 1  # Should have body + attachment
                
            finally:
                os.unlink(f.name)
    
    @patch('scripts.communications.notification_manager.SecureSMTPConnection')
    def test_send_email_retry_logic(self, mock_connection_class):
        """Test email sending retry logic."""
        mock_connection = Mock()
        mock_connection.send_message.side_effect = [
            Exception("Temporary error"),  # First attempt fails
            Exception("Temporary error"),  # Second attempt fails
            None  # Third attempt succeeds
        ]
        mock_connection_class.return_value.__enter__.return_value = mock_connection
        
        notification = EmailNotification(self.config)
        result = notification._send_impl(self.message)
        
        assert result is True
        assert mock_connection.send_message.call_count == 3
    
    @patch('scripts.communications.notification_manager.SecureSMTPConnection')
    def test_send_email_max_retries_exceeded(self, mock_connection_class):
        """Test email sending when max retries are exceeded."""
        mock_connection = Mock()
        mock_connection.send_message.side_effect = Exception("Persistent error")
        mock_connection_class.return_value.__enter__.return_value = mock_connection
        
        notification = EmailNotification(self.config)
        result = notification._send_impl(self.message)
        
        assert result is False
        assert mock_connection.send_message.call_count == 4  # Initial + 3 retries
    
    def test_create_email_message(self):
        """Test email message creation."""
        notification = EmailNotification(self.config)
        
        message = notification._create_email_message(
            self.message,
            ["recipient@example.com"],
            []
        )
        
        assert message['From'] == 'Change Process Automation <user@example.com>'
        assert message['To'] == 'recipient@example.com'
        assert '[NORMAL] Test Email' in message['Subject']
        assert 'Message-ID' in message
        assert 'X-Mailer' in message
        assert 'X-Priority' in message
    
    def test_sanitize_subject(self):
        """Test subject line sanitization."""
        notification = EmailNotification(self.config)
        
        # Test with newlines and tabs
        subject = "Test\nSubject\tWith\r\nSpecial\tChars"
        sanitized = notification._sanitize_subject(subject)
        assert sanitized == "Test Subject With Special Chars"
        
        # Test with very long subject
        long_subject = "A" * 1000
        sanitized = notification._sanitize_subject(long_subject)
        assert len(sanitized) <= 998
        assert sanitized.endswith("...")
    
    def test_generate_message_id(self):
        """Test message ID generation."""
        notification = EmailNotification(self.config)
        
        msg_id = notification._generate_message_id()
        assert msg_id.startswith("<")
        assert msg_id.endswith("@changeprocess>")
        assert len(msg_id) > 20
    
    def test_get_priority_headers(self):
        """Test priority header generation."""
        notification = EmailNotification(self.config)
        
        # Test X-Priority
        assert notification._get_priority_header("low") == "5"
        assert notification._get_priority_header("normal") == "3"
        assert notification._get_priority_header("high") == "1"
        assert notification._get_priority_header("urgent") == "1"
        
        # Test X-MSMail-Priority
        assert notification._get_ms_priority_header("low") == "Low"
        assert notification._get_ms_priority_header("normal") == "Normal"
        assert notification._get_ms_priority_header("high") == "High"
        assert notification._get_ms_priority_header("urgent") == "High"
    
    def test_create_email_body(self):
        """Test email body creation."""
        notification = EmailNotification(self.config)
        
        body = notification._create_email_body(self.message)
        
        assert "This is a test email" in body
        assert "Priority: NORMAL" in body
        assert "Additional Information:" in body
        assert "test: value" in body
        assert "automated notification" in body.lower()
    
    def test_get_statistics(self):
        """Test email statistics."""
        notification = EmailNotification(self.config)
        
        # Initially should have no sends
        stats = notification.get_statistics()
        assert stats['successful_sends'] == 0
        assert stats['failed_sends'] == 0
        assert stats['recent_failures'] == []
        assert stats['rate_limit_status']['can_send'] is True
        assert stats['rate_limit_status']['wait_time'] == 0
        
        # After a failed send
        notification._record_failed_send(self.message, "Test error")
        stats = notification.get_statistics()
        assert stats['failed_sends'] == 1
        assert len(stats['recent_failures']) == 1
        assert stats['recent_failures'][0]['error'] == "Test error"


class TestEmailIntegration:
    """Integration tests for email functionality."""
    
    def test_full_email_workflow(self):
        """Test complete email workflow with validation and sending."""
        config = {
            'email_smtp_server': 'smtp.example.com',
            'email_smtp_port': 587,
            'email_username': 'user@example.com',
            'email_password': 'password123',
            'email_use_tls': True,
            'email_use_ssl': False,
            'email_timeout': 30,
            'email_max_retries': 2,
            'email_retry_delay': 1,
            'email_max_per_hour': 100,
            'email_max_per_minute': 10,
            'enabled': True
        }
        
        # Create notification manager
        with patch('scripts.communications.notification_manager.SecureSMTPConnection'):
            notification = EmailNotification(config)
            
            # Create message with attachment
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
                f.write(b"Test attachment content")
                f.flush()
                
                try:
                    message = NotificationMessage(
                        title="Integration Test Email",
                        body="This is an integration test email",
                        priority="high",
                        recipients=["test1@example.com", "test2@example.com"],
                        attachments=[f.name],
                        metadata={
                            "test_id": "12345",
                            "environment": "test"
                        }
                    )
                    
                    # Send email
                    result = notification._send_impl(message)
                    assert result is True
                    
                    # Check statistics
                    stats = notification.get_statistics()
                    assert stats['successful_sends'] == 1
                    assert stats['failed_sends'] == 0
                    
                finally:
                    os.unlink(f.name)
