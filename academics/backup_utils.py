# academics/backup_utils.py
"""
Backup and restore utilities for COPO Management System.
Provides functionality for admins to backup and restore institutional data.
"""
import os
import json
from datetime import datetime
from django.core import serializers
from django.core.management import call_command
from django.conf import settings
from django.http import HttpResponse
from io import StringIO
import zipfile
from pathlib import Path


def create_backup(backup_type='full', selected_models=None):
    """
    Create a backup of the database.
    
    Args:
        backup_type: 'full' or 'selective'
        selected_models: List of model names to backup (for selective backup)
        
    Returns:
        tuple: (success: bool, filepath: str, message: str)
    """
    try:
        # Create backups directory if it doesn't exist
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'copo_backup_{timestamp}.json'
        backup_filepath = backup_dir / backup_filename
        
        # Determine which models to backup
        if backup_type == 'full':
            # Backup all models
            models_to_backup = [
                'academics.AcademicYear',
                'academics.Department',
                'academics.AcademicDepartment',
                'academics.Semester',
                'academics.ProgramOutcome',
                'academics.Course',
                'academics.CourseOutcome',
                'academics.COPOMapping',
                'academics.AssessmentType',
                'academics.Assessment',
                'academics.StudentMark',
                'academics.CourseOutcomeAttainment',
                'academics.ProgramOutcomeAttainment',
                'academics.CoursePlan',
                'academics.CourseObjective',
                'academics.WeeklyLessonPlan',
                'academics.CIAComponent',
                'academics.Rubric',
                'academics.RubricCriterion',
                'academics.Assignment',
                'academics.Submission',
                'academics.RubricScore',
                'academics.AuditLog',
                'users.UserProfile',
                'auth.User',
            ]
        else:
            models_to_backup = selected_models or []
        
        # Serialize data
        with open(backup_filepath, 'w', encoding='utf-8') as backup_file:
            call_command('dumpdata', *models_to_backup, 
                        indent=2, 
                        format='json',
                        stdout=backup_file,
                        natural_foreign=True,
                        natural_primary=True)
        
        # Create metadata file
        metadata = {
            'backup_type': backup_type,
            'timestamp': timestamp,
            'models': models_to_backup,
            'django_version': settings.VERSION if hasattr(settings, 'VERSION') else 'unknown',
            'database': settings.DATABASES['default']['ENGINE'].split('.')[-1],
        }
        
        metadata_filepath = backup_dir / f'copo_backup_{timestamp}_metadata.json'
        with open(metadata_filepath, 'w', encoding='utf-8') as meta_file:
            json.dump(metadata, meta_file, indent=2)
        
        file_size = os.path.getsize(backup_filepath) / (1024 * 1024)  # Size in MB
        message = f"Backup created successfully: {backup_filename} ({file_size:.2f} MB)"
        
        return True, str(backup_filepath), message
    
    except Exception as e:
        return False, '', f"Backup failed: {str(e)}"


def create_backup_download_response(backup_filepath):
    """
    Create an HTTP response for downloading a backup file.
    
    Args:
        backup_filepath: Path to the backup file
        
    Returns:
        HttpResponse: File download response
    """
    with open(backup_filepath, 'rb') as backup_file:
        response = HttpResponse(backup_file.read(), content_type='application/json')
        filename = os.path.basename(backup_filepath)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def create_backup_zip(backup_dir_path):
    """
    Create a ZIP archive containing backup files and metadata.
    
    Args:
        backup_dir_path: Path to the backups directory
        
    Returns:
        HttpResponse: ZIP file download response
    """
    from io import BytesIO
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f'copo_backup_package_{timestamp}.zip'
    
    # Create in-memory ZIP file
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        backup_dir = Path(backup_dir_path)
        
        # Add all JSON files in the backup directory
        for json_file in backup_dir.glob('*.json'):
            zip_file.write(json_file, json_file.name)
    
    zip_buffer.seek(0)
    
    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    
    return response


def restore_from_backup(backup_filepath, restore_mode='merge'):
    """
    Restore data from a backup file.
    
    Args:
        backup_filepath: Path to the backup JSON file
        restore_mode: 'merge' (add new data) or 'replace' (clear and restore)
        
    Returns:
        tuple: (success: bool, message: str, details: dict)
    """
    try:
        # Read backup file
        with open(backup_filepath, 'r', encoding='utf-8') as backup_file:
            data = json.load(backup_file)
        
        # Track restoration statistics
        stats = {
            'objects_created': 0,
            'objects_updated': 0,
            'objects_skipped': 0,
            'errors': []
        }
        
        # If replace mode, clear existing data (be very careful with this!)
        if restore_mode == 'replace':
            # This is dangerous - should only be used in controlled environments
            from django.core.management import call_command
            # Flush database (this will delete ALL data)
            # call_command('flush', '--no-input')
            # For safety, we'll NOT implement auto-flush. Admin must do manually.
            return False, "Replace mode requires manual database flush for safety.", stats
        
        # Deserialize and load data
        for obj in serializers.deserialize('json', json.dumps(data)):
            try:
                obj.save()
                stats['objects_created'] += 1
            except Exception as e:
                stats['errors'].append(f"Error saving {obj.object}: {str(e)}")
                stats['objects_skipped'] += 1
        
        message = (
            f"Restoration completed. "
            f"Created: {stats['objects_created']}, "
            f"Skipped: {stats['objects_skipped']}"
        )
        
        if stats['errors']:
            message += f" ({len(stats['errors'])} errors)"
        
        return True, message, stats
    
    except Exception as e:
        return False, f"Restoration failed: {str(e)}", {'errors': [str(e)]}


def list_available_backups(backup_dir=None):
    """
    List all available backup files.
    
    Args:
        backup_dir: Path to backups directory (optional)
        
    Returns:
        list: List of dictionaries containing backup information
    """
    if backup_dir is None:
        backup_dir = Path(settings.BASE_DIR) / 'backups'
    else:
        backup_dir = Path(backup_dir)
    
    if not backup_dir.exists():
        return []
    
    backups = []
    
    for json_file in sorted(backup_dir.glob('copo_backup_*.json'), reverse=True):
        # Skip metadata files
        if '_metadata.json' in json_file.name:
            continue
        
        file_stats = json_file.stat()
        
        # Try to load metadata if available
        metadata_file = json_file.parent / f"{json_file.stem}_metadata.json"
        metadata = None
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as mf:
                    metadata = json.load(mf)
            except:
                pass
        
        backup_info = {
            'filename': json_file.name,
            'filepath': str(json_file),
            'size_mb': file_stats.st_size / (1024 * 1024),
            'created_at': datetime.fromtimestamp(file_stats.st_ctime),
            'metadata': metadata
        }
        
        backups.append(backup_info)
    
    return backups


def delete_old_backups(days_to_keep=30, backup_dir=None):
    """
    Delete backup files older than specified days.
    
    Args:
        days_to_keep: Number of days to keep backups
        backup_dir: Path to backups directory (optional)
        
    Returns:
        tuple: (deleted_count: int, freed_space_mb: float)
    """
    from datetime import timedelta
    
    if backup_dir is None:
        backup_dir = Path(settings.BASE_DIR) / 'backups'
    else:
        backup_dir = Path(backup_dir)
    
    if not backup_dir.exists():
        return 0, 0
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    deleted_count = 0
    freed_space = 0
    
    for json_file in backup_dir.glob('copo_backup_*.json'):
        file_stats = json_file.stat()
        file_date = datetime.fromtimestamp(file_stats.st_ctime)
        
        if file_date < cutoff_date:
            file_size = file_stats.st_size
            json_file.unlink()
            
            # Also delete associated metadata file
            metadata_file = json_file.parent / f"{json_file.stem}_metadata.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            deleted_count += 1
            freed_space += file_size
    
    freed_space_mb = freed_space / (1024 * 1024)
    
    return deleted_count, freed_space_mb


def validate_backup_file(backup_filepath):
    """
    Validate a backup file before restoration.
    
    Args:
        backup_filepath: Path to the backup file
        
    Returns:
        tuple: (is_valid: bool, message: str, info: dict)
    """
    try:
        with open(backup_filepath, 'r', encoding='utf-8') as backup_file:
            data = json.load(backup_file)
        
        if not isinstance(data, list):
            return False, "Invalid backup format: Expected a JSON array", {}
        
        # Count objects by model
        model_counts = {}
        for item in data:
            model = item.get('model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        
        info = {
            'total_objects': len(data),
            'models': model_counts,
            'file_size_mb': os.path.getsize(backup_filepath) / (1024 * 1024)
        }
        
        return True, "Backup file is valid", info
    
    except json.JSONDecodeError:
        return False, "Invalid JSON format", {}
    except Exception as e:
        return False, f"Validation error: {str(e)}", {}


def export_backup_summary(backups):
    """
    Generate a summary report of all backups.
    
    Args:
        backups: List of backup information dictionaries
        
    Returns:
        str: Formatted summary text
    """
    if not backups:
        return "No backups available."
    
    summary = ["COPO Management System - Backup Summary", "=" * 50, ""]
    
    total_size = sum(b['size_mb'] for b in backups)
    summary.append(f"Total Backups: {len(backups)}")
    summary.append(f"Total Size: {total_size:.2f} MB")
    summary.append("")
    summary.append("Individual Backups:")
    summary.append("-" * 50)
    
    for backup in backups:
        summary.append(f"\nFilename: {backup['filename']}")
        summary.append(f"Created: {backup['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append(f"Size: {backup['size_mb']:.2f} MB")
        
        if backup['metadata']:
            summary.append(f"Type: {backup['metadata'].get('backup_type', 'unknown')}")
            summary.append(f"Models: {len(backup['metadata'].get('models', []))}")
    
    return "\n".join(summary)
