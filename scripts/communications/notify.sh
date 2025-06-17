#!/bin/bash

# Communication Script for MS Teams and Outlook
# Version: 1.0.0
# Last Updated: [Date]

# Configuration
TEAMS_WEBHOOK_URL="your-teams-webhook-url"
OUTLOOK_SMTP_SERVER="smtp.office365.com"
OUTLOOK_SMTP_PORT="587"
OUTLOOK_USERNAME="your-email@domain.com"
OUTLOOK_PASSWORD="your-password"

# Function to send MS Teams notification
send_teams_notification() {
    local title="$1"
    local message="$2"
    local status="$3"  # success, warning, error

    # Set color based on status
    case "$status" in
        "success") color="#00FF00" ;;
        "warning") color="#FFA500" ;;
        "error") color="#FF0000" ;;
        *) color="#808080" ;;
    esac

    # Create Teams message card
    json_payload=$(cat <<EOF
{
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "themeColor": "${color}",
    "summary": "${title}",
    "sections": [{
        "activityTitle": "${title}",
        "text": "${message}"
    }]
}
EOF
)

    # Send to Teams
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "${json_payload}" \
        "${TEAMS_WEBHOOK_URL}"
}

# Function to send Outlook email
send_outlook_email() {
    local to="$1"
    local subject="$2"
    local body="$3"
    local importance="$4"  # high, normal, low

    # Create email content
    email_content=$(cat <<EOF
From: ${OUTLOOK_USERNAME}
To: ${to}
Subject: ${subject}
Importance: ${importance}
Content-Type: text/html

${body}
EOF
)

    # Send email using curl and SMTP
    echo "${email_content}" | curl -s \
        --url "smtp://${OUTLOOK_SMTP_SERVER}:${OUTLOOK_SMTP_PORT}" \
        --mail-from "${OUTLOOK_USERNAME}" \
        --mail-rcpt "${to}" \
        --ssl-reqd \
        --user "${OUTLOOK_USERNAME}:${OUTLOOK_PASSWORD}" \
        --upload-file -
}

# Function to send change notification
send_change_notification() {
    local change_number="$1"
    local status="$2"
    local details="$3"
    local recipients="$4"

    # Create Teams message
    teams_title="Change Request ${change_number} - ${status}"
    teams_message="Status: ${status}\nDetails: ${details}"
    send_teams_notification "$teams_title" "$teams_message" "$status"

    # Create and send email
    email_subject="Change Request ${change_number} - ${status}"
    email_body="<h2>Change Request Update</h2>
                <p><strong>Change Number:</strong> ${change_number}</p>
                <p><strong>Status:</strong> ${status}</p>
                <p><strong>Details:</strong> ${details}</p>"
    
    # Send to each recipient
    IFS=',' read -ra RECIPIENT_LIST <<< "$recipients"
    for recipient in "${RECIPIENT_LIST[@]}"; do
        send_outlook_email "$recipient" "$email_subject" "$email_body" "high"
    done
}

# Example usage
# send_change_notification "CHG123456" "In Progress" "Deployment started" "team1@domain.com,team2@domain.com"
# send_teams_notification "Deployment Complete" "Successfully deployed version 1.2.3" "success"
# send_outlook_email "team@domain.com" "Deployment Notification" "Deployment completed successfully" "normal" 