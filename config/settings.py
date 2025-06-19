"""
Configuration management for change-process automation.
Centralizes all configuration settings and provides validation.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class ServiceNowConfig:
    """ServiceNow configuration settings."""
    instance: str
    client_id: str
    client_secret: str
    username: str
    password: str
    api_version: str = "v2"
    default_assignment_group: Optional[str] = None
    default_priority: str = "3"
    default_risk_level: str = "Low"

@dataclass
class NotificationConfig:
    """Notification configuration settings."""
    teams_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None

@dataclass
class HarnessConfig:
    """Harness CI/CD configuration settings."""
    account_id: str
    api_key: str
    org_id: str
    project_id: str
    pipeline_id: str

@dataclass
class AppConfig:
    """Main application configuration."""
    servicenow: ServiceNowConfig
    notifications: NotificationConfig
    harness: Optional[HarnessConfig] = None
    log_level: str = "INFO"
    log_file: str = "change_process.log"
    timeout: int = 300
    retry_attempts: int = 3

class ConfigManager:
    """Manages application configuration with validation."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initializes the configuration manager by loading environment variables and validating the application configuration.
        
        Parameters:
            env_file (Optional[str]): Path to a .env file to load environment variables from. If not provided, defaults are used.
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> AppConfig:
        """
        Constructs and returns the application configuration by reading environment variables.
        
        Returns:
            AppConfig: The aggregated configuration object populated from environment variables, including ServiceNow, notification, and optional Harness settings.
        """
        return AppConfig(
            servicenow=ServiceNowConfig(
                instance=os.getenv('SN_INSTANCE', ''),
                client_id=os.getenv('SN_CLIENT_ID', ''),
                client_secret=os.getenv('SN_CLIENT_SECRET', ''),
                username=os.getenv('SN_USERNAME', ''),
                password=os.getenv('SN_PASSWORD', ''),
                api_version=os.getenv('SN_API_VERSION', 'v2'),
                default_assignment_group=os.getenv('SN_DEFAULT_ASSIGNMENT_GROUP'),
                default_priority=os.getenv('SN_DEFAULT_PRIORITY', '3'),
                default_risk_level=os.getenv('SN_DEFAULT_RISK_LEVEL', 'Low')
            ),
            notifications=NotificationConfig(
                teams_webhook_url=os.getenv('TEAMS_WEBHOOK_URL'),
                slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
                email_smtp_server=os.getenv('EMAIL_SMTP_SERVER'),
                email_smtp_port=int(os.getenv('EMAIL_SMTP_PORT', '587')),
                email_username=os.getenv('EMAIL_USERNAME'),
                email_password=os.getenv('EMAIL_PASSWORD')
            ),
            harness=HarnessConfig(
                account_id=os.getenv('HARNESS_ACCOUNT_ID', ''),
                api_key=os.getenv('HARNESS_API_KEY', ''),
                org_id=os.getenv('HARNESS_ORG_ID', ''),
                project_id=os.getenv('HARNESS_PROJECT_ID', ''),
                pipeline_id=os.getenv('HARNESS_PIPELINE_ID', '')
            ) if os.getenv('HARNESS_ACCOUNT_ID') else None,
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'change_process.log'),
            timeout=int(os.getenv('TIMEOUT', '300')),
            retry_attempts=int(os.getenv('RETRY_ATTEMPTS', '3'))
        )
    
    def _validate_config(self) -> None:
        """
        Checks that all required ServiceNow configuration fields are present, raising a ValueError if any are missing.
        """
        required_sn_fields = [
            'instance', 'client_id', 'client_secret', 'username', 'password'
        ]
        
        for field in required_sn_fields:
            if not getattr(self.config.servicenow, field):
                raise ValueError(f"Missing required ServiceNow configuration: {field}")
    
    def get_config(self) -> AppConfig:
        """
        Return the current application configuration.
        
        Returns:
            AppConfig: The loaded and validated application configuration.
        """
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Placeholder for dynamically updating configuration settings at runtime.
        
        Parameters:
            updates (Dict[str, Any]): Dictionary of configuration fields and their new values.
        """
        # Implementation for dynamic config updates
        pass 