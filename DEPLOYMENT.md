# Deploying to Streamlit Community Cloud

This guide covers deploying the Asana Sprint Dashboard to [Streamlit Community Cloud](https://share.streamlit.io/).

## Prerequisites

1. **GitHub Account** - Your code must be in a GitHub repository
2. **Streamlit Cloud Account** - Sign up at [share.streamlit.io](https://share.streamlit.io/)
3. **Asana Access Token** - Get from [Asana Developer Console](https://app.asana.com/0/my-apps)

## Deployment Steps

### 1. Prepare Your Repository

Ensure your repository has the following structure:

```
asana-sprint-dashboard/
├── app.py                    # Main entry point
├── requirements.txt          # Pinned dependencies
├── asana_daily_report.py     # Core report logic
├── history.py                # Historical data storage
├── notify_slack.py           # Slack notifications
├── .gitignore                # Excludes .env, secrets, etc.
├── .env.example              # Environment variable template
├── DEPLOYMENT.md             # This file
├── README.md                 # Project documentation
└── assets/
    └── Text-Logo_SourceHub.png
```

**Important:** Never commit `.env` or secrets to your repository!

### 2. Push to GitHub

```bash
cd asana-sprint-dashboard
git init
git add .
git commit -m "Initial commit - Asana Sprint Dashboard"
git remote add origin https://github.com/YOUR_USERNAME/asana-sprint-dashboard.git
git push -u origin main
```

### 3. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Click **"New app"**
3. Connect your GitHub repository
4. Configure:
   - **Repository:** `your-username/asana-sprint-dashboard`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **"Deploy"**

### 4. Configure Secrets

After deployment, add your secrets via the Streamlit Cloud UI:

1. Click on your app's **"Settings"** (gear icon)
2. Select **"Secrets"**
3. Add your secrets in TOML format:

```toml
ASANA_ACCESS_TOKEN = "your_asana_token_here"

# Optional: Override default configuration
# ASANA_WORKSPACE_GID = "1198498469382287"
# ASANA_PROJECT_GID = "1210472897337973"
# SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/xxx"
```

4. Click **"Save"**

The app will automatically restart with the new secrets.

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ASANA_ACCESS_TOKEN` | Yes | Asana Personal Access Token |
| `ASANA_WORKSPACE_GID` | No | Asana workspace GID (default: sourceadvisors.com) |
| `ASANA_PROJECT_GID` | No | Asana project GID (default: Unified Partner Portal) |
| `ASANA_PROJECT_URL` | No | Project URL for Slack notifications |
| `ASANA_SPRINT_FIELD_GID` | No | Custom field GID for Sprint |
| `ASANA_PROGRESS_FIELD_GID` | No | Custom field GID for Progress/Status |
| `ASANA_EPIC_FIELD_GID` | No | Custom field GID for Epic |
| `ASANA_TYPE_FIELD_GID` | No | Custom field GID for Type |
| `ASANA_SEVERITY_FIELD_GID` | No | Custom field GID for Severity |
| `ASANA_POINTS_FIELD_GID` | No | Custom field GID for Story Points |
| `SLACK_WEBHOOK_URL` | No | Slack webhook for notifications |

## Verification

After deployment:

1. **Check App Status**
   - Visit your app URL: `https://your-app.streamlit.app`
   - Verify the login page loads

2. **Test Authentication**
   - The app should auto-load your token from secrets
   - You should see "Token auto-loaded" in the sidebar

3. **Generate Report**
   - Click "Generate Report"
   - Verify metrics display correctly
   - Test export buttons (Excel, Markdown, JSON)

4. **Check Logs** (if issues occur)
   - Go to app Settings → "Manage app"
   - Click "Logs" to view application logs

## Resource Limits

Streamlit Community Cloud free tier limits:

| Resource | Limit |
|----------|-------|
| Memory | ~1 GB |
| App sleep | After inactivity |
| GitHub updates | 5 per minute |

If your app exceeds limits, it may slow down or become unresponsive.

## Troubleshooting

### App won't start
- Check `requirements.txt` has all dependencies
- Verify Python version compatibility
- Check logs for import errors

### Authentication errors
- Verify `ASANA_ACCESS_TOKEN` is set in Secrets
- Check token hasn't expired
- Regenerate token if needed

### App is slow
- Enable "Fetch Completed Tasks" only when needed
- Reduce date ranges for analysis
- Consider caching with `@st.cache_data`

### Secrets not loading
- Ensure TOML syntax is correct
- Restart the app after saving secrets
- Check for typos in variable names

## Updating the App

To update your deployed app:

1. Make changes locally
2. Commit and push to GitHub
3. Streamlit Cloud auto-detects changes and redeploys

```bash
git add .
git commit -m "Update dashboard features"
git push origin main
```

## Local Development

For local development, use a `.env` file:

```bash
# Copy example and fill in values
cp .env.example .env

# Edit with your token
nano .env

# Run locally
streamlit run app.py
```

The app runs at `http://localhost:8501` by default.
