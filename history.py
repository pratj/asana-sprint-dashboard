"""
Historical Data Storage for Sprint Analytics
=============================================
Stores and retrieves daily snapshots of sprint data for trend analysis.

Storage location: ~/.asana_reports/history/
Format: JSON files with date-based naming

Requires Python 3.9+
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Final
from dataclasses import dataclass, asdict, field


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_HISTORY_DIR: Final[Path] = Path.home() / ".asana_reports" / "history"

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SprintSnapshot:
    """A point-in-time snapshot of sprint metrics."""
    date: str  # YYYY-MM-DD
    sprint: str

    # Story points
    total_points: float = 0
    completed_points: float = 0
    remaining_points: float = 0

    # Task counts
    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    todo_tasks: int = 0
    review_tasks: int = 0
    qa_tasks: int = 0

    # Compliance
    compliance_rate: float = 0
    tasks_missing_updates: int = 0

    # By status breakdown
    points_by_status: dict = field(default_factory=dict)

    # Metadata
    generated_at: str = ""


@dataclass
class VelocityData:
    """Velocity data for a completed sprint."""
    sprint: str
    completed_points: float
    planned_points: float
    start_date: str
    end_date: str
    duration_days: int
    completion_rate: float  # completed/planned as percentage


class HistoryManager:
    """Manages historical sprint data storage and retrieval."""

    def __init__(self, history_dir: Optional[Path] = None):
        self.history_dir = history_dir or DEFAULT_HISTORY_DIR
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories for different data types
        self.snapshots_dir = self.history_dir / "snapshots"
        self.velocity_dir = self.history_dir / "velocity"
        self.snapshots_dir.mkdir(exist_ok=True)
        self.velocity_dir.mkdir(exist_ok=True)

    @staticmethod
    def _atomic_write(filepath: Path, data: dict) -> None:
        """Write data to file atomically using temp file + rename.

        This prevents data corruption if the process is interrupted during write.

        Args:
            filepath: Target file path
            data: Dictionary to serialize as JSON
        """
        # Write to temp file in same directory (ensures same filesystem for rename)
        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent,
            prefix=f".{filepath.stem}_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            # Atomic rename (on POSIX systems)
            os.replace(tmp_path, filepath)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for safe use in filenames.

        Removes any characters that could be used for path traversal or
        are invalid in filenames across different operating systems.

        Args:
            name: The string to sanitize

        Returns:
            A safe filename string containing only alphanumeric, space, dash, underscore
        """
        # Remove any non-alphanumeric, space, dash, underscore
        safe = re.sub(r'[^\w\s-]', '', name)
        # Replace spaces and multiple dashes/underscores with single underscore
        safe = re.sub(r'[-\s]+', '_', safe)
        # Remove leading/trailing underscores
        safe = safe.strip('_')
        # Truncate to reasonable length
        return safe[:200] if safe else "unnamed"

    # =========================================================================
    # Snapshot Operations
    # =========================================================================

    def save_snapshot(self, snapshot: SprintSnapshot) -> Path:
        """Save a sprint snapshot to disk atomically.

        Note: This does not mutate the input snapshot object.
        Uses atomic write to prevent data corruption.
        """
        safe_sprint = self._sanitize_filename(snapshot.sprint)
        filename = f"{snapshot.date}_{safe_sprint}.json"
        filepath = self.snapshots_dir / filename

        # Create a copy of snapshot data and add timestamp
        data = asdict(snapshot)
        data['generated_at'] = datetime.now().isoformat()

        self._atomic_write(filepath, data)

        return filepath

    def load_snapshot(self, date: str, sprint: str) -> Optional[SprintSnapshot]:
        """Load a specific snapshot by date and sprint."""
        safe_sprint = self._sanitize_filename(sprint)
        filename = f"{date}_{safe_sprint}.json"
        filepath = self.snapshots_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return SprintSnapshot(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to load snapshot {filepath}: {e}")
            return None

    def get_snapshots_for_sprint(self, sprint: str, days: int = 30) -> list[SprintSnapshot]:
        """Get all snapshots for a sprint within the last N days."""
        snapshots = []
        safe_sprint = self._sanitize_filename(sprint)
        cutoff_date = datetime.now() - timedelta(days=days)

        # Look for files matching the sprint pattern
        for filepath in sorted(self.snapshots_dir.glob(f"*_{safe_sprint}.json")):
            try:
                # Extract date from filename first to avoid loading unnecessary files
                filename = filepath.stem  # e.g., "2024-01-15_Sprint_1"
                date_part = filename.split("_")[0]  # "2024-01-15"

                try:
                    file_date = datetime.strptime(date_part, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        continue  # Skip files outside date range
                except ValueError:
                    pass  # If date parsing fails, load the file to check

                with open(filepath, 'r') as f:
                    data = json.load(f)

                snapshot = SprintSnapshot(**data)
                snapshots.append(snapshot)

            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Could not load snapshot {filepath}: {e}")
                continue

        return sorted(snapshots, key=lambda s: s.date)

    def get_latest_snapshot(self, sprint: str) -> Optional[SprintSnapshot]:
        """Get the most recent snapshot for a sprint."""
        snapshots = self.get_snapshots_for_sprint(sprint, days=90)
        return snapshots[-1] if snapshots else None

    def get_all_snapshots(self, days: int = 30) -> list[SprintSnapshot]:
        """Get all snapshots within the last N days."""
        snapshots = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for filepath in sorted(self.snapshots_dir.glob("*.json")):
            try:
                # Extract date from filename first for efficiency
                filename = filepath.stem
                date_part = filename.split("_")[0]

                try:
                    file_date = datetime.strptime(date_part, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        continue
                except ValueError:
                    pass  # Load file to check date if parsing fails

                with open(filepath, 'r') as f:
                    data = json.load(f)

                snapshot = SprintSnapshot(**data)
                snapshots.append(snapshot)

            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Could not load snapshot {filepath}: {e}")
                continue

        return sorted(snapshots, key=lambda s: (s.sprint, s.date))

    # =========================================================================
    # Velocity Operations
    # =========================================================================

    def save_velocity(self, velocity: VelocityData) -> Path:
        """Save velocity data for a sprint atomically.

        Uses atomic write to prevent data corruption.
        """
        safe_sprint = self._sanitize_filename(velocity.sprint)
        filename = f"{safe_sprint}.json"
        filepath = self.velocity_dir / filename

        self._atomic_write(filepath, asdict(velocity))

        return filepath

    def load_velocity(self, sprint: str) -> Optional[VelocityData]:
        """Load velocity data for a sprint."""
        safe_sprint = self._sanitize_filename(sprint)
        filename = f"{safe_sprint}.json"
        filepath = self.velocity_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return VelocityData(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to load velocity data {filepath}: {e}")
            return None

    def get_all_velocities(self) -> list[VelocityData]:
        """Get velocity data for all sprints."""
        velocities = []

        for filepath in sorted(self.velocity_dir.glob("*.json")):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                velocities.append(VelocityData(**data))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Could not load velocity data {filepath}: {e}")
                continue

        # Sort by start date
        return sorted(velocities, key=lambda v: v.start_date)

    # =========================================================================
    # Burndown Calculation
    # =========================================================================

    def calculate_burndown_data(
        self,
        sprint: str,
        sprint_start: str,
        sprint_end: str,
        total_points: float
    ) -> dict:
        """
        Calculate burndown data from snapshots.

        Returns:
            dict with keys:
                - dates: list of date strings
                - ideal: list of ideal remaining points
                - actual: list of actual remaining points
                - completed: list of completed points
        """
        snapshots = self.get_snapshots_for_sprint(sprint, days=60)

        start_date = datetime.strptime(sprint_start, "%Y-%m-%d")
        end_date = datetime.strptime(sprint_end, "%Y-%m-%d")
        sprint_days = (end_date - start_date).days + 1

        # Build date range
        dates = []
        ideal_points = []
        actual_points = []
        completed_points = []

        # Create a lookup of snapshots by date
        snapshot_by_date = {s.date: s for s in snapshots}

        # Daily point decrement for ideal line
        daily_decrement = total_points / sprint_days if sprint_days > 0 else 0

        current_date = start_date
        day_num = 0
        last_remaining = total_points
        last_completed = 0

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            dates.append(date_str)

            # Ideal burndown (linear from total to 0)
            ideal_remaining = total_points - (daily_decrement * day_num)
            ideal_points.append(max(0, ideal_remaining))

            # Actual from snapshot if available
            if date_str in snapshot_by_date:
                snapshot = snapshot_by_date[date_str]
                last_remaining = snapshot.remaining_points
                last_completed = snapshot.completed_points

            actual_points.append(last_remaining)
            completed_points.append(last_completed)

            current_date += timedelta(days=1)
            day_num += 1

        return {
            "dates": dates,
            "ideal": ideal_points,
            "actual": actual_points,
            "completed": completed_points,
            "total_points": total_points,
            "sprint_days": sprint_days,
        }

    # =========================================================================
    # Trend Analysis
    # =========================================================================

    def get_compliance_trend(self, days: int = 30) -> list[dict]:
        """
        Get compliance rate trend over time.

        Returns list of dicts with keys: date, compliance_rate, sprint
        """
        snapshots = self.get_all_snapshots(days)

        # Group by date and average compliance
        trend = []
        for snapshot in snapshots:
            trend.append({
                "date": snapshot.date,
                "compliance_rate": snapshot.compliance_rate,
                "sprint": snapshot.sprint,
            })

        return trend

    def get_velocity_trend(self) -> list[dict]:
        """
        Get velocity trend across sprints.

        Returns list of dicts with keys: sprint, completed_points, planned_points
        """
        velocities = self.get_all_velocities()

        trend = []
        for v in velocities:
            trend.append({
                "sprint": v.sprint,
                "completed_points": v.completed_points,
                "planned_points": v.planned_points,
                "completion_rate": v.completion_rate,
            })

        return trend

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup_old_snapshots(self, days: int = 90):
        """Remove snapshots older than N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        removed = 0

        for filepath in self.snapshots_dir.glob("*.json"):
            try:
                # Extract date from filename (YYYY-MM-DD_sprint.json)
                date_str = filepath.stem.split("_")[0]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    filepath.unlink()
                    removed += 1
            except (ValueError, IndexError):
                continue

        return removed


def create_snapshot_from_results(
    results: list,
    summary,
    sprint: str,
    date: Optional[str] = None
) -> SprintSnapshot:
    """
    Create a SprintSnapshot from compliance analysis results.

    Args:
        results: List of TaskCompliance objects
        summary: ReportSummary object
        sprint: Sprint name to filter/use
        date: Date string (YYYY-MM-DD), defaults to today
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Filter results for this sprint
    sprint_tasks = [t for t in results if t.sprint == sprint]

    # Calculate points
    total_points = 0
    completed_points = 0
    points_by_status = {}

    status_counts = {
        "To Do": 0,
        "In Progress": 0,
        "Review": 0,
        "QA": 0,
        "Done": 0,
    }

    for task in sprint_tasks:
        try:
            points = float(task.story_points) if task.story_points else 0
        except (ValueError, TypeError):
            points = 0

        total_points += points

        status = task.progress or "Unknown"
        if status in status_counts:
            status_counts[status] += 1

        if status not in points_by_status:
            points_by_status[status] = 0
        points_by_status[status] += points

        if status == "Done":
            completed_points += points

    remaining_points = total_points - completed_points

    return SprintSnapshot(
        date=date,
        sprint=sprint,
        total_points=total_points,
        completed_points=completed_points,
        remaining_points=remaining_points,
        total_tasks=len(sprint_tasks),
        completed_tasks=status_counts.get("Done", 0),
        in_progress_tasks=status_counts.get("In Progress", 0),
        todo_tasks=status_counts.get("To Do", 0),
        review_tasks=status_counts.get("Review", 0),
        qa_tasks=status_counts.get("QA", 0),
        compliance_rate=summary.compliance_rate if hasattr(summary, 'compliance_rate') else 0,
        tasks_missing_updates=summary.tasks_missing_updates if hasattr(summary, 'tasks_missing_updates') else 0,
        points_by_status=points_by_status,
    )
