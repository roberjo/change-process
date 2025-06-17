#!/usr/bin/env python3

"""
Automated Deployment Script with ServiceNow Integration

This script demonstrates how to automate the deployment process while creating and managing
change requests in ServiceNow. It handles the entire deployment lifecycle from change request
creation to post-deployment validation.

Features:
- Automated change request creation
- Approval workflow management
- Deployment execution
- Post-deployment validation
- Comprehensive error handling
- Detailed logging
- Status notifications

Requirements:
- Python 3.8+
- requests
- python-dotenv
- pytz
- logging

Usage:
    python automated_deployment.py --version "1.0.0" --environment "production"
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Union
import pytz
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add parent directory to path to import ServiceNow module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from servicenow.change_request import ServiceNowChangeRequest, ServiceNowError

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('automated_deployment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DeploymentError(Exception):
    """Base exception class for deployment related errors."""
    pass

class ValidationError(DeploymentError):
    """Exception raised for validation errors."""
    pass

class DeploymentTimeoutError(DeploymentError):
    """Exception raised when deployment times out."""
    pass

class AutomatedDeployment:
    """Automated Deployment Management Class."""
    
    # Valid deployment environments
    VALID_ENVIRONMENTS = {
        'development': 'Development environment',
        'staging': 'Staging environment',
        'production': 'Production environment'
    }
    
    # Deployment timeouts (in seconds)
    TIMEOUTS = {
        'approval': 3600,  # 1 hour
        'deployment': 1800,  # 30 minutes
        'validation': 900   # 15 minutes
    }
    
    # Deployment statuses
    STATUSES = {
        'pending': 'Deployment pending',
        'in_progress': 'Deployment in progress',
        'completed': 'Deployment completed',
        'failed': 'Deployment failed',
        'rolled_back': 'Deployment rolled back'
    }

    def __init__(self, version: str, environment: str):
        """
        Initialize the automated deployment.
        
        Args:
            version: Version to deploy
            environment: Target environment
            
        Raises:
            ValidationError: If version or environment is invalid
        """
        # Load environment variables
        load_dotenv()
        
        # Validate inputs
        if not version or not isinstance(version, str):
            raise ValidationError("Version must be a non-empty string")
            
        if environment not in self.VALID_ENVIRONMENTS:
            raise ValidationError(
                f"Invalid environment. Must be one of: {', '.join(self.VALID_ENVIRONMENTS.keys())}"
            )
        
        self.version = version
        self.environment = environment
        self.status = 'pending'
        self.start_time = None
        self.end_time = None
        
        # Initialize ServiceNow client
        try:
            self.sn = ServiceNowChangeRequest()
        except ServiceNowError as e:
            logger.error(f"Failed to initialize ServiceNow client: {str(e)}")
            raise DeploymentError(f"ServiceNow initialization failed: {str(e)}")
        
        # Configure retry strategy for HTTP requests
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[500, 502, 503, 504]  # HTTP status codes to retry on
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _validate_deployment_prerequisites(self) -> None:
        """
        Validate deployment prerequisites.
        
        Raises:
            ValidationError: If prerequisites are not met
        """
        # Check if version exists in artifact repository
        try:
            # TODO: Implement artifact repository check
            pass
        except Exception as e:
            raise ValidationError(f"Failed to validate version: {str(e)}")
        
        # Check if environment is ready
        try:
            # TODO: Implement environment readiness check
            pass
        except Exception as e:
            raise ValidationError(f"Failed to validate environment: {str(e)}")
        
        # Check for conflicting deployments
        try:
            # TODO: Implement conflict check
            pass
        except Exception as e:
            raise ValidationError(f"Failed to check for conflicts: {str(e)}")

    def _send_notification(self, message: str, level: str = 'info') -> None:
        """
        Send deployment notification.
        
        Args:
            message: Notification message
            level: Message level (info, warning, error)
            
        Raises:
            DeploymentError: If notification fails
        """
        try:
            # TODO: Implement notification system
            logger.log(
                logging.INFO if level == 'info' else logging.WARNING if level == 'warning' else logging.ERROR,
                message
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            # Don't raise error as notification failure shouldn't stop deployment

    def create_change_request(self) -> Dict[str, Any]:
        """
        Create a change request for the deployment.
        
        Returns:
            Dict containing the created change request details
            
        Raises:
            DeploymentError: If change request creation fails
        """
        try:
            # Calculate deployment window
            now = datetime.now(pytz.UTC)
            start_time = now + timedelta(hours=1)  # Start in 1 hour
            end_time = start_time + timedelta(hours=2)  # 2-hour window
            
            # Create change request
            change = self.sn.create_scheduled_change(
                title=f"Deploy version {self.version} to {self.environment}",
                description=f"Automated deployment of version {self.version} to {self.environment} environment",
                risk_level="Low",
                implementation_plan=f"""
                1. Deploy version {self.version} to {self.environment}
                2. Run automated tests
                3. Validate deployment
                4. Update documentation
                """,
                test_plan=f"""
                1. Run unit tests
                2. Run integration tests
                3. Run performance tests
                4. Validate functionality
                """,
                rollback_plan=f"""
                1. Stop new version
                2. Restore previous version
                3. Verify rollback
                4. Update status
                """,
                start_date=start_time,
                end_date=end_time,
                category="Scheduled",
                type="Normal"
            )
            
            self._send_notification(
                f"Created change request {change['number']} for version {self.version}"
            )
            return change
            
        except ServiceNowError as e:
            logger.error(f"Failed to create change request: {str(e)}")
            raise DeploymentError(f"Change request creation failed: {str(e)}")

    def wait_for_approval(self, change_number: str) -> bool:
        """
        Wait for change request approval.
        
        Args:
            change_number: Change request number
            
        Returns:
            bool: True if approved, False if rejected
            
        Raises:
            DeploymentTimeoutError: If approval times out
            DeploymentError: If approval check fails
        """
        try:
            start_time = time.time()
            while time.time() - start_time < self.TIMEOUTS['approval']:
                # Get change request status
                change = self.sn.get_change_details(change_number)
                status = change['state']
                
                if status == 'Approval':
                    logger.info(f"Change request {change_number} is pending approval")
                    time.sleep(60)  # Check every minute
                    continue
                    
                if status == 'Scheduled':
                    logger.info(f"Change request {change_number} has been approved")
                    return True
                    
                if status == 'Closed':
                    logger.warning(f"Change request {change_number} was rejected")
                    return False
                    
                logger.warning(f"Unexpected change request status: {status}")
                return False
                
            raise DeploymentTimeoutError(
                f"Approval timeout after {self.TIMEOUTS['approval']} seconds"
            )
            
        except ServiceNowError as e:
            logger.error(f"Failed to check approval status: {str(e)}")
            raise DeploymentError(f"Approval check failed: {str(e)}")

    def execute_deployment(self, change_number: str) -> bool:
        """
        Execute the deployment.
        
        Args:
            change_number: Change request number
            
        Returns:
            bool: True if deployment successful, False otherwise
            
        Raises:
            DeploymentError: If deployment fails
        """
        try:
            # Validate prerequisites
            self._validate_deployment_prerequisites()
            
            # Update change request status
            self.sn.update_change_status(change_number, 'Implement')
            self._send_notification(f"Starting deployment of version {self.version}")
            
            # Record start time
            self.start_time = datetime.now(pytz.UTC)
            
            # TODO: Implement actual deployment steps
            # This is where you would:
            # 1. Deploy the new version
            # 2. Run automated tests
            # 3. Validate the deployment
            # 4. Update documentation
            
            # Simulate deployment steps
            logger.info("Deploying new version...")
            time.sleep(5)  # Simulate deployment time
            
            logger.info("Running automated tests...")
            time.sleep(5)  # Simulate test execution
            
            logger.info("Validating deployment...")
            time.sleep(5)  # Simulate validation
            
            # Record end time
            self.end_time = datetime.now(pytz.UTC)
            
            # Update change request status
            self.sn.update_change_status(change_number, 'Review')
            self._send_notification(
                f"Deployment of version {self.version} completed successfully"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            self._send_notification(
                f"Deployment of version {self.version} failed: {str(e)}",
                level='error'
            )
            
            # Update change request status
            try:
                self.sn.update_change_status(
                    change_number,
                    'Closed',
                    comments=f"Deployment failed: {str(e)}"
                )
            except ServiceNowError as sn_error:
                logger.error(f"Failed to update change request status: {str(sn_error)}")
            
            return False

    def validate_deployment(self) -> bool:
        """
        Validate the deployment.
        
        Returns:
            bool: True if validation successful, False otherwise
            
        Raises:
            DeploymentError: If validation fails
        """
        try:
            # TODO: Implement actual validation steps
            # This is where you would:
            # 1. Check application health
            # 2. Verify functionality
            # 3. Monitor performance
            # 4. Check logs for errors
            
            # Simulate validation steps
            logger.info("Checking application health...")
            time.sleep(2)  # Simulate health check
            
            logger.info("Verifying functionality...")
            time.sleep(2)  # Simulate functionality check
            
            logger.info("Monitoring performance...")
            time.sleep(2)  # Simulate performance check
            
            logger.info("Checking logs...")
            time.sleep(2)  # Simulate log check
            
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            self._send_notification(
                f"Deployment validation failed: {str(e)}",
                level='error'
            )
            return False

    def rollback_deployment(self) -> bool:
        """
        Rollback the deployment if it fails.
        
        Returns:
            bool: True if rollback successful, False otherwise
            
        Raises:
            DeploymentError: If rollback fails
        """
        try:
            logger.info("Starting rollback...")
            self._send_notification(
                f"Rolling back deployment of version {self.version}",
                level='warning'
            )
            
            # TODO: Implement actual rollback steps
            # This is where you would:
            # 1. Stop the new version
            # 2. Restore the previous version
            # 3. Verify the rollback
            # 4. Update documentation
            
            # Simulate rollback steps
            logger.info("Stopping new version...")
            time.sleep(2)  # Simulate stop
            
            logger.info("Restoring previous version...")
            time.sleep(2)  # Simulate restore
            
            logger.info("Verifying rollback...")
            time.sleep(2)  # Simulate verification
            
            self._send_notification(
                f"Rollback of version {self.version} completed successfully"
            )
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            self._send_notification(
                f"Rollback of version {self.version} failed: {str(e)}",
                level='error'
            )
            return False

    def run(self) -> bool:
        """
        Run the complete deployment process.
        
        Returns:
            bool: True if deployment successful, False otherwise
            
        Raises:
            DeploymentError: If deployment process fails
        """
        try:
            # Create change request
            change = self.create_change_request()
            change_number = change['number']
            
            # Wait for approval
            if not self.wait_for_approval(change_number):
                logger.warning("Deployment cancelled due to change request rejection")
                return False
            
            # Execute deployment
            if not self.execute_deployment(change_number):
                logger.error("Deployment failed")
                if not self.rollback_deployment():
                    logger.error("Rollback failed")
                return False
            
            # Validate deployment
            if not self.validate_deployment():
                logger.error("Deployment validation failed")
                if not self.rollback_deployment():
                    logger.error("Rollback failed")
                return False
            
            # Update change request status
            self.sn.update_change_status(change_number, 'Closed')
            
            # Calculate deployment duration
            if self.start_time and self.end_time:
                duration = self.end_time - self.start_time
                logger.info(f"Deployment completed in {duration}")
            
            return True
            
        except DeploymentError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during deployment: {str(e)}")
            raise DeploymentError(f"Deployment process failed: {str(e)}")

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Automated Deployment Script')
    parser.add_argument('--version', required=True, help='Version to deploy')
    parser.add_argument('--environment', required=True, 
                      choices=['development', 'staging', 'production'],
                      help='Target environment')
    
    args = parser.parse_args()
    
    try:
        deployment = AutomatedDeployment(args.version, args.environment)
        success = deployment.run()
        sys.exit(0 if success else 1)
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        sys.exit(1)
    except DeploymentTimeoutError as e:
        logger.error(f"Deployment timeout: {str(e)}")
        sys.exit(1)
    except DeploymentError as e:
        logger.error(f"Deployment error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 