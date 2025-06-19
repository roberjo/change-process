"""
Configuration management for change-process automation.
Centralizes all configuration settings and provides validation.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

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
        """Initialize configuration manager."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self.config = self._load_config()
        self._validate_config()
    
    def _safe_int(self, value: str, default: int, var_name: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            logger.warning(f"Invalid value for {var_name}: '{value}', using default {default}")
            return default
    
    def _load_config(self) -> AppConfig:
        """Load configuration from environment variables."""
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
                email_smtp_port=self._safe_int(os.getenv('EMAIL_SMTP_PORT', '587'), 587, 'EMAIL_SMTP_PORT'),
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
            timeout=self._safe_int(os.getenv('TIMEOUT', '300'), 300, 'TIMEOUT'),
            retry_attempts=self._safe_int(os.getenv('RETRY_ATTEMPTS', '3'), 3, 'RETRY_ATTEMPTS')
        )
    
    def _validate_config(self) -> None:
        """Validate required configuration settings."""
        required_sn_fields = [
            'instance', 'client_id', 'client_secret', 'username', 'password'
        ]
        
        for field in required_sn_fields:
            if not getattr(self.config.servicenow, field):
                logger.error(f"Missing required ServiceNow configuration: {field if field != 'client_secret' and field != 'password' else '***'}")
                raise ValueError(f"Missing required ServiceNow configuration: {field}")
    
    def get_config(self) -> AppConfig:
        """Get the application configuration."""
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration settings with validation and sensitive value masking in logs."""
        sensitive_keys = {'password', 'secret', 'api_key', 'client_secret'}
        updated = False
        for section_name in ['servicenow', 'notifications', 'harness']:
            section = getattr(self.config, section_name, None)
            if section and isinstance(section, object):
                for key, value in updates.items():
                    if hasattr(section, key):
                        old_value = getattr(section, key)
                        setattr(section, key, value)
                        masked_key = key.lower()
                        if any(s in masked_key for s in sensitive_keys):
                            logger.info(f"Updated config: {section_name}.{key} = *** (was ***)")
                        else:
                            logger.info(f"Updated config: {section_name}.{key} = {value} (was {old_value})")
                        updated = True
        # Top-level AppConfig fields
        for key, value in updates.items():
            if hasattr(self.config, key):
                old_value = getattr(self.config, key)
                setattr(self.config, key, value)
                masked_key = key.lower()
                if any(s in masked_key for s in sensitive_keys):
                    logger.info(f"Updated config: {key} = *** (was ***)")
                else:
                    logger.info(f"Updated config: {key} = {value} (was {old_value})")
                updated = True
        if updated:
            try:
                self._validate_config()
            except Exception as e:
                logger.error(f"Config update validation failed: {str(e)}")
                raise 