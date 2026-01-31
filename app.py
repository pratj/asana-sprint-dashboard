"""
Streamlit Web App for Asana Sprint Dashboard
==============================================
A focused dashboard for sprint compliance and burndown tracking.

Run locally:
    cd scripts && streamlit run app.py
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st
import pandas as pd

# Import Plotly for interactive charts
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Import the core report logic
from asana_daily_report import (
    Config,
    AsanaComplianceReporter,
    TaskCompliance,
    ReportSummary,
    MarkdownReportGenerator,
    JSONReportGenerator,
    OPENPYXL_AVAILABLE,
)

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="SourceHub - Sprint Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Neumorphism Design System CSS
st.markdown("""
<style>
    /* =================================================================
       DESIGN TOKENS - Neumorphism (Soft UI) System
       ================================================================= */
    :root {
        /* Base Colors */
        --nm-bg: #E4E8EC;
        --nm-surface: #E4E8EC;
        --nm-shadow-dark: #A3B1C6;
        --nm-shadow-light: #FFFFFF;

        /* Semantic Accents (Muted) */
        --nm-primary: #6B7FD7;
        --nm-success: #5B9A8B;
        --nm-warning: #D4A574;
        --nm-error: #C9736D;
        --nm-info: #5A9AA8;

        /* Text Colors */
        --nm-text-primary: #2D3748;
        --nm-text-secondary: #5A6778;
        --nm-text-muted: #8896A4;

        /* Shadow Patterns */
        --nm-shadow-raised: 6px 6px 12px #A3B1C6, -6px -6px 12px #FFFFFF;
        --nm-shadow-inset: inset 3px 3px 6px #A3B1C6, inset -3px -3px 6px #FFFFFF;
        --nm-shadow-pressed: inset 2px 2px 5px #A3B1C6, inset -2px -2px 5px #FFFFFF;
        --nm-shadow-hover: 10px 10px 20px #A3B1C6, -10px -10px 20px #FFFFFF;
    }

    /* =================================================================
       GLOBAL STYLES
       ================================================================= */
    .stApp {
        background: var(--nm-bg) !important;
    }

    [data-testid="stSidebar"] {
        background: #D8DCE2 !important;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdown"] {
        color: var(--nm-text-primary);
    }

    /* =================================================================
       METRIC CARDS - Neumorphic Style
       ================================================================= */
    .nm-card {
        background: var(--nm-bg);
        border-radius: 16px;
        padding: 24px 20px 20px 20px;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: var(--nm-shadow-raised);
        position: relative;
        overflow: hidden;
        transition: box-shadow 0.25s ease;
    }

    .nm-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--nm-primary);
        border-radius: 16px 16px 0 0;
    }

    .nm-card:hover {
        box-shadow: var(--nm-shadow-hover);
    }

    .nm-card--success::before { background: var(--nm-success); }
    .nm-card--warning::before { background: var(--nm-error); }
    .nm-card--info::before { background: var(--nm-info); }

    .nm-card-value {
        font-size: 2.25rem;
        font-weight: 700;
        color: var(--nm-text-primary);
        margin: 0;
        line-height: 1.2;
    }

    .nm-card-label {
        font-size: 0.9rem;
        color: var(--nm-text-secondary);
        margin-top: 8px;
        font-weight: 500;
    }

    /* =================================================================
       ALERT SECTIONS - Neumorphic Style with Colored Backgrounds
       ================================================================= */
    .nm-alert {
        background: var(--nm-bg);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--nm-shadow-raised);
        border-left: 5px solid var(--nm-info);
        position: relative;
        overflow: hidden;
    }

    /* Critical/Error Alert - Soft rose/coral tint */
    .nm-alert--error {
        background: linear-gradient(135deg, #F0E4E4 0%, #E8DCDC 100%);
        border-left-color: var(--nm-error);
        box-shadow:
            6px 6px 12px rgba(163, 145, 145, 0.5),
            -6px -6px 12px rgba(255, 255, 255, 0.8),
            inset 0 1px 0 rgba(255, 255, 255, 0.6);
    }

    .nm-alert--error::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle at top right, rgba(201, 115, 109, 0.15), transparent 70%);
        pointer-events: none;
    }

    .nm-alert--error h3 {
        color: #8B4C47;
    }

    .nm-alert--error p {
        color: #6B5A58;
    }

    /* Warning/Amber Alert - Soft warm amber tint */
    .nm-alert--warning {
        background: linear-gradient(135deg, #F2EBE0 0%, #EAE2D6 100%);
        border-left-color: var(--nm-warning);
        box-shadow:
            6px 6px 12px rgba(163, 155, 140, 0.5),
            -6px -6px 12px rgba(255, 255, 255, 0.8),
            inset 0 1px 0 rgba(255, 255, 255, 0.6);
    }

    .nm-alert--warning::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle at top right, rgba(212, 165, 116, 0.15), transparent 70%);
        pointer-events: none;
    }

    .nm-alert--warning h3 {
        color: #7A6340;
    }

    .nm-alert--warning p {
        color: #6B6055;
    }

    .nm-alert h3 {
        color: var(--nm-text-primary);
        margin: 0 0 0.5rem 0;
        font-weight: 600;
        font-size: 1.1rem;
    }

    .nm-alert p {
        color: var(--nm-text-secondary);
        margin: 0 0 1rem 0;
        font-size: 0.9rem;
    }

    /* =================================================================
       COMPLIANCE DETAILS SECTION - Soft blue/purple tint
       ================================================================= */
    .nm-section-compliance {
        background: linear-gradient(135deg, #E4E8F0 0%, #DCE2EC 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow:
            6px 6px 12px rgba(140, 155, 180, 0.4),
            -6px -6px 12px rgba(255, 255, 255, 0.8),
            inset 0 1px 0 rgba(255, 255, 255, 0.6);
        border-left: 5px solid var(--nm-primary);
        position: relative;
        overflow: hidden;
    }

    .nm-section-compliance::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 120px;
        height: 120px;
        background: radial-gradient(circle at top right, rgba(107, 127, 215, 0.12), transparent 70%);
        pointer-events: none;
    }

    .nm-section-compliance h3 {
        color: #4A5580;
        margin: 0 0 0.5rem 0;
        font-weight: 600;
        font-size: 1.1rem;
    }

    .nm-section-compliance p {
        color: #5A6778;
        margin: 0;
        font-size: 0.9rem;
    }

    /* =================================================================
       BUTTONS - Neumorphic Style
       ================================================================= */
    .stButton > button {
        background: var(--nm-bg) !important;
        border: none !important;
        border-radius: 10px !important;
        box-shadow: var(--nm-shadow-raised) !important;
        color: var(--nm-text-primary) !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }

    .stButton > button:hover {
        box-shadow: var(--nm-shadow-hover) !important;
        color: var(--nm-primary) !important;
    }

    .stButton > button:active {
        box-shadow: var(--nm-shadow-pressed) !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--nm-bg) !important;
        color: var(--nm-primary) !important;
    }

    .stButton > button[kind="primary"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--nm-primary);
        border-radius: 10px 10px 0 0;
    }

    /* =================================================================
       INPUTS - Neumorphic Inset Style
       ================================================================= */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stNumberInput > div > div > input {
        background: var(--nm-bg) !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: var(--nm-shadow-inset) !important;
        color: var(--nm-text-primary) !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        box-shadow: var(--nm-shadow-inset), 0 0 0 3px rgba(107, 127, 215, 0.3) !important;
    }

    /* Dropdown/Select cursor pointer */
    .stSelectbox > div > div,
    .stSelectbox [data-baseweb="select"],
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect > div > div,
    .stMultiSelect [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"] > div {
        cursor: pointer !important;
    }

    /* =================================================================
       EXPANDERS - Clean borderless style
       ================================================================= */
    div[data-testid="stExpander"] {
        background: var(--nm-bg) !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: none !important;
        overflow: hidden;
    }

    div[data-testid="stExpander"] > details {
        border: none !important;
    }

    div[data-testid="stExpander"] > details > summary {
        background: transparent !important;
        color: var(--nm-text-primary) !important;
        font-weight: 500;
        border: none !important;
    }

    div[data-testid="stExpander"] > details[open] > summary {
        border: none !important;
        border-bottom: none !important;
    }

    /* Remove any outline/border on expander focus */
    div[data-testid="stExpander"] *:focus {
        outline: none !important;
        box-shadow: none !important;
    }

    /* =================================================================
       SEVERITY-COLORED EXPANDER WRAPPERS
       ================================================================= */

    /* Critical/Red severity - soft coral/rose */
    .nm-expander-red {
        background: linear-gradient(135deg, #F0E4E4 0%, #E8DCDC 100%);
        border-radius: 14px;
        padding: 4px;
        margin-bottom: 12px;
        box-shadow:
            5px 5px 10px rgba(163, 145, 145, 0.4),
            -5px -5px 10px rgba(255, 255, 255, 0.7),
            inset 0 1px 0 rgba(255, 255, 255, 0.5);
        border-left: 4px solid var(--nm-error);
    }

    .nm-expander-red div[data-testid="stExpander"] {
        background: transparent !important;
    }

    .nm-expander-red div[data-testid="stExpander"] > details > summary {
        color: #8B4C47 !important;
    }

    /* Warning/Orange severity - soft peach/orange */
    .nm-expander-orange {
        background: linear-gradient(135deg, #F5EBE0 0%, #EDE3D6 100%);
        border-radius: 14px;
        padding: 4px;
        margin-bottom: 12px;
        box-shadow:
            5px 5px 10px rgba(170, 155, 140, 0.4),
            -5px -5px 10px rgba(255, 255, 255, 0.7),
            inset 0 1px 0 rgba(255, 255, 255, 0.5);
        border-left: 4px solid #D4885C;
    }

    .nm-expander-orange div[data-testid="stExpander"] {
        background: transparent !important;
    }

    .nm-expander-orange div[data-testid="stExpander"] > details > summary {
        color: #8B5A3C !important;
    }

    /* Caution/Yellow severity - soft cream/yellow */
    .nm-expander-yellow {
        background: linear-gradient(135deg, #F5F0E0 0%, #EDE8D4 100%);
        border-radius: 14px;
        padding: 4px;
        margin-bottom: 12px;
        box-shadow:
            5px 5px 10px rgba(170, 165, 140, 0.4),
            -5px -5px 10px rgba(255, 255, 255, 0.7),
            inset 0 1px 0 rgba(255, 255, 255, 0.5);
        border-left: 4px solid #C9A84C;
    }

    .nm-expander-yellow div[data-testid="stExpander"] {
        background: transparent !important;
    }

    .nm-expander-yellow div[data-testid="stExpander"] > details > summary {
        color: #7A6830 !important;
    }

    /* =================================================================
       DATA ROWS - Neumorphic Style
       ================================================================= */
    .nm-data-row {
        background: var(--nm-bg);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: var(--nm-shadow-raised);
        transition: box-shadow 0.25s ease;
    }

    .nm-data-row:hover {
        box-shadow: var(--nm-shadow-hover);
    }

    /* =================================================================
       SIDEBAR SECTIONS
       ================================================================= */
    .nm-sidebar-section {
        background: var(--nm-bg);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: var(--nm-shadow-raised);
    }

    /* =================================================================
       LOADING & UTILITY STYLES
       ================================================================= */
    .loading-text {
        font-size: 1.1rem;
        color: var(--nm-primary);
        padding: 1rem;
    }

    /* Status indicators */
    [data-testid="stStatus"] {
        background: var(--nm-bg) !important;
        border-radius: 12px !important;
        box-shadow: var(--nm-shadow-raised) !important;
        border: none !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: var(--nm-bg);
        border-radius: 12px;
        padding: 16px;
        box-shadow: var(--nm-shadow-raised);
    }

    [data-testid="stMetric"] label {
        color: var(--nm-text-secondary) !important;
    }

    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--nm-text-primary) !important;
    }

    /* Dividers */
    hr {
        border-color: rgba(163, 177, 198, 0.3) !important;
    }

    /* Links */
    a {
        color: var(--nm-primary) !important;
    }

    a:hover {
        color: var(--nm-info) !important;
    }

    /* Captions */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--nm-text-muted) !important;
    }

    /* Headers */
    h1, h2, h3 {
        color: var(--nm-text-primary) !important;
    }

    /* Dialogs/Modals */
    [data-testid="stModal"] > div {
        background: var(--nm-bg) !important;
        border-radius: 16px !important;
        box-shadow: 12px 12px 24px #A3B1C6, -12px -12px 24px #FFFFFF !important;
    }

    /* Download buttons */
    .stDownloadButton > button {
        background: var(--nm-bg) !important;
        border: none !important;
        border-radius: 10px !important;
        box-shadow: var(--nm-shadow-raised) !important;
        color: var(--nm-text-primary) !important;
    }

    .stDownloadButton > button:hover {
        box-shadow: var(--nm-shadow-hover) !important;
        color: var(--nm-primary) !important;
    }

    /* Checkbox and Radio */
    .stCheckbox > label > span,
    .stRadio > label > span {
        color: var(--nm-text-primary) !important;
    }

    /* Info/Warning/Error boxes */
    .stAlert {
        background: var(--nm-bg) !important;
        border-radius: 12px !important;
        box-shadow: var(--nm-shadow-raised) !important;
        border-left: 4px solid var(--nm-info) !important;
    }

    /* Text area */
    .stTextArea > div > div > textarea {
        background: var(--nm-bg) !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: var(--nm-shadow-inset) !important;
        color: var(--nm-text-primary) !important;
    }

    /* Dataframe - remove outer border, keep internal grid */
    [data-testid="stDataFrame"] {
        background: var(--nm-bg) !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        border: none !important;
        overflow: visible;
    }

    [data-testid="stDataFrame"] > div {
        border: none !important;
        box-shadow: none !important;
    }

    /* Remove outer border from table container */
    [data-testid="stDataFrame"] iframe {
        border: none !important;
    }

    /* Style the table inside dataframe */
    [data-testid="stDataFrame"] table {
        border-collapse: collapse !important;
        border: none !important;
    }

    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td {
        border-left: none !important;
        border-right: none !important;
        border-top: 1px solid rgba(163, 177, 198, 0.3) !important;
        border-bottom: 1px solid rgba(163, 177, 198, 0.3) !important;
    }

    [data-testid="stDataFrame"] tr:first-child th,
    [data-testid="stDataFrame"] tr:first-child td {
        border-top: none !important;
    }

    [data-testid="stDataFrame"] tr:last-child th,
    [data-testid="stDataFrame"] tr:last-child td {
        border-bottom: none !important;
    }

    /* Accessibility - Focus states */
    *:focus-visible {
        outline: 3px solid var(--nm-primary) !important;
        outline-offset: 2px;
    }

    /* Reduced motion preference */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            transition: none !important;
            animation: none !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Session State
# =============================================================================

def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "results": None,
        "completed_results": None,
        "summary": None,
        "config": None,
        "reporter": None,
        "report_generated": False,
        "is_generating": False,
        "selected_task_gid": None,
        "selected_task_url": None,
        "selected_task_name": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =============================================================================
# Sidebar
# =============================================================================

def render_sidebar():
    """Render sidebar with configuration."""
    st.sidebar.title("Configuration")

    # Token input
    st.sidebar.subheader("Authentication")

    default_token = ""
    try:
        if "ASANA_ACCESS_TOKEN" in st.secrets:
            default_token = st.secrets["ASANA_ACCESS_TOKEN"]
    except FileNotFoundError:
        pass

    if not default_token and os.environ.get("ASANA_ACCESS_TOKEN"):
        default_token = os.environ.get("ASANA_ACCESS_TOKEN", "")

    if default_token:
        st.sidebar.info("Token auto-loaded")

    token = st.sidebar.text_input(
        "Asana Access Token",
        value=default_token,
        type="password",
        help="Your Asana Personal Access Token"
    )

    st.sidebar.subheader("Options")

    fetch_comments = st.sidebar.checkbox(
        "Fetch Comments",
        value=True,
        help="Check for daily updates (slower but more accurate)"
    )

    fetch_completed = st.sidebar.checkbox(
        "Fetch Completed Tasks",
        value=True,
        help="Include completed tasks for burndown calculation"
    )

    min_description_length = st.sidebar.number_input(
        "Min Description Length",
        min_value=50,
        max_value=500,
        value=100,
        step=25,
    )

    hours_without_update = st.sidebar.number_input(
        "Hours Without Update",
        min_value=12,
        max_value=72,
        value=24,
        step=6,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "[Get Asana Token](https://app.asana.com/0/developer-console)"
    )

    return {
        "token": token,
        "fetch_comments": fetch_comments,
        "fetch_completed": fetch_completed,
        "min_description_length": min_description_length,
        "hours_without_update": hours_without_update,
    }


def render_dashboard_filters(results: list[TaskCompliance], analyzer) -> dict:
    """Render filter controls on the dashboard (horizontal layout)."""
    st.subheader("Filters")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        # Sprint filter
        sprints = analyzer.get_unique_sprints(results)
        selected_sprint = st.selectbox(
            "Sprint",
            ["All"] + sprints,
            index=len(sprints) if sprints else 0,
            help="Filter by sprint",
            key="filter_sprint"
        )

    with col2:
        # Assignee filter
        assignees = analyzer.get_unique_assignees(results)
        selected_assignees = st.multiselect(
            "Assignees",
            assignees,
            default=[],
            help="Filter by assignee (empty = all)",
            key="filter_assignees"
        )

    with col3:
        # Status filter
        statuses = analyzer.get_unique_statuses(results)
        selected_statuses = st.multiselect(
            "Status",
            statuses,
            default=[],
            help="Filter by status (empty = all)",
            key="filter_statuses"
        )

    with col4:
        st.write("")  # Spacing
        st.write("")  # Align with other fields
        if st.button("Refresh Data", type="secondary", use_container_width=True):
            st.session_state["report_generated"] = False
            st.rerun()

    return {
        "sprint": selected_sprint if selected_sprint != "All" else None,
        "assignees": selected_assignees if selected_assignees else None,
        "statuses": selected_statuses if selected_statuses else None,
    }


# =============================================================================
# Metric Cards
# =============================================================================

def render_metric_cards(summary: ReportSummary, metrics: dict):
    """Render summary metric cards with neumorphic design."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        compliance_class = "nm-card--success" if summary.compliance_rate >= 80 else "nm-card--warning"
        st.markdown(f"""
        <div class="nm-card {compliance_class}">
            <div class="nm-card-value">{summary.compliance_rate:.0f}%</div>
            <div class="nm-card-label">Compliance Rate</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="nm-card">
            <div class="nm-card-value">{summary.total_tasks}</div>
            <div class="nm-card-label">Total Tasks</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="nm-card nm-card--info">
            <div class="nm-card-value">{metrics.get('total_points', 0):.0f}</div>
            <div class="nm-card-label">Story Points</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        updates_class = "nm-card--warning" if summary.tasks_missing_updates > 0 else "nm-card--success"
        st.markdown(f"""
        <div class="nm-card {updates_class}">
            <div class="nm-card-value">{summary.tasks_missing_updates}</div>
            <div class="nm-card-label">Missing Updates</div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# Asana Task Viewer (Modal Dialog)
# =============================================================================

@st.dialog("Task Details", width="large")
def show_task_dialog(task_gid: str, task_url: str, task_name: str, reporter):
    """Show task details in a modal dialog."""
    # Header with link to Asana
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(task_name)
    with col2:
        st.link_button("Open in Asana", task_url, use_container_width=True)

    st.divider()

    # Fetch full task details from API
    try:
        with st.spinner("Loading task details..."):
            task_details = reporter.client.tasks_api.get_task(
                task_gid,
                opts={"opt_fields": "name,notes,assignee.name,due_on,completed,created_at,modified_at,custom_fields,custom_fields.name,custom_fields.display_value,permalink_url"}
            )
            task = task_details.to_dict() if hasattr(task_details, 'to_dict') else dict(task_details)

        # Display task details in columns
        col1, col2 = st.columns(2)

        with col1:
            assignee = task.get('assignee', {})
            assignee_name = assignee.get('name', 'Unassigned') if assignee else 'Unassigned'
            st.markdown(f"**Assignee:** {assignee_name}")
            st.markdown(f"**Due Date:** {task.get('due_on') or 'Not set'}")
            st.markdown(f"**Status:** {'Completed' if task.get('completed') else 'In Progress'}")

        with col2:
            st.markdown(f"**Created:** {task.get('created_at', '')[:10] if task.get('created_at') else 'N/A'}")
            st.markdown(f"**Modified:** {task.get('modified_at', '')[:10] if task.get('modified_at') else 'N/A'}")

        # Custom fields
        custom_fields = task.get('custom_fields', []) or []
        if custom_fields:
            st.divider()
            st.markdown("**Custom Fields:**")
            cf_cols = st.columns(3)
            for i, cf in enumerate(custom_fields):
                if cf and cf.get('display_value'):
                    cf_cols[i % 3].markdown(f"**{cf.get('name')}:** {cf.get('display_value')}")

        # Description
        st.divider()
        notes = task.get('notes', '')
        if notes:
            st.markdown("**Description:**")
            st.text_area("", value=notes, height=200, disabled=True, key="dialog_task_notes", label_visibility="collapsed")
        else:
            st.warning("No description provided")

        # Fetch and display recent comments
        st.divider()
        st.markdown("**Recent Comments:**")
        try:
            comments = reporter.client.get_task_comments(task_gid, limit=5)
            if comments:
                for comment in comments[:5]:
                    author = comment.get('created_by', {}).get('name', 'Unknown')
                    text = comment.get('text', '')
                    date = comment.get('created_at', '')[:10] if comment.get('created_at') else ''
                    if text:
                        st.markdown(f"**{author}** ({date})")
                        st.markdown(f"> {text[:500]}{'...' if len(text) > 500 else ''}")
                        st.write("")
            else:
                st.info("No comments yet")
        except Exception:
            st.info("Could not load comments")

    except Exception as e:
        st.error(f"Could not load task details: {e}")
        st.link_button("Open in Asana instead", task_url)


def open_task_viewer(task_gid: str, task_url: str, task_name: str):
    """Store task info in session state to trigger dialog."""
    st.session_state["selected_task_gid"] = task_gid
    st.session_state["selected_task_url"] = task_url
    st.session_state["selected_task_name"] = task_name


# =============================================================================
# Burndown Chart
# =============================================================================

def task_in_sprint(task: TaskCompliance, sprint: str) -> bool:
    """Check if a task belongs to a sprint (handles comma-separated sprint values)."""
    if not task.sprint:
        return False
    # Sprint field can be comma-separated like "Manali, London"
    task_sprints = [s.strip() for s in task.sprint.split(",")]
    return sprint in task_sprints


def render_burndown_chart(
    results: list[TaskCompliance],
    completed_results: Optional[list[TaskCompliance]] = None,
    selected_sprint: Optional[str] = None
):
    """Render sprint burndown chart with actual progress line."""
    if not PLOTLY_AVAILABLE:
        st.warning("Plotly is required for charts. Install with: pip install plotly")
        return

    # Determine which sprint to show
    if selected_sprint:
        sprint = selected_sprint
        # Filter tasks that contain this sprint (handles comma-separated values)
        sprint_tasks = [t for t in results if task_in_sprint(t, sprint)]
        completed_sprint_tasks = [t for t in (completed_results or []) if task_in_sprint(t, sprint)]
    else:
        sprint = "All Sprints"
        sprint_tasks = results
        completed_sprint_tasks = completed_results or []

    if not sprint_tasks and not completed_sprint_tasks:
        st.info("No tasks found for burndown chart")
        return

    # Separate tasks by completion status
    # "Done" tasks from incomplete list (progress="Done" but not marked complete in Asana)
    done_tasks = [t for t in sprint_tasks if t.progress == "Done"]
    active_tasks = [t for t in sprint_tasks if t.progress != "Done"]

    # Calculate total points (all tasks in sprint)
    total_points = 0
    completed_points = 0
    completion_dates = {}  # date -> points completed that day

    # Process active (not done) tasks
    for task in active_tasks:
        try:
            points = float(task.story_points) if task.story_points else 0
        except (ValueError, TypeError):
            points = 0
        total_points += points

    # Process "Done" tasks from incomplete list
    for task in done_tasks:
        try:
            points = float(task.story_points) if task.story_points else 0
        except (ValueError, TypeError):
            points = 0
        total_points += points
        completed_points += points

        # Use due_on as completion date approximation for Done tasks
        if points > 0 and task.due_on:
            completion_date = task.due_on
            if completion_date not in completion_dates:
                completion_dates[completion_date] = 0
            completion_dates[completion_date] += points

    # Process truly completed tasks from Asana
    for task in completed_sprint_tasks:
        try:
            points = float(task.story_points) if task.story_points else 0
        except (ValueError, TypeError):
            points = 0
        total_points += points
        completed_points += points

        # Use completed_at for actual completion date
        if points > 0 and task.completed_at:
            completion_date = task.completed_at[:10]  # YYYY-MM-DD
            if completion_date not in completion_dates:
                completion_dates[completion_date] = 0
            completion_dates[completion_date] += points
        elif points > 0 and task.due_on:
            # Fallback to due_on if no completed_at
            completion_date = task.due_on
            if completion_date not in completion_dates:
                completion_dates[completion_date] = 0
            completion_dates[completion_date] += points

    if total_points == 0:
        st.info("No story points found for this sprint")
        return

    # Debug info - show what data we have
    with st.expander("Debug: Burndown Data", expanded=True):
        st.write(f"**Sprint filter:** {sprint}")
        st.write(f"**Incomplete tasks in sprint:** {len(sprint_tasks)}")
        st.write(f"**Completed tasks from API:** {len(completed_sprint_tasks)}")
        st.write(f"**Active (not Done):** {len(active_tasks)}")
        st.write(f"**Done status tasks:** {len(done_tasks)}")
        st.write(f"**Total points:** {total_points}")
        st.write(f"**Completed points:** {completed_points}")
        st.write(f"**Completion dates:** {dict(sorted(completion_dates.items()))}")

        # Show sample of completed tasks
        if completed_sprint_tasks:
            st.write("**Sample completed tasks:**")
            for t in completed_sprint_tasks[:5]:
                st.write(f"- {t.name[:40]}... | Sprint: {t.sprint} | Points: {t.story_points} | completed_at: {t.completed_at}")

    # Get date range from all tasks
    all_dates = []
    for t in sprint_tasks + completed_sprint_tasks:
        if t.due_on:
            try:
                all_dates.append(datetime.strptime(t.due_on, "%Y-%m-%d"))
            except ValueError:
                pass
        if t.created_at:
            try:
                all_dates.append(datetime.strptime(t.created_at[:10], "%Y-%m-%d"))
            except ValueError:
                pass

    if not all_dates:
        st.warning("No dates found. Cannot generate burndown chart.")
        return

    sprint_start = min(all_dates)
    sprint_end = max(all_dates)
    today = datetime.now()

    # Ensure reasonable date range
    if (sprint_end - sprint_start).days < 7:
        sprint_start = sprint_end - timedelta(days=14)

    # Extend to today if sprint is ongoing
    if today > sprint_end:
        sprint_end = today

    sprint_days = (sprint_end - sprint_start).days + 1
    if sprint_days <= 0:
        sprint_days = 14

    # Generate date range
    dates = []
    ideal_line = []
    actual_line = []

    daily_decrement = total_points / sprint_days
    remaining = total_points

    current_date = sprint_start
    day_num = 0

    while current_date <= sprint_end:
        date_str = current_date.strftime("%Y-%m-%d")
        dates.append(date_str)

        # Ideal burndown
        ideal_remaining = max(0, total_points - (daily_decrement * day_num))
        ideal_line.append(ideal_remaining)

        # Actual burndown - subtract completed points up to this date
        if date_str in completion_dates:
            remaining -= completion_dates[date_str]

        # Only show actual line up to today
        if current_date <= today:
            actual_line.append(max(0, remaining))
        else:
            actual_line.append(None)

        current_date += timedelta(days=1)
        day_num += 1

    # Create chart
    fig = go.Figure()

    # Neumorphism color palette for charts
    nm_primary = '#6B7FD7'      # Muted blue-purple
    nm_success = '#5B9A8B'      # Sage green
    nm_error = '#C9736D'        # Muted coral
    nm_text_primary = '#2D3748' # Dark slate
    nm_bg = '#E4E8EC'           # Soft gray background

    # Ideal burndown line
    fig.add_trace(go.Scatter(
        x=dates,
        y=ideal_line,
        mode='lines',
        name='Ideal Burndown',
        line=dict(color=nm_primary, dash='dash', width=2)
    ))

    # Actual burndown line
    fig.add_trace(go.Scatter(
        x=dates,
        y=actual_line,
        mode='lines+markers',
        name='Actual Burndown',
        line=dict(color=nm_success, width=3),
        marker=dict(size=6),
        connectgaps=False
    ))

    # Current state marker
    today_str = today.strftime("%Y-%m-%d")
    if today_str in dates:
        idx = dates.index(today_str)
        current_remaining = actual_line[idx] if actual_line[idx] is not None else remaining
        fig.add_trace(go.Scatter(
            x=[today_str],
            y=[current_remaining],
            mode='markers',
            name='Today',
            marker=dict(color=nm_error, size=14, symbol='diamond'),
            showlegend=True
        ))

    # Summary annotation
    pct_complete = (completed_points / total_points * 100) if total_points > 0 else 0
    fig.add_annotation(
        x=0.02, y=0.98,
        xref="paper", yref="paper",
        text=f"Completed: {completed_points:.0f} / {total_points:.0f} pts ({pct_complete:.0f}%)",
        showarrow=False,
        font=dict(size=14, color=nm_success),
        bgcolor="rgba(228,232,236,0.95)",
        borderpad=6
    )

    fig.update_layout(
        title=dict(
            text=f"Sprint Burndown: {sprint}",
            font=dict(size=20, color=nm_text_primary)
        ),
        xaxis_title="Date",
        yaxis_title="Story Points Remaining",
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450,
        margin=dict(t=80),
        paper_bgcolor=nm_bg,
        plot_bgcolor=nm_bg,
        font=dict(color=nm_text_primary),
        xaxis=dict(
            gridcolor='rgba(163, 177, 198, 0.3)',
            linecolor='rgba(163, 177, 198, 0.5)',
            tickcolor='rgba(163, 177, 198, 0.5)',
        ),
        yaxis=dict(
            gridcolor='rgba(163, 177, 198, 0.3)',
            linecolor='rgba(163, 177, 198, 0.5)',
            tickcolor='rgba(163, 177, 198, 0.5)',
        ),
    )

    st.plotly_chart(fig, use_container_width=True, key="burndown_main")

    # Download burndown data
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        df_download = pd.DataFrame({
            "Date": dates,
            "Ideal Remaining": [round(p, 1) for p in ideal_line],
            "Actual Remaining": [round(p, 1) if p is not None else "" for p in actual_line],
        })

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_download.to_excel(writer, index=False, sheet_name='Burndown')
        buffer.seek(0)

        st.download_button(
            label="Download Burndown Data",
            data=buffer,
            file_name=f"burndown_{sprint.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# =============================================================================
# Alert Sections
# =============================================================================

def get_missing_fields(task: TaskCompliance) -> list[str]:
    """Get list of missing mandatory fields for a task."""
    missing = []
    if task.missing_epic:
        missing.append("Epic")
    if task.missing_sprint:
        missing.append("Sprint")
    if task.missing_type:
        missing.append("Type")
    if task.missing_points:
        missing.append("Story Points")
    if task.invalid_points:
        missing.append("Invalid Points")
    if task.missing_severity:
        missing.append("Severity")
    if task.missing_due_date:
        missing.append("Due Date")
    if task.missing_description:
        missing.append("Description/ACs")
    return missing


def get_all_issues(task: TaskCompliance) -> list[str]:
    """Get list of all compliance issues including rule violations."""
    issues = get_missing_fields(task)
    # Use getattr for backward compatibility with cached TaskCompliance objects
    rule_violations = getattr(task, 'rule_violations', [])
    if rule_violations:
        issues.extend(rule_violations)
    return issues


def render_red_alert_section(results: list[TaskCompliance]):
    """Render red alert for Review/QA tasks with issues."""
    # Filter: Review or QA with any compliance issue (including rule violations)
    red_tasks = [
        t for t in results
        if t.progress in ("Review", "QA")
        and (t.mandatory_count > 0 or t.missing_daily_update or getattr(t, 'rule_violations', []))
    ]

    if not red_tasks:
        return  # Don't show section if no issues

    st.markdown("""
    <div class="nm-alert nm-alert--error">
        <h3>🔴 Critical - Review/QA Tasks Need Attention</h3>
        <p>These tasks are in final stages but have issues that may block release</p>
    </div>
    """, unsafe_allow_html=True)

    # Create header row
    header_cols = st.columns([3, 1.5, 1, 2, 1, 1])
    headers = ["Task Name", "Assignee", "Status", "Issues", "Hours Since Update", "Actions"]
    for i, header in enumerate(headers):
        header_cols[i].markdown(f"**{header}**")

    # Create data rows
    for idx, task in enumerate(red_tasks):
        row_cols = st.columns([3, 1.5, 1, 2, 1, 1])

        # Task name (truncated)
        task_name = task.name[:35] + "..." if len(task.name) > 35 else task.name
        row_cols[0].write(task_name)

        # Assignee
        row_cols[1].write(task.assignee or "Unassigned")

        # Status
        row_cols[2].write(task.progress or "-")

        # Issues
        issues = []
        if task.missing_daily_update:
            issues.append("No daily update")
        missing = get_missing_fields(task)
        if missing:
            issues.append(f"Missing: {', '.join(missing[:2])}" + ("..." if len(missing) > 2 else ""))
        task_rule_violations = getattr(task, 'rule_violations', [])
        if task_rule_violations:
            issues.append(f"Rules: {', '.join(task_rule_violations[:1])}" + ("..." if len(task_rule_violations) > 1 else ""))
        row_cols[3].write("; ".join(issues) if issues else "-")

        # Hours since update
        hours = "-"
        if task.hours_since_update is not None:
            hours = f"{task.hours_since_update:.0f}h"
        row_cols[4].write(hours)

        # Action buttons
        btn_col1, btn_col2 = row_cols[5].columns(2)
        if btn_col1.button("👁", key=f"red_view_{idx}", help="View in app"):
            st.session_state["selected_task_gid"] = task.gid
            st.session_state["selected_task_url"] = task.url
            st.session_state["selected_task_name"] = task.name
            st.rerun()
        btn_col2.link_button("↗", task.url, help="Open in Asana")

    st.markdown("---")


def render_amber_alert_section(results: list[TaskCompliance]):
    """Render amber alert for To Do/In Progress tasks missing details or with rule violations."""
    # Filter: To Do or In Progress with missing mandatory fields or rule violations
    amber_tasks = [
        t for t in results
        if t.progress in ("To Do", "In Progress")
        and (t.mandatory_count > 0 or getattr(t, 'rule_violations', []))
    ]

    if not amber_tasks:
        return  # Don't show section if no issues

    st.markdown("""
    <div class="nm-alert nm-alert--warning">
        <h3>⚠️ Action Required - Tasks Need Attention</h3>
        <p>These tasks in To Do/In Progress have missing fields or rule violations</p>
    </div>
    """, unsafe_allow_html=True)

    # Create header row
    header_cols = st.columns([3, 1.5, 1, 3, 1])
    headers = ["Task Name", "Assignee", "Status", "Issues", "Actions"]
    for i, header in enumerate(headers):
        header_cols[i].markdown(f"**{header}**")

    # Create data rows
    for idx, task in enumerate(amber_tasks):
        row_cols = st.columns([3, 1.5, 1, 3, 1])

        # Task name (truncated)
        task_name = task.name[:35] + "..." if len(task.name) > 35 else task.name
        row_cols[0].write(task_name)

        # Assignee
        row_cols[1].write(task.assignee or "Unassigned")

        # Status
        row_cols[2].write(task.progress or "-")

        # Issues (missing fields + rule violations)
        all_issues = get_all_issues(task)
        row_cols[3].write(", ".join(all_issues) if all_issues else "-")

        # Action buttons
        btn_col1, btn_col2 = row_cols[4].columns(2)
        if btn_col1.button("👁", key=f"amber_view_{idx}", help="View in app"):
            st.session_state["selected_task_gid"] = task.gid
            st.session_state["selected_task_url"] = task.url
            st.session_state["selected_task_name"] = task.name
            st.rerun()
        btn_col2.link_button("↗", task.url, help="Open in Asana")

    st.markdown("---")


# =============================================================================
# Compliance Tables
# =============================================================================

def render_attributes_summary(summary: ReportSummary):
    """Render mandatory attributes summary."""
    st.subheader("Mandatory Attributes Missing/Invalid")

    # Use getattr for backward compatibility with cached summaries
    rule_violations_count = getattr(summary, 'rule_violations', 0)

    attrs = [
        ("Epic", summary.missing_epic, "🟠"),
        ("Sprint", summary.missing_sprint, "🟠"),
        ("Type", summary.missing_type, "🟠"),
        ("Story Points", summary.missing_points, "🟡"),
        ("Invalid Points", summary.invalid_points, "🟡"),
        ("Severity", summary.missing_severity, "🟡"),
        ("Due Date", summary.missing_due_date, "🟡"),
        ("Description", summary.missing_description, "🟡"),
        ("Rule Violations", rule_violations_count, "🔴"),
    ]

    cols = st.columns(3)
    for i, (name, count, icon) in enumerate(attrs):
        pct = (count / summary.total_tasks * 100) if summary.total_tasks > 0 else 0
        with cols[i % 3]:
            delta_color = "off" if count == 0 else "inverse"
            label = f"{icon} {name}" if count > 0 else f"✅ {name}"
            st.metric(label=label, value=count, delta=f"{pct:.1f}%", delta_color=delta_color)


def render_assignee_table(summary: ReportSummary):
    """Render compliance by assignee."""
    st.subheader("Compliance by Assignee")

    if not summary.by_assignee:
        st.info("No assignee data")
        return

    data = []
    for assignee, info in summary.by_assignee.items():
        total = info["total"]
        issues = info["issues"]
        compliant = total - issues
        rate = (compliant / total * 100) if total > 0 else 100
        data.append({
            "Assignee": assignee,
            "Tasks": total,
            "Compliant": compliant,
            "Issues": issues,
            "Compliance": f"{rate:.0f}%"
        })

    st.dataframe(data, use_container_width=True, hide_index=True)


def render_task_table(tasks: list[TaskCompliance], title: str, columns: list[str], table_key: str = ""):
    """Render a task table with expander and view buttons."""
    if not tasks:
        return

    with st.expander(f"{title} ({len(tasks)} tasks)", expanded=False):
        # Create header row
        header_cols = st.columns([3, 2, 1, 1, 1, 1])
        col_names = ["Task", "Assignee", "Progress", "Sprint", "Due Date", "Actions"]
        for i, col_name in enumerate(col_names):
            if i < len(columns) or col_name == "Actions":
                header_cols[i].markdown(f"**{col_name}**")

        # Create data rows with view buttons
        for idx, t in enumerate(tasks):
            row_cols = st.columns([3, 2, 1, 1, 1, 1])

            task_name = t.name[:40] + "..." if len(t.name) > 40 else t.name
            row_cols[0].write(task_name)
            row_cols[1].write(t.assignee or "Unassigned")
            row_cols[2].write(t.progress or "-")
            row_cols[3].write(t.sprint or "-")
            row_cols[4].write(t.due_on or "-")

            # Action buttons
            btn_col1, btn_col2 = row_cols[5].columns(2)
            if btn_col1.button("👁", key=f"view_{table_key}_{idx}", help="View in app"):
                st.session_state["selected_task_gid"] = t.gid
                st.session_state["selected_task_url"] = t.url
                st.session_state["selected_task_name"] = t.name
                st.rerun()
            btn_col2.link_button("↗", t.url, help="Open in Asana")


def render_rule_violations_table(tasks: list[TaskCompliance], table_key: str = "rule_violations"):
    """Render a table for tasks with rule violations showing Type and Story Points."""
    if not tasks:
        return

    with st.expander(f"🔴 Rule Violations - Epics/Bugs with Story Points ({len(tasks)} tasks)", expanded=False):
        # Create header row
        header_cols = st.columns([3, 1.5, 1, 1, 2, 1])
        col_names = ["Task", "Assignee", "Type", "Points", "Violation", "Actions"]
        for i, col_name in enumerate(col_names):
            header_cols[i].markdown(f"**{col_name}**")

        # Create data rows with view buttons
        for idx, t in enumerate(tasks):
            row_cols = st.columns([3, 1.5, 1, 1, 2, 1])

            task_name = t.name[:40] + "..." if len(t.name) > 40 else t.name
            row_cols[0].write(task_name)
            row_cols[1].write(t.assignee or "Unassigned")
            row_cols[2].write(t.task_type or "-")
            row_cols[3].write(t.story_points or "-")
            violations = getattr(t, 'rule_violations', [])
            row_cols[4].write(", ".join(violations) if violations else "-")

            # Action buttons
            btn_col1, btn_col2 = row_cols[5].columns(2)
            if btn_col1.button("👁", key=f"view_{table_key}_{idx}", help="View in app"):
                st.session_state["selected_task_gid"] = t.gid
                st.session_state["selected_task_url"] = t.url
                st.session_state["selected_task_name"] = t.name
                st.rerun()
            btn_col2.link_button("↗", t.url, help="Open in Asana")


def render_compliance_details(results: list[TaskCompliance]):
    """Render detailed compliance findings."""
    st.markdown("""
    <div class="nm-section-compliance">
        <h3>📋 Compliance Details</h3>
        <p style="color: #5A6778; margin: 0; font-size: 0.9rem;">Detailed breakdown of tasks with missing or invalid fields</p>
    </div>
    """, unsafe_allow_html=True)

    # Rule Violations (Critical - should be addressed first)
    rule_violations = [t for t in results if getattr(t, 'rule_violations', [])]
    if rule_violations:
        render_rule_violations_table(rule_violations)

    # Missing Daily Updates (Critical)
    missing_updates = [t for t in results if t.missing_daily_update]
    if missing_updates:
        render_task_table(missing_updates, "🔴 Missing Daily Updates", ["Task", "Assignee", "Progress"], "updates")

    # Missing Epic
    missing_epic = [t for t in results if t.missing_epic]
    if missing_epic:
        render_task_table(missing_epic, "🟠 Missing Epic", ["Task", "Assignee", "Progress"], "epic")

    # Missing Sprint
    missing_sprint = [t for t in results if t.missing_sprint]
    if missing_sprint:
        render_task_table(missing_sprint, "🟠 Missing Sprint", ["Task", "Assignee", "Progress"], "sprint")

    # Missing Type
    missing_type = [t for t in results if t.missing_type]
    if missing_type:
        render_task_table(missing_type, "🟠 Missing Type", ["Task", "Assignee", "Progress"], "type")

    # Missing Story Points
    missing_points = [t for t in results if t.missing_points]
    if missing_points:
        render_task_table(missing_points, "🟡 Missing Story Points", ["Task", "Assignee", "Progress"], "points")

    # Invalid Story Points (non-Fibonacci)
    invalid_points = [t for t in results if t.invalid_points]
    if invalid_points:
        render_task_table(invalid_points, "🟡 Invalid Story Points (non-Fibonacci)", ["Task", "Assignee", "Progress"], "invalid_points")

    # Missing Severity
    missing_severity = [t for t in results if t.missing_severity]
    if missing_severity:
        render_task_table(missing_severity, "🟡 Missing Severity", ["Task", "Assignee", "Progress"], "severity")

    # Missing Due Date
    missing_due = [t for t in results if t.missing_due_date]
    if missing_due:
        render_task_table(missing_due, "🟡 Missing Due Date", ["Task", "Assignee", "Sprint"], "due")

    # Missing Description
    missing_desc = [t for t in results if t.missing_description]
    if missing_desc:
        render_task_table(missing_desc, "🟡 Missing Description/ACs", ["Task", "Assignee", "Progress"], "desc")

    # Show message if all compliant
    all_issues = (rule_violations + missing_updates + missing_epic + missing_sprint + missing_type +
                  missing_points + invalid_points + missing_severity + missing_due + missing_desc)
    if not all_issues:
        st.success("All tasks are fully compliant! No missing fields or rule violations.")


# =============================================================================
# Download Buttons
# =============================================================================

def render_download_buttons(results: list[TaskCompliance], summary: ReportSummary, config: Config):
    """Render download buttons."""
    st.subheader("Download Report")

    col1, col2, col3 = st.columns(3)

    with col1:
        md_generator = MarkdownReportGenerator(config)
        markdown_content = md_generator.generate(results, summary)
        st.download_button(
            label="Download Markdown",
            data=markdown_content,
            file_name=f"compliance_{summary.report_date}.md",
            mime="text/markdown",
        )

    with col2:
        json_generator = JSONReportGenerator(config)
        json_content = json_generator.generate(results, summary)
        st.download_button(
            label="Download JSON",
            data=json_content,
            file_name=f"compliance_{summary.report_date}.json",
            mime="application/json",
        )

    with col3:
        if OPENPYXL_AVAILABLE:
            from asana_daily_report import ExcelReportGenerator
            excel_generator = ExcelReportGenerator(config)
            workbook = excel_generator.generate(results, summary)
            buffer = io.BytesIO()
            workbook.save(buffer)
            buffer.seek(0)
            st.download_button(
                label="Download Excel",
                data=buffer,
                file_name=f"compliance_{summary.report_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.button("Download Excel", disabled=True, help="Requires openpyxl")


# =============================================================================
# Main App
# =============================================================================

def render_homepage():
    """Render the landing page before report generation."""
    # Hero section with logo and title
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "Text-Logo_SourceHub.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=280)

        st.markdown("""
        <div style="text-align: center; padding: 10px 20px 20px 20px;">
            <h1 style="font-size: 2.5rem; font-weight: 700; color: #2D3748; margin: 0; letter-spacing: -1px;">
                Sprint Dashboard
            </h1>
            <p style="font-size: 1rem; color: #5A6778; margin-top: 8px;">
                Development Team Compliance & Burndown Tracking
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Feature cards
    st.markdown("""
    <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; padding: 30px 20px;">
        <div style="background: linear-gradient(135deg, #E4E8F0 0%, #DCE2EC 100%);
                    border-radius: 16px; padding: 24px; width: 200px; text-align: center;
                    box-shadow: 6px 6px 12px #A3B1C6, -6px -6px 12px #FFFFFF;">
            <div style="font-size: 2rem; margin-bottom: 8px; color: #6B7FD7;">&#x2713;</div>
            <div style="font-weight: 600; color: #2D3748; margin-bottom: 4px;">Compliance</div>
            <div style="font-size: 0.85rem; color: #5A6778;">Track task compliance & missing fields</div>
        </div>
        <div style="background: linear-gradient(135deg, #E4F0E8 0%, #DCE8E2 100%);
                    border-radius: 16px; padding: 24px; width: 200px; text-align: center;
                    box-shadow: 6px 6px 12px #A3B1C6, -6px -6px 12px #FFFFFF;">
            <div style="font-size: 2rem; margin-bottom: 8px; color: #5B9A8B;">&#x2197;</div>
            <div style="font-weight: 600; color: #2D3748; margin-bottom: 4px;">Burndown</div>
            <div style="font-size: 0.85rem; color: #5A6778;">Visualize sprint progress & velocity</div>
        </div>
        <div style="background: linear-gradient(135deg, #F0E8E4 0%, #E8E2DC 100%);
                    border-radius: 16px; padding: 24px; width: 200px; text-align: center;
                    box-shadow: 6px 6px 12px #A3B1C6, -6px -6px 12px #FFFFFF;">
            <div style="font-size: 2rem; margin-bottom: 8px; color: #C9736D;">&#x26A0;</div>
            <div style="font-weight: 600; color: #2D3748; margin-bottom: 4px;">Alerts</div>
            <div style="font-size: 0.85rem; color: #5A6778;">Identify blockers & action items</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""
    init_session_state()

    # Sidebar - always render for configuration
    config_options = render_sidebar()

    # PRIORITY: Check if generating - show ONLY loader, nothing else
    if st.session_state.get("is_generating", False):
        # Neumorphic loader container with status
        st.markdown("""
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;
                    min-height: 50vh; text-align: center;">
            <div style="background: #E4E8EC; border-radius: 20px; padding: 40px 50px;
                        box-shadow: 8px 8px 16px #A3B1C6, -8px -8px 16px #FFFFFF;">
                <div style="width: 60px; height: 60px; margin: 0 auto 20px auto;
                            border: 4px solid #E4E8EC; border-top: 4px solid #6B7FD7;
                            border-radius: 50%; animation: spin 1s linear infinite;
                            box-shadow: inset 2px 2px 4px #A3B1C6, inset -2px -2px 4px #FFFFFF;">
                </div>
                <div style="font-size: 1.2rem; color: #2D3748; font-weight: 600; margin-bottom: 8px;">
                    Generating Report
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                with st.status("Loading...", expanded=True) as status:
                    st.write("Initializing compliance reporter...")
                    config = Config(
                        min_description_length=config_options["min_description_length"],
                        hours_without_update=config_options["hours_without_update"],
                    )
                    reporter = AsanaComplianceReporter(config_options["token"], config)

                    st.write("Fetching active tasks from Asana...")
                    tasks = reporter.client.get_tasks(completed=False)
                    st.write(f"Found {len(tasks)} active tasks")

                    completed_tasks = []
                    if config_options["fetch_completed"]:
                        st.write("Fetching completed tasks from last 30 days...")
                        completed_tasks = reporter.client.get_completed_tasks(since_days=30)
                        st.write(f"Found {len(completed_tasks)} completed tasks")

                    st.write("Analyzing task compliance...")
                    results = reporter.analyzer.analyze_all(
                        tasks,
                        fetch_comments=config_options["fetch_comments"]
                    )

                    completed_results = []
                    if completed_tasks:
                        st.write("Analyzing completed tasks...")
                        completed_results = reporter.analyzer.analyze_all(
                            completed_tasks,
                            fetch_comments=False,
                            include_done=True
                        )

                    st.write("Generating summary report...")
                    summary = reporter.analyzer.generate_summary(results)

                    # Store results
                    st.session_state["results"] = results
                    st.session_state["completed_results"] = completed_results
                    st.session_state["summary"] = summary
                    st.session_state["config"] = config
                    st.session_state["reporter"] = reporter
                    st.session_state["report_generated"] = True
                    st.session_state["is_generating"] = False

                    status.update(label="Report generated!", state="complete", expanded=False)

                st.rerun()
            except Exception as e:
                st.session_state["is_generating"] = False
                error_str = str(e).lower()
                if any(x in error_str for x in ["401", "403", "unauthorized", "forbidden"]):
                    st.error("Authentication failed. Please check your access token.")
                elif "rate limit" in error_str or "429" in error_str:
                    st.error("Rate limit exceeded. Please wait and try again.")
                else:
                    st.error(f"Error generating report: {e}")
        st.stop()  # Ensure nothing else renders
        return

    # Check token
    if not config_options["token"]:
        render_homepage()
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <div style="background: linear-gradient(135deg, #F5F0E0 0%, #EDE8D4 100%);
                        border-radius: 12px; padding: 20px; display: inline-block;
                        border-left: 4px solid #D4A574;
                        box-shadow: 4px 4px 8px #A3B1C6, -4px -4px 8px #FFFFFF;">
                <p style="color: #7A6830; margin: 0; font-size: 0.95rem;">
                    <span style="color: #D4A574;">&#x26A0;</span> Please enter your <strong>Asana Access Token</strong> in the sidebar to get started.
                </p>
                <p style="color: #5A6778; margin: 8px 0 0 0; font-size: 0.85rem;">
                    <a href="https://app.asana.com/0/developer-console" target="_blank" style="color: #6B7FD7;">
                        Get your token from Asana Developer Console &#x2192;
                    </a>
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Show homepage with Generate button if report not generated
    if not st.session_state.get("report_generated"):
        render_homepage()

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Generate Report", type="primary", use_container_width=True):
                st.session_state["is_generating"] = True
                st.rerun()
        return

    # Report is generated - show dashboard header
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
        <h1 style="font-size: 2rem; font-weight: 700; color: #2D3748; margin: 0;">
            Sprint Dashboard
        </h1>
    </div>
    """, unsafe_allow_html=True)
    st.caption("SourceHub Development Team")

    # Report is generated - show dashboard
    results = st.session_state["results"]
    completed_results = st.session_state.get("completed_results", [])
    summary = st.session_state["summary"]
    config = st.session_state["config"]
    reporter = st.session_state["reporter"]

    # Check if task viewer dialog should be opened
    if st.session_state.get("selected_task_gid"):
        show_task_dialog(
            st.session_state["selected_task_gid"],
            st.session_state.get("selected_task_url", ""),
            st.session_state.get("selected_task_name", "Task"),
            reporter
        )
        # Clear the selection after dialog is shown
        st.session_state["selected_task_gid"] = None
        st.session_state["selected_task_url"] = None
        st.session_state["selected_task_name"] = None

    # Dashboard filters (horizontal layout)
    filters = render_dashboard_filters(results, reporter.analyzer)

    # Apply filters
    filtered_results = reporter.analyzer.filter_results(
        results,
        sprint=filters.get("sprint"),
        assignees=filters.get("assignees"),
        statuses=filters.get("statuses"),
    )
    filtered_summary = reporter.analyzer.generate_summary(filtered_results)
    metrics = reporter.analyzer.calculate_sprint_metrics(filtered_results)

    # Report info
    st.caption(f"Report Date: {summary.report_date} | Showing: {len(filtered_results)} tasks")

    st.markdown("---")

    # Metric cards
    render_metric_cards(filtered_summary, metrics)

    st.markdown("---")

    # Burndown chart
    render_burndown_chart(filtered_results, completed_results, filters.get("sprint"))

    st.markdown("---")

    # Alert sections (red first - more critical, then amber)
    render_red_alert_section(filtered_results)
    render_amber_alert_section(filtered_results)

    # Compliance summary
    col1, col2 = st.columns(2)
    with col1:
        render_attributes_summary(filtered_summary)
    with col2:
        render_assignee_table(filtered_summary)

    st.markdown("---")

    # Detailed findings
    render_compliance_details(filtered_results)

    st.markdown("---")

    # Download buttons
    render_download_buttons(filtered_results, filtered_summary, config)


if __name__ == "__main__":
    main()
