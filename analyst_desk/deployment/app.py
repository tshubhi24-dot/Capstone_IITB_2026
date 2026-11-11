"""Launch the Analyst Desk UI/API using the maintained dashboard module."""

if __name__ == "__main__":
    import runpy
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    runpy.run_module("analystdesk.ui.dashboard", run_name="__main__")
