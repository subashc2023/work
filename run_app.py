"""Launcher script for the Query Suggestion System."""
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Run Streamlit
if __name__ == "__main__":
    import streamlit.web.cli as stcli

    # Path to the app
    app_path = src_path / "app.py"

    # Run streamlit
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port=8501",
        "--server.address=localhost",
    ]

    sys.exit(stcli.main())
