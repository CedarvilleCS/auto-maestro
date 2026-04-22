"""util.py

This module provides shared utility helpers for the backend.

Key Features:
- clamp(): constrains a value within a min/max range.

"""


def clamp(value, min_val, max_val):
    return min(max_val, max(min_val, value))
