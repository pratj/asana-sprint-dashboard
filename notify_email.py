#!/usr/bin/env python3
"""
Stale Task Email Alert Notification
====================================
Sends email alerts for tasks that haven't been updated in 24+ hours.

This script is designed to run as a scheduled job (GitHub Actions, cron, etc.)
to send daily email notifications about stale tasks.

Usage:
    python notify_email.py

Environment Variables:
    ASANA_ACCESS_TOKEN - Your Asana Personal Access Token
    SMTP_HOST - SMTP server hostname
    SMTP_PORT - SMTP server port (default: 587)
    SMTP_USER - SMTP username
    SMTP_PASSWORD - SMTP password
    EMAIL_FROM - Sender email address
    EMAIL_TO - Comma-separated recipient email addresses
    EMAIL_CC - Comma-separated CC email addresses (optional)
    STALE_TASK_HOURS - Hours threshold for stale tasks (default: 24)
"""

import os
import sys
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import the core report logic
from asana_daily_report import (
    Config,
    AsanaComplianceReporter,
    TaskCompliance,
)


# =============================================================================
# Configuration
# =============================================================================

def get_config() -> dict:
    """Get email configuration from environment variables."""
    return {
        "smtp_host": os.environ.get("SMTP_HOST", "smtp.conseroglobal.com"),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "smtp_user": os.environ.get("SMTP_USER", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "email_from": os.environ.get("EMAIL_FROM", ""),
        "email_to": os.environ.get("EMAIL_TO", "").split(","),
        "email_cc": [e.strip() for e in os.environ.get("EMAIL_CC", "").split(",") if e.strip()],
        "stale_hours": int(os.environ.get("STALE_TASK_HOURS", "24")),
    }


# =============================================================================
# Stale Task Detection
# =============================================================================

def get_stale_tasks(
    reporter: AsanaComplianceReporter,
    hours_threshold: int = 24
) -> list[TaskCompliance]:
    """
    Fetch incomplete tasks that haven't been updated in the specified hours.

    Stale Task Criteria:
    - NOT completed (progress != "Done")
    - NOT in Backlog
    - hours_since_update >= threshold OR no recent activity tracked
    """
    # Fetch active tasks
    print(f"Fetching active tasks from Asana...")
    tasks = reporter.client.get_tasks(completed=False)
    print(f"Found {len(tasks)} active tasks")

    # Analyze tasks (with comments to get update times)
    print("Analyzing task compliance (fetching comments)...")
    results = reporter.analyzer.analyze_all(
        tasks,
        fetch_comments=True
    )

    # Filter for stale tasks
    stale_tasks = []
    for task in results:
        # Skip backlog and done tasks
        if task.progress in ("Backlog", "Done"):
            continue

        # Check if stale based on hours_since_update
        if task.hours_since_update is not None:
            if task.hours_since_update >= hours_threshold:
                stale_tasks.append(task)
        else:
            # No update tracking available - consider stale if in active status
            if task.progress in ("In Progress", "Review", "QA"):
                stale_tasks.append(task)

    # Sort by hours since update (most stale first)
    stale_tasks.sort(
        key=lambda t: t.hours_since_update if t.hours_since_update is not None else 9999,
        reverse=True
    )

    return stale_tasks


# =============================================================================
# Email Formatting
# =============================================================================

def format_email_html(stale_tasks: list[TaskCompliance], hours_threshold: int) -> str:
    """Format stale tasks as HTML email content grouped by assignee."""

    # Group tasks by assignee
    tasks_by_assignee: dict[str, list[TaskCompliance]] = {}
    for task in stale_tasks:
        assignee = task.assignee or "Unassigned"
        if assignee not in tasks_by_assignee:
            tasks_by_assignee[assignee] = []
        tasks_by_assignee[assignee].append(task)

    # Sort assignees by task count (most tasks first)
    sorted_assignees = sorted(
        tasks_by_assignee.keys(),
        key=lambda a: len(tasks_by_assignee[a]),
        reverse=True
    )

    # Build HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #2D3748;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #6B7FD7 0%, #5B9A8B 100%);
            color: white;
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 24px;
        }}
        .header p {{
            margin: 0;
            opacity: 0.9;
        }}
        .summary {{
            background: #F7FAFC;
            border-left: 4px solid #C9736D;
            padding: 16px;
            margin-bottom: 24px;
            border-radius: 0 8px 8px 0;
        }}
        .assignee-section {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            margin-bottom: 16px;
            overflow: hidden;
        }}
        .assignee-header {{
            background: #EDF2F7;
            padding: 12px 16px;
            font-weight: 600;
            border-bottom: 1px solid #E2E8F0;
        }}
        .task-list {{
            padding: 0;
            margin: 0;
            list-style: none;
        }}
        .task-item {{
            padding: 12px 16px;
            border-bottom: 1px solid #E2E8F0;
        }}
        .task-item:last-child {{
            border-bottom: none;
        }}
        .task-name {{
            font-weight: 500;
            color: #2D3748;
            text-decoration: none;
        }}
        .task-name:hover {{
            color: #6B7FD7;
        }}
        .task-meta {{
            font-size: 12px;
            color: #718096;
            margin-top: 4px;
        }}
        .stale-badge {{
            display: inline-block;
            background: #FED7D7;
            color: #C53030;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            margin-left: 8px;
        }}
        .footer {{
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid #E2E8F0;
            font-size: 12px;
            color: #718096;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Stale Task Alert</h1>
        <p>{len(stale_tasks)} tasks haven't been updated in {hours_threshold}+ hours</p>
    </div>

    <div class="summary">
        <strong>Action Required:</strong> The following tasks need attention.
        Please update their status or add a comment to reflect current progress.
    </div>
"""

    for assignee in sorted_assignees:
        tasks = tasks_by_assignee[assignee]
        html += f"""
    <div class="assignee-section">
        <div class="assignee-header">{assignee} ({len(tasks)} tasks)</div>
        <ul class="task-list">
"""
        for task in tasks:
            hours = f"{task.hours_since_update:.0f}h" if task.hours_since_update else "N/A"
            html += f"""
            <li class="task-item">
                <a href="{task.url}" class="task-name" target="_blank">{task.name}</a>
                <span class="stale-badge">{hours} since update</span>
                <div class="task-meta">
                    Status: {task.progress or 'Unknown'} |
                    Sprint: {task.sprint or 'Not set'} |
                    Points: {task.story_points or 'Not set'}
                </div>
            </li>
"""
        html += """
        </ul>
    </div>
"""

    html += f"""
    <div class="footer">
        <p>Generated by SourceHub Sprint Dashboard</p>
        <p>Report time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
</body>
</html>
"""
    return html


def format_email_plain(stale_tasks: list[TaskCompliance], hours_threshold: int) -> str:
    """Format stale tasks as plain text email content."""

    # Group tasks by assignee
    tasks_by_assignee: dict[str, list[TaskCompliance]] = {}
    for task in stale_tasks:
        assignee = task.assignee or "Unassigned"
        if assignee not in tasks_by_assignee:
            tasks_by_assignee[assignee] = []
        tasks_by_assignee[assignee].append(task)

    # Sort assignees by task count
    sorted_assignees = sorted(
        tasks_by_assignee.keys(),
        key=lambda a: len(tasks_by_assignee[a]),
        reverse=True
    )

    # Build plain text
    lines = [
        "=" * 60,
        "STALE TASK ALERT",
        "=" * 60,
        "",
        f"{len(stale_tasks)} tasks haven't been updated in {hours_threshold}+ hours",
        "",
        "ACTION REQUIRED: Please update task status or add a comment.",
        "",
        "-" * 60,
        "",
    ]

    for assignee in sorted_assignees:
        tasks = tasks_by_assignee[assignee]
        lines.append(f"{assignee} ({len(tasks)} tasks)")
        lines.append("-" * 40)

        for task in tasks:
            hours = f"{task.hours_since_update:.0f}h" if task.hours_since_update else "N/A"
            lines.append(f"  * {task.name}")
            lines.append(f"    {task.url}")
            lines.append(f"    Status: {task.progress or 'Unknown'} | Stale: {hours}")
            lines.append("")

        lines.append("")

    lines.extend([
        "-" * 60,
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "SourceHub Sprint Dashboard",
    ])

    return "\n".join(lines)


# =============================================================================
# Email Sending
# =============================================================================

def send_email(
    config: dict,
    subject: str,
    html_content: str,
    plain_content: str
) -> bool:
    """Send email via SMTP."""

    # Validate configuration
    if not config["smtp_user"] or not config["smtp_password"]:
        print("ERROR: SMTP credentials not configured")
        return False

    if not config["email_from"]:
        print("ERROR: EMAIL_FROM not configured")
        return False

    recipients = [e.strip() for e in config["email_to"] if e.strip()]
    if not recipients:
        print("ERROR: EMAIL_TO not configured")
        return False

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["email_from"]
    msg["To"] = ", ".join(recipients)

    if config["email_cc"]:
        msg["Cc"] = ", ".join(config["email_cc"])

    # Attach plain text and HTML versions
    part1 = MIMEText(plain_content, "plain")
    part2 = MIMEText(html_content, "html")
    msg.attach(part1)
    msg.attach(part2)

    # All recipients (To + Cc)
    all_recipients = recipients + config["email_cc"]

    try:
        print(f"Connecting to SMTP server {config['smtp_host']}:{config['smtp_port']}...")

        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()

            print(f"Authenticating as {config['smtp_user']}...")
            server.login(config["smtp_user"], config["smtp_password"])

            print(f"Sending email to {', '.join(all_recipients)}...")
            server.sendmail(config["email_from"], all_recipients, msg.as_string())

        print("Email sent successfully!")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"ERROR: SMTP authentication failed: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"ERROR: SMTP error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")
        return False


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point for stale task notification."""
    print("=" * 60)
    print("Stale Task Email Alert")
    print("=" * 60)
    print()

    # Get configuration
    email_config = get_config()
    hours_threshold = email_config["stale_hours"]

    print(f"Stale threshold: {hours_threshold} hours")
    print()

    # Check for Asana token
    asana_token = os.environ.get("ASANA_ACCESS_TOKEN")
    if not asana_token:
        print("ERROR: ASANA_ACCESS_TOKEN not set")
        sys.exit(1)

    # Initialize reporter
    config = Config(hours_without_update=hours_threshold)
    reporter = AsanaComplianceReporter(asana_token, config)

    # Get stale tasks
    stale_tasks = get_stale_tasks(reporter, hours_threshold)

    print()
    print(f"Found {len(stale_tasks)} stale tasks")

    if not stale_tasks:
        print("No stale tasks found. Skipping email notification.")
        sys.exit(0)

    # Format email content
    subject = f"[Sprint Dashboard] {len(stale_tasks)} Stale Tasks - {datetime.now().strftime('%Y-%m-%d')}"
    html_content = format_email_html(stale_tasks, hours_threshold)
    plain_content = format_email_plain(stale_tasks, hours_threshold)

    # Send email
    print()
    success = send_email(email_config, subject, html_content, plain_content)

    if success:
        print()
        print("Notification complete!")
        sys.exit(0)
    else:
        print()
        print("Failed to send notification email")
        sys.exit(1)


if __name__ == "__main__":
    main()
