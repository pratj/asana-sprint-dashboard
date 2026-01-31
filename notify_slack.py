#!/usr/bin/env python3
"""
Slack Notification for Asana Daily Report
==========================================
Sends a summary of the daily report to a Slack channel.

Usage:
    python notify_slack.py /path/to/report.json

Environment Variables:
    SLACK_WEBHOOK_URL - Slack incoming webhook URL
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


def load_report(report_path: str) -> dict:
    """Load the JSON report file."""
    with open(report_path) as f:
        return json.load(f)


def format_slack_message(report: dict) -> dict:
    """Format the report as a Slack message with blocks."""
    summary = report.get('summary', {})

    # Build blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📋 Asana Daily Report",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Generated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Tickets Missing Key Details*"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Missing Due Date:*\n{summary.get('missing_due_date', 0)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Missing ACs:*\n{summary.get('missing_acs', 0)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Missing Sprint:*\n{summary.get('missing_sprint', 0)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Missing Epic:*\n{summary.get('missing_epic', 0)}"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Top Assignees with Missing Details:*"
            }
        }
    ]

    # Add assignee list
    by_assignee = summary.get('by_assignee', {})
    assignee_text = ""
    for i, (assignee, count) in enumerate(list(by_assignee.items())[:5], 1):
        assignee_text += f"{i}. *{assignee}*: {count} tasks\n"

    if assignee_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": assignee_text
            }
        })

    # Add action button
    project_url = os.environ.get(
        "ASANA_PROJECT_URL",
        "https://app.asana.com/0/1210472897337973"
    )
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View Asana Project",
                    "emoji": True
                },
                "url": project_url,
                "action_id": "view_asana"
            }
        ]
    })

    return {
        "blocks": blocks,
        "text": f"Asana Daily Report - {summary.get('missing_due_date', 0)} tasks missing due date"
    }


def send_slack_notification(webhook_url: str, message: dict) -> bool:
    """Send a message to Slack via webhook."""
    try:
        data = json.dumps(message).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.URLError as e:
        print(f"Error sending Slack notification: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python notify_slack.py /path/to/report.json")
        sys.exit(1)

    report_path = sys.argv[1]
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')

    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL environment variable not set")
        sys.exit(1)

    if not Path(report_path).exists():
        print(f"Error: Report file not found: {report_path}")
        sys.exit(1)

    print(f"Loading report from: {report_path}")
    report = load_report(report_path)

    print("Formatting Slack message...")
    message = format_slack_message(report)

    print("Sending notification to Slack...")
    if send_slack_notification(webhook_url, message):
        print("✓ Notification sent successfully!")
    else:
        print("✗ Failed to send notification")
        sys.exit(1)


if __name__ == '__main__':
    main()
