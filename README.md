# Asana Compliance Report

A Streamlit web application for generating and viewing Asana ticket compliance reports for the Unified Partner Portal team.

## Features

- **Web Interface**: User-friendly UI accessible from any browser
- **Real-time Reports**: Generate compliance reports on demand
- **Multiple Export Formats**: Download as Excel, Markdown, or JSON
- **Compliance Tracking**: Monitor mandatory attributes, daily updates, and team metrics
- **By Assignee**: View compliance breakdown per team member

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   cd scripts
   pip install -r requirements.txt
   ```

2. **Set your Asana token (optional):**
   ```bash
   export ASANA_ACCESS_TOKEN=your_token_here
   ```

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```

4. **Open in browser:** http://localhost:8501

### Using the Web App

1. Enter your Asana Personal Access Token in the sidebar
   - Get a token at: https://app.asana.com/0/developer-console
2. Configure options (optional):
   - Fetch Comments: Enable/disable daily update checks
   - Min Description Length: Set minimum required description characters
   - Hours Without Update: Threshold for flagging stale tasks
3. Click "Generate Report"
4. View metrics, findings, and download reports

## Deployment to Streamlit Cloud

### Prerequisites

- GitHub repository with these files
- Streamlit Cloud account (free at https://share.streamlit.io)

### Deploy Steps

1. **Push to GitHub:**
   ```bash
   git add scripts/app.py scripts/requirements.txt scripts/.streamlit/
   git commit -m "Add Streamlit web app for compliance reports"
   git push
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect your GitHub repository
   - Set:
     - Main file path: `scripts/app.py`
     - Python version: 3.11
   - Click "Deploy"

3. **Add Secrets (Optional):**
   - Go to your app's settings > Secrets
   - Add:
     ```toml
     ASANA_ACCESS_TOKEN = "your_token_here"
     ```
   - This pre-fills the token for all users (useful for team-shared deployments)

### Auto-Updates

Once deployed, Streamlit Cloud automatically rebuilds when you push to GitHub:
```
git push origin main  ->  App rebuilds (~1 min)  ->  Users refresh to get latest
```

## File Structure

```
scripts/
├── app.py                    # Streamlit web app (entry point)
├── asana_daily_report.py     # Core compliance logic
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── config.toml          # Streamlit theme and settings
└── README.md                 # This file
```

## Command Line Usage

The core script can also be run from the command line:

```bash
# Basic markdown report
python asana_daily_report.py

# Excel report
python asana_daily_report.py --format excel

# All formats
python asana_daily_report.py --format all

# Custom output directory
python asana_daily_report.py --output-dir ./my-reports

# Skip comment fetching (faster)
python asana_daily_report.py --no-comments
```

## Compliance Checks

The report checks for:

### Mandatory Attributes
- Epic assignment
- Sprint assignment
- Type classification
- Story Points (Fibonacci: 0, 1, 2, 3, 5, 8, 13)
- Severity level
- Due Date
- Description/ACs (min 100 characters)

### Daily Updates
- Tasks in "In Progress", "Review", or "QA" status
- Flagged if no comment in last 24 hours

### Exclusions
- "Done" tasks: Excluded from report
- "Backlog" tasks: Excluded from compliance checks

## Troubleshooting

### "401 Unauthorized" Error
- Your Asana token is invalid or expired
- Generate a new token at https://app.asana.com/0/developer-console

### Slow Report Generation
- Disable "Fetch Comments" in the sidebar for faster reports
- This skips daily update checks but speeds up API calls

### Excel Download Not Working
- Ensure `openpyxl` is installed: `pip install openpyxl`

## Development

### Adding New Compliance Checks

1. Add new fields to `TaskCompliance` dataclass in `asana_daily_report.py`
2. Update `ComplianceAnalyzer.analyze_task()` method
3. Add display logic in `app.py` render functions

### Customizing Theme

Edit `.streamlit/config.toml` to change colors and appearance.

## License

Internal tool for Source Advisors team use.
