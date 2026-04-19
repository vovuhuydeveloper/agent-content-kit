"""
Path utilities — Centralized path resolution for the project.
"""

from pathlib import Path


def get_project_root() -> Path:
    """
    Get the project root directory.
    Resolves to the directory containing 'backend/' package.
    """
    # This file is at backend/core/path_utils.py
    # Project root is 2 levels up
    return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """Get data directory, creating if needed"""
    d = get_project_root() / "data"
    d.mkdir(exist_ok=True)
    return d


def get_jobs_dir() -> Path:
    """Get jobs directory"""
    d = get_data_dir() / "jobs"
    d.mkdir(exist_ok=True)
    return d
