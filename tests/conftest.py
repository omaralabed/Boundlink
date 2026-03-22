"""Test configuration for pytest"""

import sys
from pathlib import Path

# Add client directory to path
client_dir = Path(__file__).parent.parent
sys.path.insert(0, str(client_dir))
