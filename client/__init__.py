"""Bondlink Client - Multi-WAN Bonding Router"""

__version__ = "1.0.0"
__author__ = "Bondlink Team"
__description__ = "Production-ready multi-WAN bonding router client"

from client.core.config import Config
from client.core.logger import setup_logging

__all__ = ["Config", "setup_logging"]
