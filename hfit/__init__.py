#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hfit Module

Provides functionality to translate HTML files while preserving structure.
"""

# Expose the core translation function as the primary API
from .core import run_translation

# Optionally expose lower-level components if needed for advanced usage
# from .translation_services import get_translation_service, list_available_translation_services
# from .html_processor import HTMLProcessor

# Define package version (optional but good practice)
__version__ = "0.1.0"

# The rest of the original file content remains unchanged 