"""The grouped launcher must find the application independently of the caller's cwd."""

import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from analystdesk.paths import APP_ROOT


class ApplicationLauncherTests(unittest.TestCase):
    def test_launch_from_another_directory_finds_dashboard_without_starting_server(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp, patch.object(sys, "path", list(sys.path)), \
             patch("runpy.run_module") as launch:
            try:
                os.chdir(tmp)
                runpy.run_path(str(APP_ROOT / "deployment" / "app.py"), run_name="__main__")
                self.assertEqual(Path(sys.path[0]), APP_ROOT)
                launch.assert_called_once_with("analystdesk.ui.dashboard", run_name="__main__")
            finally:
                os.chdir(previous)
