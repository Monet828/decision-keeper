import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

FIXTURES = ROOT / "tests" / "fixtures"
ASSETS = FIXTURES / "assets"

__all__ = ["ROOT", "FIXTURES", "ASSETS"]
