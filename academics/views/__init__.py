"""
Views package for academics app.

This package provides a modular view structure for better organization and maintainability.

IMPORTANT: During refactoring, we import all legacy views from views_legacy.py
(the renamed views.py) to maintain backward compatibility. As functions are migrated
to modular files, they are imported from those files instead.
"""

# Import permission helpers from the new modular structure
from .permission_helpers import (
    is_admin,
    is_hod,
    is_faculty,
    is_student,
    is_admin_or_superuser,
    is_admin_or_hod,
    is_admin_or_hod_or_faculty,
)

# Import all views from the legacy views_legacy.py (renamed from views.py)
# This maintains backward compatibility while we refactor
from ..views_legacy import *

# The above import brings in all view functions, but we override the permission helpers
# since they've been migrated to the modular structure

__all__ = [
    # Permission helpers (migrated to modular structure)
    'is_admin',
    'is_hod',
    'is_faculty',
    'is_student',
    'is_admin_or_superuser',
    'is_admin_or_hod',
    'is_admin_or_hod_or_faculty',
    # All other views imported from views_legacy.py via wildcard import
    # TODO: As views are migrated, explicitly list them here and remove from wildcard import
]
