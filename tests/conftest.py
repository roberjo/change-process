import pytest
import os
from datetime import datetime, timedelta
import pytz

@pytest.fixture(scope="session")
def test_config():
    """Fixture to provide test configuration."""
    return {
        'version': '1.0.0',
        'environment': 'production',
        'start_date': datetime.now(pytz.UTC),
        'end_date': datetime.now(pytz.UTC) + timedelta(hours=2),
        'change_number': 'CHG123456'
    }

@pytest.fixture(scope="session")
def mock_servicenow_responses():
    """Fixture to provide mock ServiceNow API responses."""
    return {
        'create_change': {
            'result': {
                'number': 'CHG123456',
                'state': 'Draft',
                'short_description': 'Test Change',
                'description': 'Test Description',
                'risk_level': 'Low',
                'type': 'Normal'
            }
        },
        'get_change': {
            'result': {
                'number': 'CHG123456',
                'state': 'Scheduled',
                'short_description': 'Test Change',
                'description': 'Test Description',
                'risk_level': 'Low',
                'type': 'Normal'
            }
        },
        'list_changes': {
            'result': [
                {
                    'number': 'CHG123456',
                    'state': 'Scheduled',
                    'short_description': 'Test Change 1'
                },
                {
                    'number': 'CHG123457',
                    'state': 'Draft',
                    'short_description': 'Test Change 2'
                }
            ]
        }
    }

@pytest.fixture(scope="session")
def test_env_vars():
    """Fixture to set up test environment variables."""
    env_vars = {
        'SN_INSTANCE': 'test-instance',
        'SN_CLIENT_ID': 'test-client-id',
        'SN_CLIENT_SECRET': 'test-client-secret',
        'SN_USERNAME': 'test-username',
        'SN_PASSWORD': 'test-password',
        'SN_DEFAULT_ASSIGNMENT_GROUP': 'test-group',
        'SN_DEFAULT_PRIORITY': '3',
        'SN_DEFAULT_RISK_LEVEL': 'Low'
    }
    
    # Store original environment variables
    original_env = {}
    for key in env_vars:
        if key in os.environ:
            original_env[key] = os.environ[key]
    
    # Set test environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield env_vars
    
    # Restore original environment variables
    for key in env_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key] 