# Change Process Automation

This project provides a comprehensive set of tools and scripts for automating change management processes, particularly focusing on ServiceNow integration, deployment automation, and communication workflows.

## Technology Stack

- **ServiceNow**: Change management and request tracking
- **Harness**: CI/CD pipeline automation
- **Microsoft Teams & Outlook**: Communication and notifications
- **Python**: Core automation and integration scripts
- **Bash**: Utility scripts and process automation
- **Git**: Version control and change tracking

## Directory Structure

```
.
├── docs/                      # Documentation
│   ├── index.md              # Documentation index
│   ├── process/              # Process documentation
│   │   ├── change-process.md # Change process details
│   │   └── templates/        # Process templates
│   └── tools/                # Tool documentation
│       ├── servicenow.md     # ServiceNow integration
│       └── harness.md        # Harness pipeline
├── scripts/                   # Automation scripts
│   ├── servicenow/           # ServiceNow integration
│   │   ├── change_request.py # Change request automation
│   │   └── .env.template     # Environment template
│   ├── communications/       # Communication scripts
│   │   └── notify.sh        # Notification utilities
│   └── examples/            # Example scripts
│       └── automated_deployment.py # Deployment automation
├── templates/                # Process templates
│   ├── change-request.md    # Change request template
│   ├── deployment-plan.md   # Deployment plan template
│   └── harness-pipeline-template.yaml # Harness pipeline
└── README.md                # Project documentation
```

## Documentation

### Process Documentation
- [Change Process Overview](docs/process/change-process.md)
- [Change Request Template](templates/change-request.md)
- [Deployment Plan Template](templates/deployment-plan.md)

### Tool Documentation
- [ServiceNow Integration](docs/tools/servicenow.md)
- [Harness Pipeline](docs/tools/harness.md)

## Getting Started

### Prerequisites
- Python 3.8 or higher
- ServiceNow instance with API access
- Harness account and API access
- Microsoft Teams webhook URL
- Outlook SMTP access

### Configuration

1. **ServiceNow Integration**
   ```bash
   # Copy the environment template
   cp scripts/servicenow/.env.template scripts/servicenow/.env
   
   # Edit the .env file with your credentials
   SN_INSTANCE=your-instance.service-now.com
   SN_CLIENT_ID=your-client-id
   SN_CLIENT_SECRET=your-client-secret
   SN_USERNAME=your-username
   SN_PASSWORD=your-password
   ```

2. **Communication Setup**
   ```bash
   # Configure Teams webhook
   export TEAMS_WEBHOOK_URL=your-webhook-url
   
   # Configure Outlook SMTP
   export OUTLOOK_SMTP_SERVER=your-smtp-server
   export OUTLOOK_SMTP_PORT=587
   export OUTLOOK_USERNAME=your-email
   export OUTLOOK_PASSWORD=your-password
   ```

### Scripts

#### ServiceNow Change Request Automation
The `change_request.py` script provides comprehensive change request management:

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

Features:
- OAuth2 authentication
- Comprehensive error handling
- Input validation
- Retry logic for network operations
- Proper session management
- Detailed logging
- Change calendar integration
- Status tracking and updates

#### Automated Deployment
The `automated_deployment.py` script automates the deployment process:

```bash
# Run automated deployment
python scripts/examples/automated_deployment.py \
    --version "1.0.0" \
    --environment "production"
```

Features:
- Automated change request creation
- Approval workflow management
- Deployment execution
- Post-deployment validation
- Comprehensive error handling
- Detailed logging
- Status notifications
- Rollback capabilities
- Timeout handling

#### Communication Scripts
The `notify.sh` script handles notifications:

```bash
# Send Teams notification
./scripts/communications/notify.sh teams \
    --title "Deployment Complete" \
    --message "Version 1.0.0 deployed successfully"

# Send Outlook email
./scripts/communications/notify.sh outlook \
    --to "team@example.com" \
    --subject "Deployment Complete" \
    --body "Version 1.0.0 deployed successfully"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Version Control

- Use semantic versioning
- Follow Git flow branching model
- Include detailed commit messages
- Reference issue numbers in commits

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security

- OAuth2 authentication for ServiceNow
- Environment variable based configuration
- No hardcoded credentials
- Secure token management
- Input validation
- Error handling
- Logging and monitoring

## Error Handling

All scripts include comprehensive error handling:
- Custom exception classes
- Detailed error messages
- Proper logging
- Retry logic for transient failures
- Validation of input data
- Graceful handling of network issues

## Logging

Logs are stored in:
- `servicenow_change.log` for ServiceNow operations
- `automated_deployment.log` for deployment operations

Log format includes:
- Timestamp
- Log level
- Module name
- File and line number
- Detailed message

