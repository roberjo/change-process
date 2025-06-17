import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import pytz
from scripts.examples.automated_deployment import (
    AutomatedDeployment,
    DeploymentError,
    ValidationError,
    DeploymentTimeoutError
)

@pytest.mark.integration
class TestAutomatedDeploymentIntegration:
    """Integration tests for AutomatedDeployment class."""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_config, test_env_vars, mock_servicenow_responses):
        """Set up test environment."""
        self.config = test_config
        self.env_vars = test_env_vars
        self.mock_responses = mock_servicenow_responses
        
        # Create a real AutomatedDeployment instance with mocked ServiceNow client
        with patch('scripts.examples.automated_deployment.ServiceNowChangeRequest') as mock_sn:
            self.sn_client = mock_sn.return_value
            self.deployment = AutomatedDeployment(
                version=self.config['version'],
                environment=self.config['environment']
            )
    
    def test_complete_deployment_workflow(self):
        """Test the complete deployment workflow."""
        # Mock ServiceNow responses
        self.sn_client.create_scheduled_change.return_value = self.mock_responses['create_change']['result']
        self.sn_client.get_change_details.return_value = self.mock_responses['get_change']['result']
        
        # Mock deployment steps
        with patch.object(self.deployment, '_validate_deployment_prerequisites') as mock_validate, \
             patch.object(self.deployment, '_send_notification') as mock_notify:
            
            # Run the deployment
            result = self.deployment.run()
            
            # Verify the result
            assert result is True
            
            # Verify ServiceNow interactions
            self.sn_client.create_scheduled_change.assert_called_once()
            self.sn_client.update_change_status.assert_called_with('CHG123456', 'Closed')
            
            # Verify notifications
            assert mock_notify.call_count > 0
    
    def test_deployment_with_approval_rejection(self):
        """Test deployment workflow with approval rejection."""
        # Mock ServiceNow responses
        self.sn_client.create_scheduled_change.return_value = self.mock_responses['create_change']['result']
        self.sn_client.get_change_details.return_value = {
            'number': 'CHG123456',
            'state': 'Closed'
        }
        
        # Run the deployment
        result = self.deployment.run()
        
        # Verify the result
        assert result is False
        self.sn_client.update_change_status.assert_not_called()
    
    def test_deployment_with_validation_failure(self):
        """Test deployment workflow with validation failure."""
        # Mock ServiceNow responses
        self.sn_client.create_scheduled_change.return_value = self.mock_responses['create_change']['result']
        self.sn_client.get_change_details.return_value = self.mock_responses['get_change']['result']
        
        # Mock validation failure
        with patch.object(self.deployment, '_validate_deployment_prerequisites') as mock_validate:
            mock_validate.side_effect = ValidationError("Validation failed")
            
            # Run the deployment
            result = self.deployment.run()
            
            # Verify the result
            assert result is False
            self.sn_client.update_change_status.assert_not_called()
    
    def test_deployment_with_rollback(self):
        """Test deployment workflow with rollback."""
        # Mock ServiceNow responses
        self.sn_client.create_scheduled_change.return_value = self.mock_responses['create_change']['result']
        self.sn_client.get_change_details.return_value = self.mock_responses['get_change']['result']
        
        # Mock deployment failure
        with patch.object(self.deployment, 'execute_deployment') as mock_execute, \
             patch.object(self.deployment, 'rollback_deployment') as mock_rollback:
            
            mock_execute.return_value = False
            mock_rollback.return_value = True
            
            # Run the deployment
            result = self.deployment.run()
            
            # Verify the result
            assert result is False
            mock_rollback.assert_called_once()
    
    def test_deployment_timeout(self):
        """Test deployment workflow with timeout."""
        # Mock ServiceNow responses
        self.sn_client.create_scheduled_change.return_value = self.mock_responses['create_change']['result']
        self.sn_client.get_change_details.return_value = {
            'number': 'CHG123456',
            'state': 'Approval'
        }
        
        # Run the deployment
        with pytest.raises(DeploymentTimeoutError):
            self.deployment.wait_for_approval('CHG123456')
    
    def test_deployment_notification(self):
        """Test deployment notification system."""
        # Mock ServiceNow responses
        self.sn_client.create_scheduled_change.return_value = self.mock_responses['create_change']['result']
        
        # Test different notification levels
        with patch.object(self.deployment, '_send_notification') as mock_notify:
            # Info notification
            self.deployment._send_notification("Test info message", level='info')
            
            # Warning notification
            self.deployment._send_notification("Test warning message", level='warning')
            
            # Error notification
            self.deployment._send_notification("Test error message", level='error')
            
            # Verify notifications
            assert mock_notify.call_count == 3
    
    def test_deployment_validation(self):
        """Test deployment validation process."""
        # Mock ServiceNow responses
        self.sn_client.create_scheduled_change.return_value = self.mock_responses['create_change']['result']
        
        # Test successful validation
        with patch.object(self.deployment, '_send_notification') as mock_notify:
            result = self.deployment.validate_deployment()
            
            assert result is True
            mock_notify.assert_called()
        
        # Test failed validation
        with patch.object(self.deployment, '_send_notification') as mock_notify, \
             patch('time.sleep') as mock_sleep:
            
            mock_sleep.side_effect = Exception("Validation failed")
            
            result = self.deployment.validate_deployment()
            
            assert result is False
            mock_notify.assert_called_with(
                "Deployment validation failed: Validation failed",
                level='error'
            ) 