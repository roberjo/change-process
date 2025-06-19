#!/usr/bin/env python3
"""
Command Line Interface for Change Process Automation

Provides a unified CLI for all change management operations.
"""

import click
import logging
import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import re

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import ConfigManager
from scripts.servicenow.change_request import ServiceNowChangeRequest
from scripts.communications.notification_manager import NotificationManager, NotificationType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_datetime_format(date_string: str, field_name: str) -> datetime:
    """
    Validate and parse datetime string in format 'YYYY-MM-DD HH:MM:SS'.
    
    Args:
        date_string: The date string to validate and parse
        field_name: Name of the field for error messages
        
    Returns:
        Parsed datetime object
        
    Raises:
        click.BadParameter: If date format is invalid
    """
    expected_format = '%Y-%m-%d %H:%M:%S'
    
    # Check if the string matches the expected pattern
    pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'
    if not re.match(pattern, date_string):
        raise click.BadParameter(
            f"Invalid {field_name} format: '{date_string}'. "
            f"Expected format: YYYY-MM-DD HH:MM:SS (e.g., '2024-01-15 14:30:00')"
        )
    
    try:
        return datetime.strptime(date_string, expected_format)
    except ValueError as e:
        raise click.BadParameter(
            f"Invalid {field_name}: '{date_string}'. "
            f"Date/time values are invalid. Expected format: YYYY-MM-DD HH:MM:SS (e.g., '2024-01-15 14:30:00')"
        )

@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """Change Process Automation CLI"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize configuration
    try:
        config_manager = ConfigManager(config)
        ctx.obj = {
            'config': config_manager.get_config(),
            'sn_client': ServiceNowChangeRequest(config_manager.get_config().servicenow),
            'notifications': NotificationManager({
                'teams_webhook_url': config_manager.get_config().notifications.teams_webhook_url,
                'email_smtp_server': config_manager.get_config().notifications.email_smtp_server,
                'email_smtp_port': config_manager.get_config().notifications.email_smtp_port,
                'email_username': config_manager.get_config().notifications.email_username,
                'email_password': config_manager.get_config().notifications.email_password,
            })
        }
    except Exception as e:
        click.echo(f"Configuration error: {str(e)}", err=True)
        sys.exit(1)

@cli.group()
def change():
    """Change request management commands"""
    pass

@change.command()
@click.option('--title', '-t', required=True, help='Change request title')
@click.option('--description', '-d', required=True, help='Change request description')
@click.option('--start-date', '-s', required=True, help='Start date (YYYY-MM-DD HH:MM:SS)')
@click.option('--end-date', '-e', required=True, help='End date (YYYY-MM-DD HH:MM:SS)')
@click.option('--risk-level', '-r', default='Low', 
              type=click.Choice(['Low', 'Medium', 'High', 'Critical']),
              help='Risk level')
@click.option('--type', default='Normal',
              type=click.Choice(['Normal', 'Standard', 'Emergency', 'Emergency Fix']),
              help='Change type')
@click.option('--priority', '-p', default='3',
              type=click.Choice(['1', '2', '3', '4', '5']),
              help='Priority (1=highest, 5=lowest)')
@click.option('--implementation-plan', '-i', help='Implementation plan')
@click.option('--test-plan', help='Test plan')
@click.option('--rollback-plan', help='Rollback plan')
@click.pass_context
def create(ctx, title: str, description: str, start_date: str, end_date: str,
           risk_level: str, type: str, priority: str, implementation_plan: str,
           test_plan: str, rollback_plan: str):
    """Create a new change request"""
    try:
        sn_client = ctx.obj['sn_client']
        
        # Parse dates with validation
        start_dt = validate_datetime_format(start_date, 'start date')
        end_dt = validate_datetime_format(end_date, 'end date')
        
        # Validate that end date is after start date
        if end_dt <= start_dt:
            raise click.BadParameter(
                f"End date ({end_date}) must be after start date ({start_date})"
            )
        
        # Create change request
        change = sn_client.create_scheduled_change(
            title=title,
            description=description,
            risk_level=risk_level,
            implementation_plan=implementation_plan or "Standard implementation plan",
            test_plan=test_plan or "Standard test plan",
            rollback_plan=rollback_plan or "Standard rollback plan",
            start_date=start_dt,
            end_date=end_dt,
            type=type,
            priority=priority
        )
        
        click.echo(f"✅ Change request created successfully: {change['number']}")
        
        # Send notification
        notifications = ctx.obj['notifications']
        notifications.send_change_notification(
            change_number=change['number'],
            status='Created',
            title=title,
            description=description,
            priority='normal' if risk_level == 'Low' else 'high'
        )
        
    except click.BadParameter as e:
        click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Failed to create change request: {str(e)}", err=True)
        sys.exit(1)

@change.command()
@click.option('--number', '-n', required=True, help='Change request number')
@click.option('--status', '-s', required=True,
              type=click.Choice(['Draft', 'Requested', 'Planning', 'Approval', 
                               'Scheduled', 'Implement', 'Review', 'Closed']),
              help='New status')
@click.option('--comments', '-c', help='Status change comments')
@click.pass_context
def update_status(ctx, number: str, status: str, comments: str):
    """Update change request status"""
    try:
        sn_client = ctx.obj['sn_client']
        
        change = sn_client.update_change_status(number, status, comments)
        click.echo(f"✅ Change request {number} status updated to {status}")
        
        # Send notification
        notifications = ctx.obj['notifications']
        notifications.send_change_notification(
            change_number=number,
            status=status,
            title=f"Status updated to {status}",
            description=comments or f"Status changed to {status}",
            priority='normal'
        )
        
    except Exception as e:
        click.echo(f"❌ Failed to update change request status: {str(e)}", err=True)
        sys.exit(1)

@change.command()
@click.option('--status', '-s', help='Filter by status')
@click.option('--start-date', help='Filter by start date (YYYY-MM-DD)')
@click.option('--end-date', help='Filter by end date (YYYY-MM-DD)')
@click.option('--limit', '-l', default=10, help='Maximum number of results')
@click.pass_context
def list(ctx, status: Optional[str], start_date: Optional[str], 
         end_date: Optional[str], limit: int):
    """List change requests"""
    try:
        sn_client = ctx.obj['sn_client']
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        changes = sn_client.list_changes(
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit
        )
        
        if not changes:
            click.echo("No change requests found")
            return
        
        # Display results
        click.echo(f"\nFound {len(changes)} change request(s):")
        click.echo("-" * 80)
        
        for change in changes:
            click.echo(f"Number: {change.get('number', 'N/A')}")
            click.echo(f"Title: {change.get('short_description', 'N/A')}")
            click.echo(f"Status: {change.get('state', 'N/A')}")
            click.echo(f"Risk: {change.get('risk', 'N/A')}")
            click.echo(f"Start: {change.get('start_date', 'N/A')}")
            click.echo(f"End: {change.get('end_date', 'N/A')}")
            click.echo("-" * 80)
        
    except Exception as e:
        click.echo(f"❌ Failed to list change requests: {str(e)}", err=True)
        sys.exit(1)

@cli.group()
def deployment():
    """Deployment management commands"""
    pass

@deployment.command()
@click.option('--version', '-v', required=True, help='Version to deploy')
@click.option('--environment', '-e', required=True,
              type=click.Choice(['development', 'staging', 'production']),
              help='Target environment')
@click.option('--auto-approve', is_flag=True, help='Skip manual approval')
@click.pass_context
def deploy(ctx, version: str, environment: str, auto_approve: bool):
    """Deploy a version to an environment"""
    try:
        from scripts.examples.automated_deployment import AutomatedDeployment
        
        deployment = AutomatedDeployment(version, environment)
        
        if auto_approve:
            click.echo(f"🚀 Starting automated deployment of {version} to {environment}")
        else:
            click.echo(f"📋 Creating deployment plan for {version} to {environment}")
        
        success = deployment.run()
        
        if success:
            click.echo(f"✅ Deployment completed successfully")
            
            # Send notification
            notifications = ctx.obj['notifications']
            notifications.send_deployment_notification(
                version=version,
                environment=environment,
                status='Completed',
                details='Deployment completed successfully',
                priority='normal'
            )
        else:
            click.echo(f"❌ Deployment failed")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Deployment error: {str(e)}", err=True)
        sys.exit(1)

@cli.group()
def notifications():
    """Notification management commands"""
    pass

@notifications.command()
@click.option('--title', '-t', required=True, help='Notification title')
@click.option('--message', '-m', required=True, help='Notification message')
@click.option('--priority', '-p', default='normal',
              type=click.Choice(['low', 'normal', 'high', 'urgent']),
              help='Message priority')
@click.option('--channels', '-c', multiple=True,
              type=click.Choice(['teams', 'email']),
              help='Notification channels')
@click.pass_context
def send(ctx, title: str, message: str, priority: str, channels):
    """Send a notification"""
    try:
        notifications = ctx.obj['notifications']
        
        from scripts.communications.notification_manager import NotificationMessage
        
        msg = NotificationMessage(
            title=title,
            body=message,
            priority=priority
        )
        
        # Convert channel names to enum values
        channel_types = []
        if 'teams' in channels:
            channel_types.append(NotificationType.TEAMS)
        if 'email' in channels:
            channel_types.append(NotificationType.EMAIL)
        
        results = notifications.send_notification(msg, channel_types)
        
        for channel, success in results.items():
            if success:
                click.echo(f"✅ Notification sent via {channel.value}")
            else:
                click.echo(f"❌ Failed to send notification via {channel.value}")
                
    except Exception as e:
        click.echo(f"❌ Notification error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
def version():
    """Show version information"""
    click.echo("Change Process Automation v1.0.0")

if __name__ == '__main__':
    cli() 