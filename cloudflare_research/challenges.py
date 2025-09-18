"""Compatibility module for contract tests.

This module provides the expected class names that the contract tests are looking for.
It imports from the actual challenge module and provides aliases.
"""

# Import everything from the main challenge module
from .challenge import *

# Ensure the aliases are available at module level
from .challenge import ChallengeDetector, JavaScriptSolver