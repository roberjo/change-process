# Harness Pipeline Integration

This document describes the Harness pipeline configuration and integration with the change management process.

## Overview

The Harness pipeline integration provides a standardized approach to CI/CD automation, with built-in support for change management and deployment validation. The pipeline is designed to work seamlessly with ServiceNow for change tracking and approval workflows.

## Pipeline Structure

The pipeline consists of the following stages:

1. **Test Stage**
   - Build and test application
   - Run automated tests
   - Generate test reports
   - Validate test coverage

2. **Production Stage**
   - Production readiness checks
   - Change request validation
   - Deployment execution
   - Post-deployment validation

## Configuration

### Pipeline Template

The pipeline template is located at `templates/harness-pipeline-template.yaml`:

```yaml
pipeline:
  name: Change Management Pipeline
  identifier: change_management_pipeline
  projectIdentifier: your_project
  orgIdentifier: your_org
  tags: {}
  stages:
    - stage:
        name: Test
        identifier: Test
        type: CI
        spec:
          cloneCodebase: true
          execution:
            steps:
              - step:
                  type: Run
                  name: Build and Test
                  identifier: Build_and_Test
                  spec:
                    shell: Sh
                    command: |
                      # Build application
                      ./gradlew build
                      
                      # Run tests
                      ./gradlew test
                      
                      # Generate reports
                      ./gradlew jacocoTestReport
                      
                      # Validate coverage
                      ./gradlew checkCoverage
                      
    - stage:
        name: Production
        identifier: Production
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            serviceRef: your_service
          environment:
            environmentRef: Production
            deployToAll: false
            infrastructureDefinitions:
              - identifier: your_infra
          execution:
            steps:
              - step:
                  type: ShellScript
                  name: Production Readiness
                  identifier: Production_Readiness
                  spec:
                    shell: Bash
                    command: |
                      # Check production readiness
                      ./scripts/check_production_readiness.sh
                      
              - step:
                  type: ShellScript
                  name: Deploy
                  identifier: Deploy
                  spec:
                    shell: Bash
                    command: |
                      # Deploy application
                      ./scripts/deploy.sh
                      
              - step:
                  type: ShellScript
                  name: Validate
                  identifier: Validate
                  spec:
                    shell: Bash
                    command: |
                      # Validate deployment
                      ./scripts/validate_deployment.sh
```

### Environment Variables

Configure the following environment variables:

```bash
# Harness API
HARNESS_API_KEY=your-api-key
HARNESS_ACCOUNT_ID=your-account-id

# ServiceNow Integration
SN_INSTANCE=your-instance.service-now.com
SN_CLIENT_ID=your-client-id
SN_CLIENT_SECRET=your-client-secret
SN_USERNAME=your-username
SN_PASSWORD=your-password

# Deployment Configuration
DEPLOYMENT_ENVIRONMENT=production
DEPLOYMENT_VERSION=1.0.0
```

## Integration with Change Management

### Change Request Creation

The pipeline automatically creates a change request in ServiceNow when triggered:

```python
# Create change request
change = sn.create_scheduled_change(
    title=f"Deploy version {DEPLOYMENT_VERSION}",
    description="Automated deployment via Harness",
    risk_level="Low",
    implementation_plan="Deployment steps",
    test_plan="Validation steps",
    rollback_plan="Rollback steps",
    start_date=deployment_start,
    end_date=deployment_end
)
```

### Approval Workflow

The pipeline integrates with ServiceNow's approval workflow:

1. Create change request
2. Wait for approval
3. Execute deployment
4. Update change status
5. Validate deployment
6. Close change request

### Status Updates

The pipeline updates the change request status throughout the deployment:

```python
# Update status to implementing
sn.update_change_status(change_number, 'Implement')

# Update status to review
sn.update_change_status(change_number, 'Review')

# Update status to closed
sn.update_change_status(change_number, 'Closed')
```

## Validation Steps

### Production Readiness

The pipeline includes comprehensive production readiness checks:

1. Environment validation
2. Configuration verification
3. Resource availability
4. Security compliance
5. Performance baseline

### Deployment Validation

Post-deployment validation includes:

1. Application health checks
2. Functionality verification
3. Performance monitoring
4. Error rate analysis
5. Log validation

## Error Handling

The pipeline includes comprehensive error handling:

1. **Validation Errors**
   - Input validation
   - Environment checks
   - Resource verification

2. **Deployment Errors**
   - Rollback procedures
   - Error logging
   - Status updates

3. **Integration Errors**
   - API error handling
   - Retry logic
   - Fallback procedures

## Logging and Monitoring

### Pipeline Logs

Logs are available in the Harness UI and include:
- Stage execution details
- Step outputs
- Error messages
- Performance metrics

### Integration Logs

Integration logs are stored in:
- `servicenow_change.log`
- `deployment.log`
- `validation.log`

## Security

The pipeline implements several security measures:

1. **Authentication**
   - API key authentication
   - OAuth2 for ServiceNow
   - Secure credential storage

2. **Authorization**
   - Role-based access control
   - Environment-specific permissions
   - Approval workflows

3. **Data Protection**
   - Encrypted credentials
   - Secure communication
   - Audit logging

## Best Practices

1. **Pipeline Design**
   - Modular stages
   - Reusable components
   - Clear documentation

2. **Change Management**
   - Automated change requests
   - Approval workflows
   - Status tracking

3. **Deployment**
   - Zero-downtime deployments
   - Rollback procedures
   - Validation steps

4. **Monitoring**
   - Comprehensive logging
   - Performance metrics
   - Error tracking

## Troubleshooting

Common issues and solutions:

1. **Pipeline Failures**
   - Check logs
   - Verify configurations
   - Validate permissions

2. **Integration Issues**
   - Verify API connectivity
   - Check credentials
   - Validate endpoints

3. **Deployment Problems**
   - Review deployment logs
   - Check resource availability
   - Verify configurations

## Support

For issues and support:
1. Check the Harness documentation
2. Review pipeline logs
3. Consult the integration logs
4. Contact the development team 