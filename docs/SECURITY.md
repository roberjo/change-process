# Security Documentation

This document outlines the security measures implemented in the Change Process Automation project, particularly focusing on the notification system.

## URL Validation and SSRF Prevention

### Overview

The notification system implements comprehensive URL validation to prevent Server-Side Request Forgery (SSRF) attacks and malicious redirects. This is critical when making HTTP requests to external webhook URLs.

### Security Measures Implemented

#### 1. **URL Scheme Validation**
- **Requirement**: Only HTTPS URLs are allowed
- **Rationale**: Prevents man-in-the-middle attacks and ensures encrypted communication
- **Implementation**: Validates `parsed_url.scheme.lower() == 'https'`

#### 2. **Domain Whitelisting**
- **Requirement**: Only pre-approved domains are allowed
- **Teams Allowed Domains**:
  - `webhook.office.com`
  - `outlook.office.com`
  - `outlook.office365.com`
- **Slack Allowed Domains**:
  - `hooks.slack.com`
  - `slack.com`
- **Implementation**: Checks domain against service-specific whitelist

#### 3. **IP Address Blocking**
- **Requirement**: IP addresses are not allowed (only domain names)
- **Rationale**: Prevents direct access to internal networks and localhost
- **Implementation**: Uses `ipaddress.ip_address()` to detect IP addresses

#### 4. **Suspicious Pattern Detection**
- **Blocked Patterns**:
  - `file://` - Local file access
  - `ftp://` - File transfer protocol
  - `gopher://` - Legacy protocol
  - `data:` - Data URLs
  - `javascript:` - JavaScript execution
  - `vbscript:` - VBScript execution
  - `about:` - Browser internal pages
  - `chrome://` - Chrome internal pages
  - `chrome-extension://` - Chrome extensions
  - `moz-extension://` - Firefox extensions
  - `view-source:` - Source code viewing
  - `blob:` - Blob URLs
  - `mediasource:` - Media source URLs
  - `filesystem:` - File system URLs

#### 5. **URL Structure Validation**
- **Requirement**: URLs must have valid structure with domain and path
- **Implementation**: Validates `parsed_url.netloc` and `parsed_url.path`

## Notification Message Validation

### Overview

The `NotificationMessage` class implements comprehensive input validation to ensure data integrity, prevent injection attacks, and maintain system security.

### Validation Features

#### 1. **Title Validation**
- **Maximum Length**: 200 characters
- **Content Validation**: Blocks dangerous patterns like `<script>`, `javascript:`, `vbscript:`, `data:`
- **Whitespace Validation**: Prevents whitespace-only titles
- **Type Validation**: Ensures string type

#### 2. **Body Validation**
- **Maximum Length**: 4,000 characters
- **Content Validation**: Blocks dangerous patterns including:
  - `<script[^>]*>.*?</script>` - Script tags
  - `javascript:` - JavaScript protocol
  - `vbscript:` - VBScript protocol
  - `data:text/html` - HTML data URLs
  - `data:application/x-javascript` - JavaScript data URLs
- **Whitespace Validation**: Prevents whitespace-only bodies
- **Type Validation**: Ensures string type

#### 3. **Priority Validation**
- **Valid Values**: `low`, `normal`, `high`, `urgent`
- **Case Insensitive**: Accepts any case (e.g., `HIGH`, `High`, `high`)
- **Type Validation**: Ensures string type

#### 4. **Recipients Validation**
- **Maximum Count**: 50 recipients
- **Maximum Length**: 100 characters per recipient
- **Email Validation**: Basic email format validation for recipients containing `@`
- **Type Validation**: Ensures list of strings
- **Empty Validation**: Prevents empty recipient entries

#### 5. **Attachments Validation**
- **Maximum Count**: 10 attachments
- **Maximum Length**: 500 characters per attachment
- **Path Security**: Blocks dangerous patterns:
  - `../` - Directory traversal
  - `..\\` - Windows directory traversal
  - `file://` - File protocol
  - `data:` - Data URLs
- **Type Validation**: Ensures list of strings
- **Empty Validation**: Prevents empty attachment entries

#### 6. **Metadata Validation**
- **Maximum Entries**: 20 metadata entries
- **Key Length**: Maximum 50 characters per key
- **Value Length**: Maximum 500 characters per string value
- **Value Types**: Supports string, int, float, bool, and None
- **Type Validation**: Ensures dictionary with string keys
- **Empty Validation**: Prevents empty keys

### Validation Implementation

#### 1. **Automatic Validation**
```python
# Validation runs automatically on object creation
message = NotificationMessage(
    title="Test",
    body="Test body",
    priority="normal"
)
# If validation fails, NotificationMessageValidationError is raised
```

#### 2. **Manual Validation**
```python
message = NotificationMessage(title="Test", body="Test body")
message.validate()  # Explicit validation
```

#### 3. **Sanitization**
```python
message = NotificationMessage(
    title="  Test  ",
    body="  Body  ",
    priority="  HIGH  "
)
sanitized = message.sanitize()  # Removes whitespace, normalizes case
```

### Security Benefits

#### 1. **Injection Prevention**
- Blocks script injection in titles and bodies
- Prevents XSS attacks through notification content
- Validates email formats to prevent email injection

#### 2. **Resource Protection**
- Limits message sizes to prevent memory exhaustion
- Restricts recipient counts to prevent spam
- Controls attachment counts and sizes

#### 3. **Path Traversal Prevention**
- Blocks dangerous file paths in attachments
- Prevents access to system files
- Validates URL formats

#### 4. **Data Integrity**
- Ensures consistent data types
- Prevents malformed data structures
- Maintains system stability

## HTTP Request Security

#### 1. **Redirect Prevention**
- **Setting**: `allow_redirects=False`
- **Rationale**: Prevents malicious redirects to unauthorized endpoints
- **Implementation**: Disables automatic redirects and logs unexpected redirects

#### 2. **SSL Certificate Verification**
- **Setting**: `verify=True`
- **Rationale**: Ensures secure connections and prevents certificate-based attacks
- **Implementation**: Verifies SSL certificates for all HTTPS requests

#### 3. **Security Headers**
- **User-Agent**: `ChangeProcessAutomation/1.0`
- **Content-Type**: `application/json`
- **Accept**: `application/json`
- **Rationale**: Provides consistent identification and prevents content-type confusion

#### 4. **Timeout Protection**
- **Setting**: `timeout=30`
- **Rationale**: Prevents hanging requests and resource exhaustion
- **Implementation**: 30-second timeout for all webhook requests

#### 5. **Session Management**
- **Implementation**: Uses `requests.Session()` with proper cleanup
- **Rationale**: Ensures proper resource management and connection pooling

## Error Handling and Logging

#### 1. **Specific Exception Handling**
- **SSL Errors**: Separate handling for certificate issues
- **Connection Errors**: Separate handling for network issues
- **Timeout Errors**: Separate handling for timeout issues
- **Validation Errors**: Specific handling for input validation failures
- **General Request Errors**: Catch-all for other HTTP issues

#### 2. **Comprehensive Logging**
- **Success**: Log successful notifications
- **Validation Failures**: Log URL validation errors and message validation errors
- **Network Errors**: Log connection and SSL errors
- **Security Events**: Log suspicious patterns and redirects

## Configuration Security

#### 1. **Environment Variable Usage**
- **Implementation**: All sensitive data stored in environment variables
- **Rationale**: Prevents hardcoded credentials and configuration

#### 2. **Validation at Initialization**
- **Implementation**: URL validation during object construction
- **Rationale**: Fails fast if configuration is invalid

#### 3. **Re-validation Before Requests**
- **Implementation**: URL validation before each HTTP request
- **Rationale**: Provides defense in depth against runtime tampering

## Testing Security Features

### Test Coverage

The security features are thoroughly tested with:

1. **Valid URL Tests**: Ensure legitimate URLs pass validation
2. **Invalid Scheme Tests**: Ensure HTTP URLs are rejected
3. **IP Address Tests**: Ensure IP addresses are blocked
4. **Unauthorized Domain Tests**: Ensure non-whitelisted domains are rejected
5. **Suspicious Pattern Tests**: Ensure dangerous URL patterns are blocked
6. **Security Header Tests**: Ensure proper headers are set
7. **Redirect Prevention Tests**: Ensure redirects are disabled
8. **Message Validation Tests**: Ensure notification message validation works
9. **Content Security Tests**: Ensure dangerous content is blocked
10. **Sanitization Tests**: Ensure data sanitization works correctly

### Running Security Tests

```bash
# Run all security tests
python -m pytest tests/unit/test_notification_security.py -v
python -m pytest tests/unit/test_notification_validation.py -v

# Run specific security test
python -m pytest tests/unit/test_notification_security.py::test_ip_address_not_allowed -v
python -m pytest tests/unit/test_notification_validation.py::test_title_with_dangerous_content -v
```

## Best Practices

### For Developers

1. **Always validate URLs**: Never trust user-provided URLs
2. **Use HTTPS only**: Require encrypted connections
3. **Implement whitelisting**: Only allow known, trusted domains
4. **Prevent redirects**: Disable automatic redirects
5. **Verify certificates**: Always verify SSL certificates
6. **Set timeouts**: Prevent hanging requests
7. **Log security events**: Monitor for suspicious activity
8. **Validate all inputs**: Use NotificationMessage validation
9. **Sanitize data**: Clean user input before processing
10. **Limit data sizes**: Prevent resource exhaustion

### For Administrators

1. **Regular audits**: Review allowed domain lists
2. **Monitor logs**: Watch for security-related log entries
3. **Update configurations**: Keep webhook URLs current
4. **Network security**: Ensure proper firewall rules
5. **Access control**: Limit who can modify webhook configurations
6. **Review validation rules**: Adjust limits as needed
7. **Monitor validation failures**: Track validation error patterns

## Incident Response

### If a Security Issue is Detected

1. **Immediate Actions**:
   - Disable affected notification channels
   - Review logs for suspicious activity
   - Check for unauthorized configuration changes
   - Review validation error logs

2. **Investigation**:
   - Analyze URL validation logs
   - Check for unexpected redirects
   - Review network connections
   - Examine message validation failures

3. **Recovery**:
   - Update webhook URLs if compromised
   - Review and update domain whitelists
   - Implement additional monitoring
   - Adjust validation rules if needed

## Compliance

### Security Standards

The implementation follows these security standards:

- **OWASP Top 10**: Addresses SSRF (A5:2021), XSS (A3:2021), and injection (A2:2021)
- **NIST Cybersecurity Framework**: Implements Identify and Protect functions
- **ISO 27001**: Information security management
- **SOC 2**: Security, availability, and confidentiality

### Audit Trail

All security-related activities are logged:

- URL validation attempts (success/failure)
- HTTP request details (headers, timing)
- Security exceptions and errors
- Configuration changes
- Message validation failures
- Sanitization operations

## Future Enhancements

### Planned Security Improvements

1. **Rate Limiting**: Implement request rate limiting
2. **Content Validation**: Validate webhook payload content
3. **Signature Verification**: Implement webhook signature verification
4. **Network Segmentation**: Isolate notification services
5. **Advanced Monitoring**: Implement real-time security monitoring
6. **Automated Response**: Implement automated security responses
7. **Enhanced Validation**: Add more sophisticated content validation
8. **Encryption**: Implement end-to-end encryption for sensitive messages

### Security Metrics

Track these security metrics:

- URL validation success/failure rates
- Average response times
- SSL certificate validation rates
- Security exception frequencies
- Configuration change frequencies
- Message validation success/failure rates
- Sanitization operation counts
- Content security violation rates 