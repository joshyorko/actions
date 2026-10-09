"""Versioned Actions Runtime integration contracts.

This module is the narrow Core-to-Runtime integration surface used by the
separately distributed ``actions-runtime`` package. It preserves the existing
objects and behavior; it is not a general end-user convenience API.
"""

from actions._collect_actions import DEFAULT_EXCLUSION_PATTERNS
from actions._customization._extension_points import EPManagedParameters
from actions._customization._plugin_manager import PluginManager
from actions._lint_action import format_lint_results
from actions._managed_parameters import ManagedParameters

__all__ = [
    "DEFAULT_EXCLUSION_PATTERNS",
    "EPManagedParameters",
    "ManagedParameters",
    "PluginManager",
    "format_lint_results",
]
