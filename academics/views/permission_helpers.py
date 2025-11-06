"""
Permission helper functions for role-based access control.

These functions are used throughout the application to check user permissions
based on their role (ADMIN, HOD, FACULTY, STUDENT).
"""


def is_admin(user):
    """
    Check if user is an ADMIN.
    
    Args:
        user: User object
    
    Returns:
        bool: True if user is authenticated and has ADMIN role
    """
    return user.is_authenticated and user.profile.role == "ADMIN"


def is_hod(user):
    """
    Check if user is a Head of Department (HOD).
    
    Args:
        user: User object
    
    Returns:
        bool: True if user is authenticated and has HOD role
    """
    return user.is_authenticated and user.profile.role == "HOD"


def is_faculty(user):
    """
    Check if user is FACULTY or HOD (both have faculty permissions).
    
    Args:
        user: User object
    
    Returns:
        bool: True if user is authenticated and has FACULTY or HOD role
    """
    return user.is_authenticated and user.profile.role in ['FACULTY', 'HOD']


def is_student(user):
    """
    Check if user is a STUDENT.
    
    Args:
        user: User object
    
    Returns:
        bool: True if user is authenticated and has STUDENT role
    """
    return user.is_authenticated and user.profile.role == "STUDENT"


def is_admin_or_superuser(user):
    """
    Check if user is ADMIN or Django superuser.
    
    Args:
        user: User object
    
    Returns:
        bool: True if user is superuser or has ADMIN role
    """
    return user.is_superuser or (user.is_authenticated and user.profile.role == "ADMIN")


def is_admin_or_hod(user):
    """
    Check if user is ADMIN or HOD.
    
    Args:
        user: User object
    
    Returns:
        bool: True if user is authenticated and has ADMIN or HOD role, or is superuser
    """
    return user.is_authenticated and (
        user.is_superuser or user.profile.role in ["ADMIN", "HOD"]
    )


def is_admin_or_hod_or_faculty(user):
    """
    Check if user is ADMIN, HOD, or FACULTY.
    
    Args:
        user: User object
    
    Returns:
        bool: True if user is authenticated and has ADMIN, HOD, or FACULTY role, or is superuser
    """
    return user.is_authenticated and (
        user.is_superuser or user.profile.role in ["ADMIN", "HOD", "FACULTY"]
    )
