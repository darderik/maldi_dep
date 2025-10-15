#!/usr/bin/env python3
"""
MALDI Sample Preparation - Web App Launcher

Run this script to start the Streamlit web interface.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Launch the Streamlit web app."""
    try:
        # Check if we're in the right directory
        webapp_dir = Path(__file__).parent / "webapp"
        entry_file = webapp_dir / "entry.py"

        if not entry_file.exists():
            print("Error: entry.py not found in webapp directory")
            sys.exit(1)

        # Change to webapp directory and run streamlit
        print("Starting MALDI Sample Preparation Web App...")
        print(f"Launching: streamlit run {entry_file}")

        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(entry_file),
            "--server.headless", "true",
            "--server.port", "8501"
        ], cwd=str(webapp_dir))

    except KeyboardInterrupt:
        print("\nWeb app stopped by user.")
    except Exception as e:
        print(f"Error starting web app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
