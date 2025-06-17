#!/bin/bash

# ServiceNow Change Request Script
# Version: 1.0.0
# Last Updated: [Date]

# Configuration
SN_INSTANCE="your-instance.service-now.com"
SN_USERNAME="your-username"
SN_PASSWORD="your-password"
SN_TABLE="change_request"

# Function to create change request
create_change_request() {
    local title="$1"
    local description="$2"
    local risk_level="$3"
    local implementation_plan="$4"
    local test_plan="$5"
    local rollback_plan="$6"

    # Create change request using ServiceNow REST API
    response=$(curl -s -X POST \
        "https://${SN_INSTANCE}/api/now/table/${SN_TABLE}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -u "${SN_USERNAME}:${SN_PASSWORD}" \
        -d "{
            \"short_description\": \"${title}\",
            \"description\": \"${description}\",
            \"risk\": \"${risk_level}\",
            \"implementation_plan\": \"${implementation_plan}\",
            \"test_plan\": \"${test_plan}\",
            \"rollback_plan\": \"${rollback_plan}\"
        }")

    # Extract change request number from response
    change_number=$(echo "$response" | jq -r '.result.number')
    
    if [ "$change_number" != "null" ]; then
        echo "Change request created successfully: ${change_number}"
        return 0
    else
        echo "Failed to create change request"
        return 1
    fi
}

# Function to update change request status
update_change_status() {
    local change_number="$1"
    local new_status="$2"

    response=$(curl -s -X PUT \
        "https://${SN_INSTANCE}/api/now/table/${SN_TABLE}/${change_number}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -u "${SN_USERNAME}:${SN_PASSWORD}" \
        -d "{
            \"state\": \"${new_status}\"
        }")

    if [ $? -eq 0 ]; then
        echo "Change request ${change_number} updated to ${new_status}"
        return 0
    else
        echo "Failed to update change request status"
        return 1
    fi
}

# Function to get change request details
get_change_details() {
    local change_number="$1"

    response=$(curl -s -X GET \
        "https://${SN_INSTANCE}/api/now/table/${SN_TABLE}?number=${change_number}" \
        -H "Accept: application/json" \
        -u "${SN_USERNAME}:${SN_PASSWORD}")

    echo "$response" | jq '.result[0]'
}

# Example usage
# create_change_request "Deploy Application Update" "Deploying version 1.2.3" "Low" "Implementation steps..." "Test steps..." "Rollback steps..."
# update_change_status "CHG123456" "In Progress"
# get_change_details "CHG123456" 