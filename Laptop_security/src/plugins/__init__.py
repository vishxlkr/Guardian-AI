# src/plugins/__init__.py
"""Plugin system for extensible functionality"""

from .base_plugin import BasePlugin
from .example_alert import ExampleAlertPlugin

__all__ = ['BasePlugin','ExampleAlertPlugin']