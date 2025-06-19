#!/usr/bin/env python3
"""
Command Line Interface for Change Process Automation

Provides a unified CLI for all change management operations.
"""

import click
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

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

@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """
    Initializes the Change Process Automation CLI, loading configuration and setting up required services.
    
    Parameters:
        ctx: Click context object for passing shared state between commands.
        config (str, optional): Path to the configuration file.
        verbose (bool): Enables verbose logging if True.
    
    Exits the program if configuration loading fails.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize configuration
    try:
        config_manager = ConfigManager(config)
        ctx.obj = {
            'config': config_manager.get_config(),
            'sn_client': ServiceNowChangeRequest(),
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
    """
    Defines the CLI command group for managing change requests.
    """
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
    """
           Creates a new change request in ServiceNow with the specified details and sends a notification upon success.
           
           Parameters:
               title (str): The title of the change request.
               description (str): A detailed description of the change.
               start_date (str): Scheduled start date and time in 'YYYY-MM-DD HH:MM:SS' format.
               end_date (str): Scheduled end date and time in 'YYYY-MM-DD HH:MM:SS' format.
               risk_level (str): The risk level for the change (e.g., Low, Medium, High, Critical).
               type (str): The type of change (e.g., Normal, Standard, Emergency, Emergency Fix).
               priority (str): The priority of the change (1-5).
               implementation_plan (str): The implementation plan for the change.
               test_plan (str): The test plan for the change.
               rollback_plan (str): The rollback plan for the change.
           
           On successful creation, outputs the change request number and sends a notification. Exits with an error message if creation fails.
           """
    try:
        sn_client = ctx.obj['sn_client']
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        
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
    """
    Updates the status of a specified change request and sends a notification about the status change.
    
    Parameters:
        number (str): The unique identifier of the change request to update.
        status (str): The new status to set for the change request.
        comments (str): Optional comments to include with the status update.
    """
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
    """
         List change requests with optional filters for status, start date, end date, and result limit.
         
         Parameters:
             status (Optional[str]): Filter change requests by status if provided.
             start_date (Optional[str]): Filter change requests starting on or after this date (YYYY-MM-DD).
             end_date (Optional[str]): Filter change requests ending on or before this date (YYYY-MM-DD).
             limit (int): Maximum number of change requests to display.
         
         Displays the list of matching change requests or a message if none are found.
         """
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
    """
    Defines the CLI group for deployment management commands.
    """
    pass

@deployment.command()
@click.option('--version', '-v', required=True, help='Version to deploy')
@click.option('--environment', '-e', required=True,
              type=click.Choice(['development', 'staging', 'production']),
              help='Target environment')
@click.option('--auto-approve', is_flag=True, help='Skip manual approval')
@click.pass_context
def deploy(ctx, version: str, environment: str, auto_approve: bool):
    """
    Deploys a specified version to a given environment, optionally skipping manual approval.
    
    Parameters:
        version (str): The version identifier to deploy.
        environment (str): The target environment for deployment (e.g., development, staging, production).
        auto_approve (bool): If True, proceeds with deployment without manual approval.
    
    On successful deployment, sends a completion notification. Exits with an error message if deployment fails or an exception occurs.
    """
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
    """
    Defines the CLI group for notification management commands.
    """
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
    """
    Sends a notification message with the specified title, body, and priority to one or more channels.
    
    Parameters:
        title (str): The notification title.
        message (str): The notification body content.
        priority (str): The priority level of the notification (e.g., low, normal, high, urgent).
        channels (list): List of channels to send the notification through (e.g., 'teams', 'email').
    """
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
    """
    Display the current version of the Change Process Automation CLI.
    """
    click.echo("Change Process Automation v1.0.0")

if __name__ == '__main__':
    cli() 