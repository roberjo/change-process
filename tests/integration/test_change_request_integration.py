import pytest
from unittest.mock import patch
import requests
from scripts.servicenow.change_request import (
    ServiceNowChangeRequest,
    ServiceNowError,
    ServiceNowAuthError,
    ServiceNowValidationError,
    ServiceNowAPIError
)

@pytest.mark.integration
class TestServiceNowChangeRequestIntegration:
    """Integration tests for ServiceNowChangeRequest class."""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_env_vars, mock_servicenow_responses):
        """Set up test environment."""
        self.env_vars = test_env_vars
        self.mock_responses = mock_servicenow_responses
        
        # Create a real ServiceNowChangeRequest instance
        with patch('requests.Session') as mock_session:
            self.session = mock_session.return_value
            self.client = ServiceNowChangeRequest()
    
    def test_create_and_get_change(self):
        """Test creating and retrieving a change request."""
        # Mock the create change response
        self.session.post.return_value.json.return_value = self.mock_responses['create_change']
        
        # Create change request
        change = self.client.create_scheduled_change(
            title="Test Change",
            description="Test Description",
            risk_level="Low",
            implementation_plan="Test Plan",
            test_plan="Test Plan",
            rollback_plan="Rollback Plan",
            start_date=self.env_vars['start_date'],
            end_date=self.env_vars['end_date']
        )
        
        assert change['number'] == 'CHG123456'
        assert change['state'] == 'Draft'
        
        # Mock the get change response
        self.session.get.return_value.json.return_value = self.mock_responses['get_change']
        
        # Get change details
        details = self.client.get_change_details('CHG123456')
        
        assert details['number'] == 'CHG123456'
        assert details['state'] == 'Scheduled'
    
    def test_list_and_update_changes(self):
        """Test listing and updating change requests."""
        # Mock the list changes response
        self.session.get.return_value.json.return_value = self.mock_responses['list_changes']
        
        # List changes
        changes = self.client.list_changes(status='Scheduled')
        
        assert len(changes) == 2
        assert changes[0]['number'] == 'CHG123456'
        assert changes[1]['number'] == 'CHG123457'
        
        # Mock the update response
        self.session.put.return_value.json.return_value = {
            'result': {
                'number': 'CHG123456',
                'state': 'Implement'
            }
        }
        
        # Update change status
        updated = self.client.update_change_status('CHG123456', 'Implement')
        
        assert updated['number'] == 'CHG123456'
        assert updated['state'] == 'Implement'
    
    def test_error_handling(self):
        """Test error handling in API calls."""
        # Test authentication error
        self.session.post.side_effect = requests.exceptions.RequestException("Auth Error")
        
        with pytest.raises(ServiceNowAuthError):
            self.client._get_oauth_token()
        
        # Test API error
        self.session.get.side_effect = requests.exceptions.RequestException("API Error")
        
        with pytest.raises(ServiceNowAPIError):
            self.client.get_change_details('CHG123456')
        
        # Test validation error
        with pytest.raises(ServiceNowValidationError):
            self.client.create_scheduled_change(
                title="Test Change",
                description="Test Description",
                risk_level="Invalid",
                implementation_plan="Test Plan",
                test_plan="Test Plan",
                rollback_plan="Rollback Plan",
                start_date=self.env_vars['start_date'],
                end_date=self.env_vars['end_date']
            )
    
    def test_retry_mechanism(self):
        """Test retry mechanism for transient failures."""
        # Mock a sequence of responses: two failures followed by success
        self.session.get.side_effect = [
            requests.exceptions.RequestException("Temporary Error"),
            requests.exceptions.RequestException("Temporary Error"),
            Mock(json=lambda: self.mock_responses['get_change'])
        ]
        
        # Should succeed after retries
        details = self.client.get_change_details('CHG123456')
        
        assert details['number'] == 'CHG123456'
        assert self.session.get.call_count == 3
    
    def test_change_calendar(self):
        """Test change calendar functionality."""
        # Mock the calendar response
        self.session.get.return_value.json.return_value = {
            'result': [
                {
                    'number': 'CHG123456',
                    'start_date': '2024-03-20 10:00:00',
                    'end_date': '2024-03-20 12:00:00'
                }
            ]
        }
        
        # Get change calendar
        calendar = self.client.get_change_calendar(
            start_date=self.env_vars['start_date'],
            end_date=self.env_vars['end_date']
        )
        
        assert len(calendar) == 1
        assert calendar[0]['number'] == 'CHG123456' 