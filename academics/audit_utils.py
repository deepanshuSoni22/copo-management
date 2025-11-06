# academics/audit_utils.py
"""
Utility functions for audit logging system.
Provides helper functions to log user actions across the application.
"""
import json
from django.contrib.auth.models import User
from .models import AuditLog


def get_client_ip(request):
    """
    Extract client IP address from request.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: IP address of the client
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_action(user, action, model_name, obj=None, object_id=None, changes=None, request=None):
    """
    Create an audit log entry for a user action.
    
    Args:
        user: User object or None (for system actions)
        action: One of 'CREATE', 'UPDATE', 'DELETE', 'CALCULATE', 'EXPORT', 'IMPORT'
        model_name: Name of the affected model (string)
        obj: The affected object (optional, for getting repr)
        object_id: ID of the affected object (optional if obj is provided)
        changes: Dictionary of changes made (for UPDATE actions)
        request: HttpRequest object (optional, for IP logging)
        
    Returns:
        AuditLog: Created audit log entry
    """
    ip_address = None
    if request:
        ip_address = get_client_ip(request)
    
    object_repr = str(obj) if obj else ''
    if not object_id and obj:
        object_id = str(obj.pk) if hasattr(obj, 'pk') else None
    
    changes_json = None
    if changes:
        try:
            changes_json = json.dumps(changes, default=str)
        except (TypeError, ValueError):
            changes_json = str(changes)
    
    audit_entry = AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr[:500],  # Truncate if too long
        changes=changes_json,
        ip_address=ip_address
    )
    
    return audit_entry


def log_create(user, obj, request=None):
    """
    Log a CREATE action.
    
    Args:
        user: User who created the object
        obj: The created object
        request: HttpRequest object (optional)
    """
    return log_action(
        user=user,
        action='CREATE',
        model_name=obj.__class__.__name__,
        obj=obj,
        request=request
    )


def log_update(user, obj, changes=None, request=None):
    """
    Log an UPDATE action.
    
    Args:
        user: User who updated the object
        obj: The updated object
        changes: Dictionary of field changes (optional)
        request: HttpRequest object (optional)
    """
    return log_action(
        user=user,
        action='UPDATE',
        model_name=obj.__class__.__name__,
        obj=obj,
        changes=changes,
        request=request
    )


def log_delete(user, obj, request=None):
    """
    Log a DELETE action.
    
    Args:
        user: User who deleted the object
        obj: The object being deleted (before deletion)
        request: HttpRequest object (optional)
    """
    return log_action(
        user=user,
        action='DELETE',
        model_name=obj.__class__.__name__,
        obj=obj,
        request=request
    )


def log_calculation(user, model_name, description, request=None):
    """
    Log a CALCULATE action (for attainment calculations).
    
    Args:
        user: User who performed the calculation
        model_name: Name of the model being calculated
        description: Description of what was calculated
        request: HttpRequest object (optional)
    """
    return log_action(
        user=user,
        action='CALCULATE',
        model_name=model_name,
        object_id=description[:100],
        request=request
    )


def log_export(user, model_name, format_type, description=None, request=None):
    """
    Log an EXPORT action.
    
    Args:
        user: User who performed the export
        model_name: Name of the model being exported
        format_type: Export format (PDF, Excel, CSV)
        description: Additional description (optional)
        request: HttpRequest object (optional)
    """
    changes = {'format': format_type}
    if description:
        changes['description'] = description
    
    return log_action(
        user=user,
        action='EXPORT',
        model_name=model_name,
        changes=changes,
        request=request
    )


def log_import(user, model_name, description, request=None):
    """
    Log an IMPORT action.
    
    Args:
        user: User who performed the import
        model_name: Name of the model being imported
        description: Description of what was imported
        request: HttpRequest object (optional)
    """
    return log_action(
        user=user,
        action='IMPORT',
        model_name=model_name,
        object_id=description[:100],
        request=request
    )


def get_audit_logs_for_object(obj, limit=50):
    """
    Get audit logs for a specific object.
    
    Args:
        obj: The object to get logs for
        limit: Maximum number of logs to return
        
    Returns:
        QuerySet: Audit logs for the object
    """
    return AuditLog.objects.filter(
        model_name=obj.__class__.__name__,
        object_id=str(obj.pk)
    ).select_related('user')[:limit]


def get_recent_logs(user=None, days=7, limit=100):
    """
    Get recent audit logs, optionally filtered by user.
    
    Args:
        user: User object to filter by (optional)
        days: Number of days to look back
        limit: Maximum number of logs to return
        
    Returns:
        QuerySet: Recent audit logs
    """
    from django.utils import timezone
    from datetime import timedelta
    
    since = timezone.now() - timedelta(days=days)
    logs = AuditLog.objects.filter(timestamp__gte=since)
    
    if user:
        logs = logs.filter(user=user)
    
    return logs.select_related('user').order_by('-timestamp')[:limit]
