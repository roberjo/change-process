# Development Guide

This document provides comprehensive guidance for developers working on the Change Process Automation project.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Development Setup](#development-setup)
3. [Code Standards](#code-standards)
4. [Testing](#testing)
5. [Configuration](#configuration)
6. [Docker Development](#docker-development)
7. [Contributing](#contributing)

## Project Structure

```
change-process/
├── config/                     # Configuration management
│   └── settings.py            # Centralized configuration
├── docs/                      # Documentation
│   ├── processes/             # Process documentation
│   ├── guides/                # User guides
│   └── templates/             # Documentation templates
├── scripts/                   # Core automation scripts
│   ├── communications/        # Notification system
│   ├── servicenow/           # ServiceNow integration
│   ├── examples/             # Example implementations
│   └── cli.py                # Command line interface
├── templates/                 # Process templates
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── requirements-test.txt # Test dependencies
├── tools/                    # Utility tools
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose setup
├── Makefile                  # Build automation
├── requirements.txt          # Production dependencies
└── README.md                 # Project overview
```

## Development Setup

### Prerequisites

- Python 3.9+
- Docker (optional)
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd change-process
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   make install
   ```

4. **Configure environment**
   ```bash
   make setup-env
   ```

5. **Run tests**
   ```bash
   make test
   ```

## Code Standards

### Python Style Guide

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Maximum line length: 88 characters
- Use f-strings for string formatting

### Documentation

- All public functions and classes must have docstrings
- Use Google-style docstrings
- Include type hints in docstrings

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
python -m pytest tests/ -v --cov=scripts --cov-report=html
```

## Configuration

### Environment Variables

Key configuration variables:

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
```

## Docker Development

### Using Docker

```bash
# Build the image
make docker-build

# Run the application
make docker-run

# Run tests in Docker
make docker-test
```

## Contributing

### Development Workflow

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Commit your changes
5. Create a pull request

### Commit Message Format

Use conventional commit format:

```
type(scope): description
```

Types: feat, fix, docs, style, refactor, test, chore 