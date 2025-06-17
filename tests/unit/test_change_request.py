import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pytz
from scripts.servicenow.change_request import (
    ServiceNowChangeRequest,
    ServiceNowError,
    ServiceNowAuthError,
    ServiceNowValidationError,
    ServiceNowAPIError
)

@pytest.fixture
def mock_env_vars():
    """Fixture to set up mock environment variables."""
    with patch.dict('os.environ', {
        'SN_INSTANCE': 'test-instance',
        'SN_CLIENT_ID': 'test-client-id',
        'SN_CLIENT_SECRET': 'test-client-secret',
        'SN_USERNAME': 'test-username',
        'SN_PASSWORD': 'test-password',
        'SN_DEFAULT_ASSIGNMENT_GROUP': 'test-group',
        'SN_DEFAULT_PRIORITY': '3',
        'SN_DEFAULT_RISK_LEVEL': 'Low'
    }):
        yield

@pytest.fixture
def mock_session():
    """Fixture to create a mock requests session."""
    with patch('requests.Session') as mock:
        session = Mock()
        mock.return_value = session
        yield session

@pytest.fixture
def sn_client(mock_env_vars, mock_session):
    """Fixture to create a ServiceNowChangeRequest instance with mocked dependencies."""
    with patch('scripts.servicenow.change_request.ServiceNowChangeRequest._get_oauth_token') as mock_token:
        mock_token.return_value = 'test-token'
        client = ServiceNowChangeRequest()
        return client

def test_init_missing_env_vars():
    """Test initialization with missing environment variables."""
    with pytest.raises(ServiceNowValidationError) as exc_info:
        ServiceNowChangeRequest()
    assert "Missing required environment variables" in str(exc_info.value)

def test_init_success(mock_env_vars, mock_session):
    """Test successful initialization."""
    with patch('scripts.servicenow.change_request.ServiceNowChangeRequest._get_oauth_token') as mock_token:
        mock_token.return_value = 'test-token'
        client = ServiceNowChangeRequest()
        assert client.instance == 'test-instance'
        assert client.client_id == 'test-client-id'
        assert client.token == 'test-token'

def test_get_oauth_token_success(mock_env_vars, mock_session):
    """Test successful OAuth token retrieval."""
    mock_session.post.return_value.json.return_value = {'access_token': 'test-token'}
    mock_session.post.return_value.raise_for_status = Mock()
    
    client = ServiceNowChangeRequest()
    token = client._get_oauth_token()
    
    assert token == 'test-token'
    mock_session.post.assert_called_once()

def test_get_oauth_token_failure(mock_env_vars, mock_session):
    """Test OAuth token retrieval failure."""
    mock_session.post.side_effect = requests.exceptions.RequestException("API Error")
    
    with pytest.raises(ServiceNowAuthError):
        ServiceNowChangeRequest()

def test_create_scheduled_change(sn_client, mock_session):
    """Test creating a scheduled change request."""
    mock_response = Mock()
    mock_response.json.return_value = {'result': {'number': 'CHG123456'}}
    mock_session.post.return_value = mock_response
    
    start_date = datetime.now(pytz.UTC)
    end_date = start_date + timedelta(hours=2)
    
    change = sn_client.create_scheduled_change(
        title="Test Change",
        description="Test Description",
        risk_level="Low",
        implementation_plan="Test Plan",
        test_plan="Test Plan",
        rollback_plan="Rollback Plan",
        start_date=start_date,
        end_date=end_date
    )
    
    assert change['number'] == 'CHG123456'
    mock_session.post.assert_called_once()

def test_update_change_status(sn_client, mock_session):
    """Test updating change request status."""
    mock_response = Mock()
    mock_response.json.return_value = {'result': {'number': 'CHG123456', 'state': 'Scheduled'}}
    mock_session.put.return_value = mock_response
    
    change = sn_client.update_change_status('CHG123456', 'Scheduled')
    
    assert change['number'] == 'CHG123456'
    assert change['state'] == 'Scheduled'
    mock_session.put.assert_called_once()

def test_get_change_details(sn_client, mock_session):
    """Test retrieving change request details."""
    mock_response = Mock()
    mock_response.json.return_value = {'result': {'number': 'CHG123456', 'state': 'Scheduled'}}
    mock_session.get.return_value = mock_response
    
    change = sn_client.get_change_details('CHG123456')
    
    assert change['number'] == 'CHG123456'
    assert change['state'] == 'Scheduled'
    mock_session.get.assert_called_once()

def test_list_changes(sn_client, mock_session):
    """Test listing change requests."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'result': [
            {'number': 'CHG123456', 'state': 'Scheduled'},
            {'number': 'CHG123457', 'state': 'Draft'}
        ]
    }
    mock_session.get.return_value = mock_response
    
    changes = sn_client.list_changes(status='Scheduled')
    
    assert len(changes) == 2
    assert changes[0]['number'] == 'CHG123456'
    assert changes[1]['number'] == 'CHG123457'
    mock_session.get.assert_called_once()

def test_invalid_risk_level(sn_client):
    """Test creating change request with invalid risk level."""
    with pytest.raises(ServiceNowValidationError) as exc_info:
        sn_client.create_scheduled_change(
            title="Test Change",
            description="Test Description",
            risk_level="Invalid",
            implementation_plan="Test Plan",
            test_plan="Test Plan",
            rollback_plan="Rollback Plan",
            start_date=datetime.now(pytz.UTC),
            end_date=datetime.now(pytz.UTC) + timedelta(hours=2)
        )
    assert "Invalid risk level" in str(exc_info.value)

def test_invalid_change_type(sn_client):
    """Test creating change request with invalid change type."""
    with pytest.raises(ServiceNowValidationError) as exc_info:
        sn_client.create_scheduled_change(
            title="Test Change",
            description="Test Description",
            risk_level="Low",
            implementation_plan="Test Plan",
            test_plan="Test Plan",
            rollback_plan="Rollback Plan",
            start_date=datetime.now(pytz.UTC),
            end_date=datetime.now(pytz.UTC) + timedelta(hours=2),
            type="Invalid"
        )
    assert "Invalid change type" in str(exc_info.value) 