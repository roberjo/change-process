# Change Process Automation

This project provides a comprehensive set of tools and scripts for automating change management processes, particularly focusing on ServiceNow integration, deployment automation, and communication workflows.

## 🚀 New Features & Improvements

### ✨ Enhanced Features
- **Unified CLI Interface**: Modern command-line interface using Click
- **Centralized Configuration**: Type-safe configuration management
- **Multi-Channel Notifications**: Support for Teams, Slack, and Email
- **Docker Support**: Containerized deployment and development
- **CI/CD Pipeline**: GitHub Actions for automated testing and deployment
- **Comprehensive Testing**: Unit, integration, and end-to-end tests
- **Development Tools**: Makefile for common tasks and PowerShell support

### 🔧 Technical Improvements
- **Better Error Handling**: Comprehensive exception management
- **Type Safety**: Full type hints throughout the codebase
- **Security**: OAuth2 authentication and secure credential management
- **Performance**: Connection pooling and retry mechanisms
- **Documentation**: Extensive documentation and development guides

## Technology Stack

- **ServiceNow**: Change management and request tracking
- **Harness**: CI/CD pipeline automation
- **Microsoft Teams & Outlook**: Communication and notifications
- **Python**: Core automation and integration scripts
- **Bash**: Utility scripts and process automation
- **Git**: Version control and change tracking
- **Docker**: Containerization and deployment
- **GitHub Actions**: Continuous integration and deployment

## Directory Structure

```
.
├── config/                     # Configuration management
│   └── settings.py            # Centralized configuration
├── docs/                      # Documentation
│   ├── processes/             # Process documentation
│   ├── guides/                # User guides
│   ├── DEVELOPMENT.md         # Development guide
│   └── templates/             # Documentation templates
├── scripts/                   # Automation scripts
│   ├── communications/        # Notification system
│   │   └── notification_manager.py # Unified notification manager
│   ├── servicenow/           # ServiceNow integration
│   │   ├── change_request.py # Change request automation
│   │   └── .env.template     # Environment template
│   ├── examples/            # Example scripts
│   │   └── automated_deployment.py # Deployment automation
│   └── cli.py               # Command line interface
├── templates/                # Process templates
│   └── harness-pipeline-template.yaml # Harness pipeline
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── requirements-test.txt # Test dependencies
├── tools/                   # Utility tools
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker Compose setup
├── Makefile                 # Build automation
├── requirements.txt         # Production dependencies
├── .github/workflows/       # CI/CD pipelines
│   └── ci.yml              # GitHub Actions workflow
└── README.md               # Project documentation
```

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Docker (optional)
- ServiceNow instance with API access
- Microsoft Teams webhook URL (optional)
- Email SMTP access (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd change-process
   ```

2. **Quick setup (recommended)**
   ```bash
   make quick-start
   ```

3. **Manual setup**
   ```bash
   # Install dependencies
   make install
   
   # Set up environment
   make setup-env
   
   # Edit configuration
   # Edit scripts/servicenow/.env with your credentials
   ```

### Windows PowerShell Setup

For Windows users, use PowerShell-specific commands:

```powershell
# Install dependencies
make install-ps

# Run tests
make test-ps

# Clean up
make clean-ps
```

## Usage

### Command Line Interface

The project now includes a modern CLI for easy interaction:

```bash
# Show help
python scripts/cli.py --help

# Create a change request
python scripts/cli.py change create \
    --title "Deploy Update" \
    --description "Deploy version 1.0.0" \
    --start-date "2024-03-20 10:00:00" \
    --end-date "2024-03-20 12:00:00" \
    --risk-level "Low"

# List change requests
python scripts/cli.py change list --status "Scheduled"

# Update change status
python scripts/cli.py change update-status \
    --number "CHG123456" \
    --status "Implement"

# Deploy to environment
python scripts/cli.py deployment deploy \
    --version "1.0.0" \
    --environment "production"

# Send notification
python scripts/cli.py notifications send \
    --title "Deployment Complete" \
    --message "Version 1.0.0 deployed successfully" \
    --channels teams email
```

### Docker Usage

```bash
# Build and run with Docker
make docker-build
make docker-run

# Development with Docker Compose
docker-compose --profile dev up --build

# Run tests in Docker
docker-compose --profile test up --build --abort-on-container-exit
```

### Traditional Script Usage

#### ServiceNow Change Request Automation
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
```

#### Automated Deployment
```bash
# Run automated deployment
python scripts/examples/automated_deployment.py \
    --version "1.0.0" \
    --environment "production"
```

## Configuration

### Environment Variables

Create a `.env` file with your configuration:

```bash
# ServiceNow Configuration
SN_INSTANCE=your-instance.service-now.com
SN_CLIENT_ID=your-client-id
SN_CLIENT_SECRET=your-client-secret
SN_USERNAME=your-username
SN_PASSWORD=your-password

# Notification Configuration
TEAMS_WEBHOOK_URL=your-teams-webhook-url
EMAIL_SMTP_SERVER=your-smtp-server
EMAIL_USERNAME=your-email
EMAIL_PASSWORD=your-password

# Application Configuration
LOG_LEVEL=INFO
TIMEOUT=300
RETRY_ATTEMPTS=3
```

### Centralized Configuration

The project now uses a centralized configuration system:

```python
from config.settings import ConfigManager

config_manager = ConfigManager()
config = config_manager.get_config()

# Access configuration
sn_config = config.servicenow
notification_config = config.notifications
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
python -m pytest tests/ -v --cov=scripts --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_change_request.py -v
```

### Code Quality

```bash
# Run linting
make lint

# Clean up generated files
make clean
```

### Development with Docker

```bash
# Development environment with hot reload
docker-compose --profile dev up --build

# Test environment
docker-compose --profile test up --build --abort-on-container-exit
```

## Documentation

- [Development Guide](docs/DEVELOPMENT.md) - Comprehensive development documentation
- [Process Documentation](docs/processes/) - Change management processes
- [Tool Documentation](docs/tools/) - Integration guides
- [Templates](templates/) - Process and pipeline templates

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the [Development Guide](docs/DEVELOPMENT.md)
4. Run tests and ensure code quality
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Create a Pull Request

## CI/CD Pipeline

The project includes a comprehensive CI/CD pipeline with:

- **Automated Testing**: Unit, integration, and security tests
- **Code Quality**: Linting and style checks
- **Docker Builds**: Automated container builds
- **Security Scanning**: Vulnerability assessment
- **Deployment**: Automated deployment to production

## Security

- OAuth2 authentication for ServiceNow
- Environment variable based configuration
- No hardcoded credentials
- Secure token management
- Input validation and sanitization
- Comprehensive error handling
- Security scanning in CI/CD pipeline

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
- Console output for immediate feedback
- Log files for persistence
- Structured logging for better analysis
- Configurable log levels

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Check the [documentation](docs/) for detailed guides
- Review [existing issues](https://github.com/your-repo/issues) on GitHub
- Create a new issue with detailed information
- Contact the development team for urgent matters

