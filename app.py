"""Direct entry point: `python app.py [args]` — same as the `japa` command.

Imports the package straight from src/, so it works even when the
editable install's .pth file is broken (macOS can mark venv .pth files
hidden, which Python 3.12+ then skips).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from japa.cli import main

if __name__ == "__main__":
    main()
