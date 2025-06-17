import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pytz
from scripts.examples.automated_deployment import (
    AutomatedDeployment,
    DeploymentError,
    ValidationError,
    DeploymentTimeoutError
)

@pytest.fixture
def mock_env_vars():
    """Fixture to set up mock environment variables."""
    with patch.dict('os.environ', {
        'SN_INSTANCE': 'test-instance',
        'SN_CLIENT_ID': 'test-client-id',
        'SN_CLIENT_SECRET': 'test-client-secret',
        'SN_USERNAME': 'test-username',
        'SN_PASSWORD': 'test-password'
    }):
        yield

@pytest.fixture
def deployment(mock_env_vars):
    """Fixture to create an AutomatedDeployment instance."""
    with patch('scripts.examples.automated_deployment.ServiceNowChangeRequest') as mock_sn:
        mock_sn.return_value = Mock()
        return AutomatedDeployment(version="1.0.0", environment="production")

def test_init_invalid_version():
    """Test initialization with invalid version."""
    with pytest.raises(ValidationError) as exc_info:
        AutomatedDeployment(version="", environment="production")
    assert "Version must be a non-empty string" in str(exc_info.value)

def test_init_invalid_environment():
    """Test initialization with invalid environment."""
    with pytest.raises(ValidationError) as exc_info:
        AutomatedDeployment(version="1.0.0", environment="invalid")
    assert "Invalid environment" in str(exc_info.value)

def test_init_success(deployment):
    """Test successful initialization."""
    assert deployment.version == "1.0.0"
    assert deployment.environment == "production"
    assert deployment.status == "pending"

def test_create_change_request(deployment):
    """Test creating a change request."""
    mock_change = {
        'number': 'CHG123456',
        'state': 'Draft'
    }
    deployment.sn.create_scheduled_change.return_value = mock_change
    
    change = deployment.create_change_request()
    
    assert change['number'] == 'CHG123456'
    deployment.sn.create_scheduled_change.assert_called_once()

def test_wait_for_approval_approved(deployment):
    """Test waiting for approval when approved."""
    mock_change = {
        'state': 'Scheduled'
    }
    deployment.sn.get_change_details.return_value = mock_change
    
    result = deployment.wait_for_approval('CHG123456')
    
    assert result is True
    deployment.sn.get_change_details.assert_called_once()

def test_wait_for_approval_rejected(deployment):
    """Test waiting for approval when rejected."""
    mock_change = {
        'state': 'Closed'
    }
    deployment.sn.get_change_details.return_value = mock_change
    
    result = deployment.wait_for_approval('CHG123456')
    
    assert result is False
    deployment.sn.get_change_details.assert_called_once()

def test_wait_for_approval_timeout(deployment):
    """Test waiting for approval timeout."""
    mock_change = {
        'state': 'Approval'
    }
    deployment.sn.get_change_details.return_value = mock_change
    
    with pytest.raises(DeploymentTimeoutError) as exc_info:
        deployment.wait_for_approval('CHG123456')
    assert "Approval timeout" in str(exc_info.value)

def test_execute_deployment_success(deployment):
    """Test successful deployment execution."""
    with patch.object(deployment, '_validate_deployment_prerequisites') as mock_validate:
        mock_validate.return_value = None
        
        result = deployment.execute_deployment('CHG123456')
        
        assert result is True
        deployment.sn.update_change_status.assert_called_with('CHG123456', 'Implement')

def test_execute_deployment_validation_failure(deployment):
    """Test deployment execution with validation failure."""
    with patch.object(deployment, '_validate_deployment_prerequisites') as mock_validate:
        mock_validate.side_effect = ValidationError("Validation failed")
        
        with pytest.raises(DeploymentError) as exc_info:
            deployment.execute_deployment('CHG123456')
        assert "Validation failed" in str(exc_info.value)

def test_validate_deployment_success(deployment):
    """Test successful deployment validation."""
    with patch.object(deployment, '_send_notification') as mock_notify:
        result = deployment.validate_deployment()
        
        assert result is True
        mock_notify.assert_called()

def test_validate_deployment_failure(deployment):
    """Test deployment validation failure."""
    with patch.object(deployment, '_send_notification') as mock_notify:
        with patch('time.sleep') as mock_sleep:
            mock_sleep.side_effect = Exception("Validation failed")
            
            result = deployment.validate_deployment()
            
            assert result is False
            mock_notify.assert_called_with(
                "Deployment validation failed: Validation failed",
                level='error'
            )

def test_rollback_deployment_success(deployment):
    """Test successful deployment rollback."""
    with patch.object(deployment, '_send_notification') as mock_notify:
        result = deployment.rollback_deployment()
        
        assert result is True
        mock_notify.assert_called_with(
            f"Rolling back deployment of version {deployment.version}",
            level='warning'
        )

def test_run_successful_deployment(deployment):
    """Test successful complete deployment process."""
    # Mock all the necessary methods
    deployment.create_change_request.return_value = {'number': 'CHG123456'}
    deployment.wait_for_approval.return_value = True
    deployment.execute_deployment.return_value = True
    deployment.validate_deployment.return_value = True
    
    result = deployment.run()
    
    assert result is True
    deployment.sn.update_change_status.assert_called_with('CHG123456', 'Closed')

def test_run_approval_rejected(deployment):
    """Test deployment process with rejected approval."""
    deployment.create_change_request.return_value = {'number': 'CHG123456'}
    deployment.wait_for_approval.return_value = False
    
    result = deployment.run()
    
    assert result is False
    deployment.sn.update_change_status.assert_not_called()

def test_run_deployment_failure(deployment):
    """Test deployment process with deployment failure."""
    deployment.create_change_request.return_value = {'number': 'CHG123456'}
    deployment.wait_for_approval.return_value = True
    deployment.execute_deployment.return_value = False
    deployment.rollback_deployment.return_value = True
    
    result = deployment.run()
    
    assert result is False
    deployment.sn.update_change_status.assert_not_called()

def test_run_validation_failure(deployment):
    """Test deployment process with validation failure."""
    deployment.create_change_request.return_value = {'number': 'CHG123456'}
    deployment.wait_for_approval.return_value = True
    deployment.execute_deployment.return_value = True
    deployment.validate_deployment.return_value = False
    deployment.rollback_deployment.return_value = True
    
    result = deployment.run()
    
    assert result is False
    deployment.sn.update_change_status.assert_not_called() 