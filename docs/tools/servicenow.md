# ServiceNow Integration

This document describes the ServiceNow integration capabilities and usage of the change request automation scripts.

## Overview

The ServiceNow integration provides a comprehensive Python-based interface for automating change request management in ServiceNow. It supports creating, updating, and monitoring change requests, with a focus on scheduled changes and deployment automation.

## Features

- OAuth2 authentication
- Comprehensive error handling
- Input validation
- Retry logic for network operations
- Proper session management
- Detailed logging
- Change calendar integration
- Status tracking and updates

## Prerequisites

- Python 3.8 or higher
- ServiceNow instance with API access
- OAuth2 credentials (Client ID and Secret)
- ServiceNow user credentials

## Configuration

1. Copy the environment template:
   ```bash
   cp scripts/servicenow/.env.template scripts/servicenow/.env
   ```

2. Configure the environment variables:
   ```bash
   # ServiceNow instance
   SN_INSTANCE=your-instance.service-now.com
   
   # OAuth2 credentials
   SN_CLIENT_ID=your-client-id
   SN_CLIENT_SECRET=your-client-secret
   
   # User credentials
   SN_USERNAME=your-username
   SN_PASSWORD=your-password
   
   # Optional configurations
   SN_API_VERSION=v2
   SN_DEFAULT_ASSIGNMENT_GROUP=your-group
   SN_DEFAULT_PRIORITY=3
   SN_DEFAULT_RISK_LEVEL=Low
   ```

## Usage

### Command Line Interface

The `change_request.py` script provides a command-line interface for managing change requests:

```bash
# Create a change request
python scripts/servicenow/change_request.py --action create \
    --title "Deploy Update" \
    --start-date "2024-03-20 10:00:00" \
    --end-date "2024-03-20 12:00:00"

# List change requests
python scripts/servicenow/change_request.py --action list --status "Draft"

# Get change details
python scripts/servicenow/change_request.py --action get --number "CHG123456"

# View change calendar
python scripts/servicenow/change_request.py --action calendar \
    --start-date "2024-03-20" \
    --end-date "2024-03-27"
```

### Python API

The `ServiceNowChangeRequest` class can be used in Python scripts:

```python
from servicenow.change_request import ServiceNowChangeRequest

# Initialize the client
sn = ServiceNowChangeRequest()

# Create a change request
change = sn.create_scheduled_change(
    title="Deploy Update",
    description="Deploy new version",
    risk_level="Low",
    implementation_plan="Implementation steps",
    test_plan="Testing steps",
    rollback_plan="Rollback steps",
    start_date="2024-03-20 10:00:00",
    end_date="2024-03-20 12:00:00"
)

# Update change status
sn.update_change_status(change['number'], 'Approval')

# Get change details
details = sn.get_change_details(change['number'])

# List changes
changes = sn.list_changes(status='Draft')

# Get calendar view
calendar = sn.get_change_calendar(
    start_date="2024-03-20",
    end_date="2024-03-27"
)
```

## Change Request States

The following states are supported:

| State | Description |
|-------|-------------|
| Draft | Initial state for new changes |
| Requested | Change has been requested |
| Planning | Change is being planned |
| Approval | Change is awaiting approval |
| Scheduled | Change is scheduled for implementation |
| Implement | Change is being implemented |
| Review | Change is under review |
| Closed | Change has been completed |

## Risk Levels

The following risk levels are supported:

| Risk Level | Description |
|------------|-------------|
| Low | Minimal impact, easily reversible |
| Medium | Moderate impact, reversible with effort |
| High | Significant impact, difficult to reverse |
| Critical | Severe impact, may be irreversible |

## Change Types

The following change types are supported:

| Type | Description |
|------|-------------|
| Normal | Standard change with minimal risk |
| Standard | Pre-approved change with known procedure |
| Emergency | Urgent change requiring immediate attention |
| Emergency Fix | Critical fix requiring immediate deployment |

## Error Handling

The integration includes comprehensive error handling:

- Custom exception classes:
  - `ServiceNowError`: Base exception class
  - `ServiceNowAuthError`: Authentication errors
  - `ServiceNowValidationError`: Validation errors
  - `ServiceNowAPIError`: API errors

- Retry logic for transient failures:
  - 3 retries with exponential backoff
  - Retries on 500, 502, 503, and 504 status codes

- Input validation:
  - Required fields
  - Valid states
  - Valid risk levels
  - Valid change types
  - Date validation

## Logging

Logs are stored in `servicenow_change.log` with the following format:
```
2024-03-20 10:00:00,000 - servicenow.change_request - INFO - [change_request.py:123] - Created change request CHG123456
```

The log includes:
- Timestamp
- Log level
- Module name
- File and line number
- Detailed message

## Security

- OAuth2 authentication
- Environment variable based configuration
- No hardcoded credentials
- Secure token management
- Input validation
- Error handling
- Logging and monitoring

## Best Practices

1. Always use environment variables for credentials
2. Validate input data before API calls
3. Handle errors appropriately
4. Use proper logging
5. Follow the change request lifecycle
6. Document changes properly
7. Use appropriate risk levels
8. Plan for rollback
9. Monitor change status
10. Keep audit trail

## Troubleshooting

Common issues and solutions:

1. Authentication failures:
   - Verify OAuth2 credentials
   - Check user permissions
   - Validate token expiration

2. API errors:
   - Check API version
   - Verify endpoint URLs
   - Validate request payload

3. Validation errors:
   - Check required fields
   - Verify date formats
   - Validate state transitions

4. Network issues:
   - Check connectivity
   - Verify firewall rules
   - Monitor retry attempts

## Support

For issues and support:
1. Check the logs
2. Review error messages
3. Consult the documentation
4. Contact the development team 