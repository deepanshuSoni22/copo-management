"""
Service layer for COPO Management System.

This package contains business logic separated from views for better
maintainability and testability.
"""

from .attainment_service import AttainmentService
from .course_service import CourseService
from .enrollment_service import EnrollmentService
from .outcome_service import OutcomeService

__all__ = [
    'AttainmentService',
    'CourseService',
    'EnrollmentService',
    'OutcomeService',
]
