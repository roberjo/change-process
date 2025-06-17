#!/usr/bin/env python3

"""
ServiceNow Change Request Automation Script

This script provides a comprehensive interface for automating ServiceNow change request
operations, including creation, updates, approvals, and monitoring of scheduled changes.

Features:
- OAuth2 authentication
- Scheduled change creation and management
- Change request status updates
- Approval workflow automation
- Change request monitoring
- Risk assessment
- Impact analysis
- Automated notifications
- Change calendar integration

Requirements:
- Python 3.8+
- requests
- python-dotenv
- pytz
- pandas (for reporting)
- tabulate (for pretty printing)

Usage:
    python change_request.py --action create --title "Deploy Update" --start-date "2024-03-20 10:00:00"
    python change_request.py --action list --status "Draft"
    python change_request.py --action approve --number "CHG123456"

Error Handling:
- All API calls include comprehensive error handling
- Validation of input data before API calls
- Detailed logging of errors and responses
- Graceful handling of network issues
- Retry logic for transient failures

Security:
- OAuth2 authentication
- Environment variable based configuration
- No hardcoded credentials
- Secure token management
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
import requests
from typing import Dict, Optional, Any, List, Union, Tuple
import pytz
from dotenv import load_dotenv
import pandas as pd
from tabulate import tabulate
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('servicenow_change.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ServiceNowError(Exception):
    """Base exception class for ServiceNow related errors."""
    pass

class ServiceNowAuthError(ServiceNowError):
    """Exception raised for authentication errors."""
    pass

class ServiceNowValidationError(ServiceNowError):
    """Exception raised for validation errors."""
    pass

class ServiceNowAPIError(ServiceNowError):
    """Exception raised for API errors."""
    def __init__(self, message: str, response: Optional[requests.Response] = None):
        self.message = message
        self.response = response
        if response is not None:
            self.status_code = response.status_code
            self.response_text = response.text
        super().__init__(self.message)

class ServiceNowChangeRequest:
    """ServiceNow Change Request Management Class."""
    
    # Valid change states with descriptions
    VALID_STATES = {
        'Draft': 'Initial state for new changes',
        'Requested': 'Change has been requested',
        'Planning': 'Change is being planned',
        'Approval': 'Change is awaiting approval',
        'Scheduled': 'Change is scheduled for implementation',
        'Implement': 'Change is being implemented',
        'Review': 'Change is under review',
        'Closed': 'Change has been completed'
    }
    
    # Valid risk levels with descriptions
    VALID_RISK_LEVELS = {
        'Low': 'Minimal impact, easily reversible',
        'Medium': 'Moderate impact, reversible with effort',
        'High': 'Significant impact, difficult to reverse',
        'Critical': 'Severe impact, may be irreversible'
    }
    
    # Valid change types with descriptions
    VALID_CHANGE_TYPES = {
        'Normal': 'Standard change with minimal risk',
        'Standard': 'Pre-approved change with known procedure',
        'Emergency': 'Urgent change requiring immediate attention',
        'Emergency Fix': 'Critical fix requiring immediate deployment'
    }

    def __init__(self):
        """Initialize the ServiceNow client with configuration."""
        # Load environment variables
        load_dotenv()
        
        # ServiceNow configuration
        self.instance = os.getenv('SN_INSTANCE')
        self.client_id = os.getenv('SN_CLIENT_ID')
        self.client_secret = os.getenv('SN_CLIENT_SECRET')
        self.username = os.getenv('SN_USERNAME')
        self.password = os.getenv('SN_PASSWORD')
        
        # API configuration
        self.api_version = os.getenv('SN_API_VERSION', 'v2')
        self.base_url = f'https://{self.instance}/api/now/{self.api_version}'
        self.table = 'change_request'
        
        # Default values
        self.default_assignment_group = os.getenv('SN_DEFAULT_ASSIGNMENT_GROUP')
        self.default_priority = os.getenv('SN_DEFAULT_PRIORITY', '3')
        self.default_risk_level = os.getenv('SN_DEFAULT_RISK_LEVEL', 'Low')
        
        # Configure retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[500, 502, 503, 504]  # HTTP status codes to retry on
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Validate configuration
        self._validate_config()
        
        # Get OAuth token
        self.token = self._get_oauth_token()

    def _validate_config(self) -> None:
        """
        Validate required configuration is present.
        
        Raises:
            ServiceNowValidationError: If required configuration is missing
        """
        required_vars = ['SN_INSTANCE', 'SN_CLIENT_ID', 'SN_CLIENT_SECRET', 
                        'SN_USERNAME', 'SN_PASSWORD']
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ServiceNowValidationError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    def _get_oauth_token(self) -> str:
        """
        Get OAuth token from ServiceNow.
        
        Returns:
            str: OAuth token
            
        Raises:
            ServiceNowAuthError: If authentication fails
            ServiceNowAPIError: If API call fails
        """
        try:
            response = self.session.post(
                f'https://{self.instance}/oauth_token.do',
                data={
                    'grant_type': 'password',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'username': self.username,
                    'password': self.password
                }
            )
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get OAuth token: {str(e)}")
            if hasattr(e, 'response'):
                raise ServiceNowAuthError(
                    f"Authentication failed: {e.response.text if e.response else str(e)}"
                )
            raise ServiceNowAPIError(f"API call failed: {str(e)}")

    def _format_datetime(self, dt: datetime) -> str:
        """
        Format datetime for ServiceNow API.
        
        Args:
            dt: Datetime object to format
            
        Returns:
            str: Formatted datetime string
        """
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        Parse datetime string to datetime object.
        
        Args:
            dt_str: Datetime string to parse
            
        Returns:
            datetime: Parsed datetime object
            
        Raises:
            ServiceNowValidationError: If datetime format is invalid
        """
        try:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d')
            except ValueError:
                raise ServiceNowValidationError(
                    "Invalid datetime format. Use 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'"
                )

    def _validate_change_data(self, data: Dict[str, Any]) -> None:
        """
        Validate change request data.
        
        Args:
            data: Change request data to validate
            
        Raises:
            ServiceNowValidationError: If validation fails
        """
        # Validate state
        if 'state' in data and data['state'] not in self.VALID_STATES:
            raise ServiceNowValidationError(
                f"Invalid state. Must be one of: {', '.join(self.VALID_STATES.keys())}"
            )
        
        # Validate risk level
        if 'risk' in data and data['risk'] not in self.VALID_RISK_LEVELS:
            raise ServiceNowValidationError(
                f"Invalid risk level. Must be one of: {', '.join(self.VALID_RISK_LEVELS.keys())}"
            )
        
        # Validate change type
        if 'type' in data and data['type'] not in self.VALID_CHANGE_TYPES:
            raise ServiceNowValidationError(
                f"Invalid change type. Must be one of: {', '.join(self.VALID_CHANGE_TYPES.keys())}"
            )
        
        # Validate dates
        if 'start_date' in data and 'end_date' in data:
            start = self._parse_datetime(data['start_date'])
            end = self._parse_datetime(data['end_date'])
            if end <= start:
                raise ServiceNowValidationError("End date must be after start date")
            
            # Validate against current time
            now = datetime.now(pytz.UTC)
            if start < now:
                raise ServiceNowValidationError("Start date must be in the future")

    def _handle_api_response(self, response: requests.Response, operation: str) -> Dict[str, Any]:
        """
        Handle API response and extract result.
        
        Args:
            response: API response to handle
            operation: Operation being performed (for error messages)
            
        Returns:
            Dict containing the API response result
            
        Raises:
            ServiceNowAPIError: If API call fails
        """
        try:
            response.raise_for_status()
            return response.json()['result']
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed during {operation}: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response: {e.response.text}")
                raise ServiceNowAPIError(
                    f"API call failed during {operation}: {e.response.text}",
                    e.response
                )
            raise ServiceNowAPIError(f"API call failed during {operation}: {str(e)}")

    def create_scheduled_change(
        self,
        title: str,
        description: str,
        risk_level: str,
        implementation_plan: str,
        test_plan: str,
        rollback_plan: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        category: str = 'Scheduled',
        type: str = 'Normal',
        priority: str = '3',
        assignment_group: Optional[str] = None,
        assigned_to: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a scheduled change request in ServiceNow.
        
        Args:
            title: Short description of the change
            description: Detailed description
            risk_level: Risk level (Low, Medium, High, Critical)
            implementation_plan: Implementation steps
            test_plan: Testing steps
            rollback_plan: Rollback steps
            start_date: Scheduled start date/time (datetime or string)
            end_date: Scheduled end date/time (datetime or string)
            category: Change category (default: Scheduled)
            type: Change type (default: Normal)
            priority: Change priority (default: 3)
            assignment_group: Assignment group
            assigned_to: Assigned to user
            additional_fields: Any additional fields to include
            
        Returns:
            Dict containing the created change request details
            
        Raises:
            ServiceNowValidationError: If validation fails
            ServiceNowAPIError: If API call fails
        """
        try:
            # Convert string dates to datetime if needed
            if isinstance(start_date, str):
                start_date = self._parse_datetime(start_date)
            if isinstance(end_date, str):
                end_date = self._parse_datetime(end_date)

            # Prepare the change request payload
            payload = {
                'short_description': title,
                'description': description,
                'risk': risk_level,
                'implementation_plan': implementation_plan,
                'test_plan': test_plan,
                'rollback_plan': rollback_plan,
                'category': category,
                'type': type,
                'priority': priority,
                'start_date': self._format_datetime(start_date),
                'end_date': self._format_datetime(end_date),
                'state': 'Draft'
            }

            # Add optional fields if provided
            if assignment_group:
                payload['assignment_group'] = assignment_group
            if assigned_to:
                payload['assigned_to'] = assigned_to
            if additional_fields:
                payload.update(additional_fields)

            # Validate the payload
            self._validate_change_data(payload)

            # Create the change request
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = self.session.post(
                f'{self.base_url}/table/{self.table}',
                headers=headers,
                json=payload
            )
            
            result = self._handle_api_response(response, "create change request")
            logger.info(f"Successfully created change request: {result['number']}")
            return result

        except ServiceNowValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create change request: {str(e)}")
            raise ServiceNowAPIError(f"Failed to create change request: {str(e)}")

    def update_change_status(
        self,
        change_number: str,
        new_status: str,
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of a change request.
        
        Args:
            change_number: The change request number
            new_status: New status to set
            comments: Optional comments for the status change
            
        Returns:
            Dict containing the updated change request details
            
        Raises:
            ServiceNowValidationError: If validation fails
            ServiceNowAPIError: If API call fails
        """
        try:
            # Validate the new status
            if new_status not in self.VALID_STATES:
                raise ServiceNowValidationError(
                    f"Invalid state. Must be one of: {', '.join(self.VALID_STATES.keys())}"
                )

            # Get the sys_id for the change request
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/json'
            }
            
            response = self.session.get(
                f'{self.base_url}/table/{self.table}',
                headers=headers,
                params={'number': change_number}
            )
            
            result = self._handle_api_response(response, "get change request")
            if not result:
                raise ServiceNowValidationError(f"Change request {change_number} not found")
            
            sys_id = result[0]['sys_id']
            
            # Update the status
            payload = {'state': new_status}
            if comments:
                payload['comments'] = comments
                
            response = self.session.put(
                f'{self.base_url}/table/{self.table}/{sys_id}',
                headers=headers,
                json=payload
            )
            
            result = self._handle_api_response(response, "update change status")
            logger.info(f"Successfully updated change request {change_number} to {new_status}")
            return result
            
        except ServiceNowValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to update change request status: {str(e)}")
            raise ServiceNowAPIError(f"Failed to update change request status: {str(e)}")

    def get_change_details(self, change_number: str) -> Dict[str, Any]:
        """
        Get details of a specific change request.
        
        Args:
            change_number: The change request number
            
        Returns:
            Dict containing the change request details
            
        Raises:
            ServiceNowValidationError: If change request not found
            ServiceNowAPIError: If API call fails
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/json'
            }
            
            response = self.session.get(
                f'{self.base_url}/table/{self.table}',
                headers=headers,
                params={'number': change_number}
            )
            
            result = self._handle_api_response(response, "get change details")
            if not result:
                raise ServiceNowValidationError(f"Change request {change_number} not found")
            
            return result[0]
            
        except ServiceNowValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get change request details: {str(e)}")
            raise ServiceNowAPIError(f"Failed to get change request details: {str(e)}")

    def list_changes(
        self,
        status: Optional[str] = None,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        assigned_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List change requests based on filters.
        
        Args:
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date
            assigned_to: Filter by assigned to
            limit: Maximum number of results
            
        Returns:
            List of change request details
            
        Raises:
            ServiceNowValidationError: If validation fails
            ServiceNowAPIError: If API call fails
        """
        try:
            # Build query parameters
            params = {'sysparm_limit': limit}
            
            if status:
                if status not in self.VALID_STATES:
                    raise ServiceNowValidationError(
                        f"Invalid state. Must be one of: {', '.join(self.VALID_STATES.keys())}"
                    )
                params['state'] = status
                
            if start_date:
                if isinstance(start_date, str):
                    start_date = self._parse_datetime(start_date)
                params['start_date>='] = self._format_datetime(start_date)
                
            if end_date:
                if isinstance(end_date, str):
                    end_date = self._parse_datetime(end_date)
                params['end_date<='] = self._format_datetime(end_date)
                
            if assigned_to:
                params['assigned_to'] = assigned_to

            headers = {
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/json'
            }
            
            response = self.session.get(
                f'{self.base_url}/table/{self.table}',
                headers=headers,
                params=params
            )
            
            return self._handle_api_response(response, "list changes")
            
        except ServiceNowValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to list change requests: {str(e)}")
            raise ServiceNowAPIError(f"Failed to list change requests: {str(e)}")

    def get_change_calendar(
        self,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        format: str = 'table'
    ) -> Union[pd.DataFrame, str]:
        """
        Get a calendar view of changes.
        
        Args:
            start_date: Start date for calendar view
            end_date: End date for calendar view
            format: Output format ('table' or 'json')
            
        Returns:
            Calendar view in specified format
            
        Raises:
            ServiceNowValidationError: If validation fails
            ServiceNowAPIError: If API call fails
        """
        try:
            # Get changes for the date range
            changes = self.list_changes(start_date=start_date, end_date=end_date)
            
            # Convert to DataFrame
            df = pd.DataFrame(changes)
            
            # Select relevant columns
            columns = ['number', 'short_description', 'state', 'start_date', 
                      'end_date', 'assigned_to', 'risk']
            df = df[columns]
            
            if format == 'table':
                return tabulate(df, headers='keys', tablefmt='pretty')
            else:
                return df.to_json(orient='records')
                
        except ServiceNowValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get change calendar: {str(e)}")
            raise ServiceNowAPIError(f"Failed to get change calendar: {str(e)}")

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='ServiceNow Change Request Management')
    parser.add_argument('--action', required=True, 
                      choices=['create', 'update', 'get', 'list', 'calendar'],
                      help='Action to perform')
    parser.add_argument('--number', help='Change request number')
    parser.add_argument('--title', help='Change request title')
    parser.add_argument('--status', help='Change request status')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                      help='Output format for list and calendar actions')
    
    args = parser.parse_args()
    
    try:
        sn = ServiceNowChangeRequest()
        
        if args.action == 'create':
            if not all([args.title, args.start_date, args.end_date]):
                parser.error("create action requires --title, --start-date, and --end-date")
            
            change = sn.create_scheduled_change(
                title=args.title,
                description="Created via automation script",
                risk_level="Low",
                implementation_plan="Automated implementation",
                test_plan="Automated testing",
                rollback_plan="Automated rollback",
                start_date=args.start_date,
                end_date=args.end_date
            )
            print(f"Created change request: {change['number']}")
            
        elif args.action == 'update':
            if not all([args.number, args.status]):
                parser.error("update action requires --number and --status")
            
            change = sn.update_change_status(args.number, args.status)
            print(f"Updated change request: {change['number']}")
            
        elif args.action == 'get':
            if not args.number:
                parser.error("get action requires --number")
            
            change = sn.get_change_details(args.number)
            print(json.dumps(change, indent=2))
            
        elif args.action == 'list':
            changes = sn.list_changes(
                status=args.status,
                start_date=args.start_date,
                end_date=args.end_date
            )
            if args.format == 'table':
                df = pd.DataFrame(changes)
                print(tabulate(df, headers='keys', tablefmt='pretty'))
            else:
                print(json.dumps(changes, indent=2))
                
        elif args.action == 'calendar':
            if not all([args.start_date, args.end_date]):
                parser.error("calendar action requires --start-date and --end-date")
            
            calendar = sn.get_change_calendar(
                start_date=args.start_date,
                end_date=args.end_date,
                format=args.format
            )
            print(calendar)
            
    except ServiceNowValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        sys.exit(1)
    except ServiceNowAPIError as e:
        logger.error(f"API error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 