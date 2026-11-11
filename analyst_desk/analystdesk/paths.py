"""Stable application paths shared by relocated components."""

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = APP_ROOT / ".runtime"
