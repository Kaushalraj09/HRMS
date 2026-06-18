from pathlib import Path
import sys


# Allow `pytest` to import the backend app package without requiring
# developers to export PYTHONPATH manually before every run.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
