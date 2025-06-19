"""
Tests for NotificationMessage validation functionality.
"""

import pytest
from scripts.communications.notification_manager import (
    NotificationMessage,
    NotificationMessageValidator,
    NotificationMessageValidationError
)

def test_valid_message():
    """Test valid notification message."""
    message = NotificationMessage(
        title="Test Title",
        body="Test body content",
        priority="normal",
        recipients=["test@example.com"],
        metadata={"key": "value"}
    )
    # Should not raise any exception
    message.validate()

def test_empty_title():
    """Test message with empty title."""
    with pytest.raises(NotificationMessageValidationError, match="Title cannot be empty"):
        NotificationMessage(title="", body="Test body")

def test_title_too_long():
    """Test message with title exceeding maximum length."""
    long_title = "a" * 201  # Exceeds MAX_TITLE_LENGTH of 200
    with pytest.raises(NotificationMessageValidationError, match="Title too long"):
        NotificationMessage(title=long_title, body="Test body")

def test_title_with_dangerous_content():
    """Test message with dangerous content in title."""
    with pytest.raises(NotificationMessageValidationError, match="Title contains potentially dangerous content"):
        NotificationMessage(title="Test<script>alert('xss')</script>", body="Test body")

def test_empty_body():
    """Test message with empty body."""
    with pytest.raises(NotificationMessageValidationError, match="Body cannot be empty"):
        NotificationMessage(title="Test", body="")

def test_invalid_priority():
    """Test message with invalid priority."""
    with pytest.raises(NotificationMessageValidationError, match="Invalid priority"):
        NotificationMessage(title="Test", body="Test body", priority="invalid")

def test_valid_priorities():
    """Test all valid priority levels."""
    valid_priorities = ["low", "normal", "high", "urgent"]
    
    for priority in valid_priorities:
        message = NotificationMessage(title="Test", body="Test body", priority=priority)
        message.validate()  # Should not raise exception

def test_too_many_recipients():
    """Test message with too many recipients."""
    recipients = [f"test{i}@example.com" for i in range(51)]  # Exceeds MAX_RECIPIENTS of 50
    with pytest.raises(NotificationMessageValidationError, match="Too many recipients"):
        NotificationMessage(title="Test", body="Test body", recipients=recipients)

def test_invalid_email_format():
    """Test message with invalid email format."""
    with pytest.raises(NotificationMessageValidationError, match="has invalid email format"):
        NotificationMessage(title="Test", body="Test body", recipients=["invalid-email"])

def test_dangerous_attachment_path():
    """Test message with dangerous attachment path."""
    with pytest.raises(NotificationMessageValidationError, match="contains potentially dangerous path"):
        NotificationMessage(title="Test", body="Test body", attachments=["../../../etc/passwd"])

def test_sanitize_whitespace():
    """Test sanitization removes leading/trailing whitespace."""
    message = NotificationMessage(
        title="  Test Title  ",
        body="  Test body  ",
        priority="  HIGH  ",
        recipients=["  test@example.com  "],
        metadata={"  key  ": "  value  "}
    )
    
    sanitized = message.sanitize()
    
    assert sanitized.title == "Test Title"
    assert sanitized.body == "Test body"
    assert sanitized.priority == "high"
    assert sanitized.recipients == ["test@example.com"]
    assert sanitized.metadata == {"key": "value"}

class TestNotificationMessageValidator:
    """Test NotificationMessage validation."""
    
    def test_valid_message(self):
        """Test valid notification message."""
        message = NotificationMessage(
            title="Test Title",
            body="Test body content",
            priority="normal",
            recipients=["test@example.com"],
            metadata={"key": "value"}
        )
        # Should not raise any exception
        message.validate()
    
    def test_empty_title(self):
        """Test message with empty title."""
        with pytest.raises(NotificationMessageValidationError, match="Title cannot be empty"):
            NotificationMessage(title="", body="Test body")
    
    def test_none_title(self):
        """Test message with None title."""
        with pytest.raises(NotificationMessageValidationError, match="Title cannot be empty"):
            NotificationMessage(title=None, body="Test body")
    
    def test_whitespace_only_title(self):
        """Test message with whitespace-only title."""
        with pytest.raises(NotificationMessageValidationError, match="Title cannot be whitespace only"):
            NotificationMessage(title="   ", body="Test body")
    
    def test_title_too_long(self):
        """Test message with title exceeding maximum length."""
        long_title = "a" * 201  # Exceeds MAX_TITLE_LENGTH of 200
        with pytest.raises(NotificationMessageValidationError, match="Title too long"):
            NotificationMessage(title=long_title, body="Test body")
    
    def test_title_with_dangerous_content(self):
        """Test message with dangerous content in title."""
        dangerous_titles = [
            "Test<script>alert('xss')</script>",
            "Test javascript:alert('xss')",
            "Test vbscript:alert('xss')",
            "Test data:text/html,<script>alert('xss')</script>"
        ]
        
        for title in dangerous_titles:
            with pytest.raises(NotificationMessageValidationError, match="Title contains potentially dangerous content"):
                NotificationMessage(title=title, body="Test body")
    
    def test_empty_body(self):
        """Test message with empty body."""
        with pytest.raises(NotificationMessageValidationError, match="Body cannot be empty"):
            NotificationMessage(title="Test", body="")
    
    def test_none_body(self):
        """Test message with None body."""
        with pytest.raises(NotificationMessageValidationError, match="Body cannot be empty"):
            NotificationMessage(title="Test", body=None)
    
    def test_whitespace_only_body(self):
        """Test message with whitespace-only body."""
        with pytest.raises(NotificationMessageValidationError, match="Body cannot be whitespace only"):
            NotificationMessage(title="Test", body="   ")
    
    def test_body_too_long(self):
        """Test message with body exceeding maximum length."""
        long_body = "a" * 4001  # Exceeds MAX_BODY_LENGTH of 4000
        with pytest.raises(NotificationMessageValidationError, match="Body too long"):
            NotificationMessage(title="Test", body=long_body)
    
    def test_body_with_dangerous_content(self):
        """Test message with dangerous content in body."""
        dangerous_bodies = [
            "Test<script>alert('xss')</script>",
            "Test javascript:alert('xss')",
            "Test vbscript:alert('xss')",
            "Test data:text/html,<script>alert('xss')</script>",
            "Test data:application/x-javascript,alert('xss')"
        ]
        
        for body in dangerous_bodies:
            with pytest.raises(NotificationMessageValidationError, match="Body contains potentially dangerous content"):
                NotificationMessage(title="Test", body=body)
    
    def test_invalid_priority(self):
        """Test message with invalid priority."""
        with pytest.raises(NotificationMessageValidationError, match="Invalid priority"):
            NotificationMessage(title="Test", body="Test body", priority="invalid")
    
    def test_empty_priority(self):
        """Test message with empty priority."""
        with pytest.raises(NotificationMessageValidationError, match="Priority cannot be empty"):
            NotificationMessage(title="Test", body="Test body", priority="")
    
    def test_priority_case_insensitive(self):
        """Test priority validation is case insensitive."""
        message = NotificationMessage(title="Test", body="Test body", priority="HIGH")
        message.validate()  # Should not raise exception
    
    def test_too_many_recipients(self):
        """Test message with too many recipients."""
        recipients = [f"test{i}@example.com" for i in range(51)]  # Exceeds MAX_RECIPIENTS of 50
        with pytest.raises(NotificationMessageValidationError, match="Too many recipients"):
            NotificationMessage(title="Test", body="Test body", recipients=recipients)
    
    def test_empty_recipient(self):
        """Test message with empty recipient."""
        with pytest.raises(NotificationMessageValidationError, match="Recipient 1 cannot be empty"):
            NotificationMessage(title="Test", body="Test body", recipients=[""])
    
    def test_recipient_too_long(self):
        """Test message with recipient exceeding maximum length."""
        long_email = "a" * 101 + "@example.com"  # Exceeds MAX_RECIPIENT_LENGTH of 100
        with pytest.raises(NotificationMessageValidationError, match="Recipient 1 too long"):
            NotificationMessage(title="Test", body="Test body", recipients=[long_email])
    
    def test_too_many_attachments(self):
        """Test message with too many attachments."""
        attachments = [f"attachment{i}.pdf" for i in range(11)]  # Exceeds MAX_ATTACHMENTS of 10
        with pytest.raises(NotificationMessageValidationError, match="Too many attachments"):
            NotificationMessage(title="Test", body="Test body", attachments=attachments)
    
    def test_empty_attachment(self):
        """Test message with empty attachment."""
        with pytest.raises(NotificationMessageValidationError, match="Attachment 1 cannot be empty"):
            NotificationMessage(title="Test", body="Test body", attachments=[""])
    
    def test_attachment_too_long(self):
        """Test message with attachment exceeding maximum length."""
        long_attachment = "a" * 501  # Exceeds MAX_ATTACHMENT_LENGTH of 500
        with pytest.raises(NotificationMessageValidationError, match="Attachment 1 too long"):
            NotificationMessage(title="Test", body="Test body", attachments=[long_attachment])
    
    def test_too_many_metadata_entries(self):
        """Test message with too many metadata entries."""
        metadata = {f"key{i}": f"value{i}" for i in range(21)}  # Exceeds MAX_METADATA_ENTRIES of 20
        with pytest.raises(NotificationMessageValidationError, match="Too many metadata entries"):
            NotificationMessage(title="Test", body="Test body", metadata=metadata)
    
    def test_empty_metadata_key(self):
        """Test message with empty metadata key."""
        with pytest.raises(NotificationMessageValidationError, match="Metadata key cannot be empty"):
            NotificationMessage(title="Test", body="Test body", metadata={"": "value"})
    
    def test_metadata_key_too_long(self):
        """Test message with metadata key exceeding maximum length."""
        long_key = "a" * 51  # Exceeds MAX_METADATA_KEY_LENGTH of 50
        with pytest.raises(NotificationMessageValidationError, match="Metadata key.*too long"):
            NotificationMessage(title="Test", body="Test body", metadata={long_key: "value"})
    
    def test_metadata_value_too_long(self):
        """Test message with metadata value exceeding maximum length."""
        long_value = "a" * 501  # Exceeds MAX_METADATA_VALUE_LENGTH of 500
        with pytest.raises(NotificationMessageValidationError, match="value too long"):
            NotificationMessage(title="Test", body="Test body", metadata={"key": long_value})
    
    def test_unsupported_metadata_value_type(self):
        """Test message with unsupported metadata value type."""
        with pytest.raises(NotificationMessageValidationError, match="unsupported value type"):
            NotificationMessage(title="Test", body="Test body", metadata={"key": [1, 2, 3]})
    
    def test_valid_metadata_value_types(self):
        """Test all valid metadata value types."""
        valid_values = {
            "string": "test",
            "integer": 123,
            "float": 123.45,
            "boolean": True,
            "none": None
        }
        
        for value_type, value in valid_values.items():
            message = NotificationMessage(
                title="Test", 
                body="Test body", 
                metadata={"key": value}
            )
            message.validate()  # Should not raise exception

class TestNotificationMessageSanitization:
    """Test NotificationMessage sanitization."""
    
    def test_sanitize_whitespace(self):
        """Test sanitization removes leading/trailing whitespace."""
        message = NotificationMessage(
            title="  Test Title  ",
            body="  Test body  ",
            priority="  HIGH  ",
            recipients=["  test@example.com  "],
            attachments=["  attachment.pdf  "],
            metadata={"  key  ": "  value  "}
        )
        
        sanitized = message.sanitize()
        
        assert sanitized.title == "Test Title"
        assert sanitized.body == "Test body"
        assert sanitized.priority == "high"
        assert sanitized.recipients == ["test@example.com"]
        assert sanitized.attachments == ["attachment.pdf"]
        assert sanitized.metadata == {"key": "value"}
    
    def test_sanitize_empty_lists(self):
        """Test sanitization handles empty lists."""
        message = NotificationMessage(
            title="Test",
            body="Test body",
            recipients=["", "  ", "valid@example.com", ""],
            attachments=["", "  ", "valid.pdf", ""],
            metadata={"": "value", "  ": "value", "valid": "value"}
        )
        
        sanitized = message.sanitize()
        
        assert sanitized.recipients == ["valid@example.com"]
        assert sanitized.attachments == ["valid.pdf"]
        assert sanitized.metadata == {"valid": "value"}
    
    def test_sanitize_none_values(self):
        """Test sanitization handles None values."""
        message = NotificationMessage(
            title="Test",
            body="Test body",
            recipients=None,
            attachments=None,
            metadata=None
        )
        
        sanitized = message.sanitize()
        
        assert sanitized.recipients is None
        assert sanitized.attachments is None
        assert sanitized.metadata is None

class TestNotificationMessageIntegration:
    """Test NotificationMessage integration with validation."""
    
    def test_validation_in_constructor(self):
        """Test that validation runs automatically in constructor."""
        # Valid message should work
        message = NotificationMessage(
            title="Test",
            body="Test body",
            priority="normal"
        )
        assert message.title == "Test"
        
        # Invalid message should raise exception
        with pytest.raises(NotificationMessageValidationError):
            NotificationMessage(title="", body="Test body")
    
    def test_validation_method(self):
        """Test the validate method."""
        message = NotificationMessage(
            title="Test",
            body="Test body",
            priority="normal"
        )
        
        # Should not raise exception
        message.validate()
        
        # Modify to invalid state and test
        message.title = ""
        with pytest.raises(NotificationMessageValidationError):
            message.validate()
    
    def test_sanitize_creates_new_instance(self):
        """Test that sanitize creates a new instance."""
        original = NotificationMessage(
            title="  Test  ",
            body="  Body  ",
            priority="normal"
        )
        
        sanitized = original.sanitize()
        
        # Should be different objects
        assert original is not sanitized
        
        # Original should be unchanged
        assert original.title == "  Test  "
        assert original.body == "  Body  "
        
        # Sanitized should be cleaned
        assert sanitized.title == "Test"
        assert sanitized.body == "Body" 