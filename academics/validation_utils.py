# academics/validation_utils.py
"""
Enhanced validation utilities for COPO Management System.
Provides strict validation rules to prevent data inconsistencies.
"""
from django.core.exceptions import ValidationError
from django.db.models import Q
import re


def validate_outcome_code(code, prefix=''):
    """
    Validate outcome code format.
    
    Args:
        code: The outcome code to validate (e.g., "CO1", "PO2")
        prefix: Expected prefix (optional, e.g., "CO", "PO")
        
    Raises:
        ValidationError: If code format is invalid
    """
    if not code:
        raise ValidationError("Outcome code cannot be empty.")
    
    # Check format: should be letters followed by numbers
    pattern = r'^[A-Z]{2,3}\d+$'
    if not re.match(pattern, code.upper()):
        raise ValidationError(
            f"Invalid outcome code format '{code}'. "
            "Expected format: 2-3 uppercase letters followed by numbers (e.g., CO1, PO12)"
        )
    
    # If prefix is specified, validate it
    if prefix:
        if not code.upper().startswith(prefix.upper()):
            raise ValidationError(
                f"Outcome code must start with '{prefix}'. Got: '{code}'"
            )


def validate_duplicate_outcome(model_class, code, course=None, department=None, exclude_pk=None):
    """
    Check for duplicate outcome codes within the same scope.
    
    Args:
        model_class: The model class (CourseOutcome or ProgramOutcome)
        code: The outcome code to check
        course: Course object (for CourseOutcome)
        department: Department object (for ProgramOutcome)
        exclude_pk: Primary key to exclude (when updating existing outcome)
        
    Raises:
        ValidationError: If duplicate is found
    """
    query = Q(code__iexact=code)  # Case-insensitive comparison
    
    if course:
        query &= Q(course=course)
    if department:
        query &= Q(department=department)
    
    duplicates = model_class.objects.filter(query)
    
    if exclude_pk:
        duplicates = duplicates.exclude(pk=exclude_pk)
    
    if duplicates.exists():
        scope = f"course '{course.code}'" if course else f"department '{department.name}'"
        raise ValidationError(
            f"An outcome with code '{code}' already exists for {scope}. "
            "Please use a unique code."
        )


def validate_correlation_level(level):
    """
    Validate CO-PO mapping correlation level.
    
    Args:
        level: The correlation level (0-3)
        
    Raises:
        ValidationError: If level is invalid
    """
    if level is None:
        raise ValidationError("Correlation level cannot be empty.")
    
    if not isinstance(level, int):
        try:
            level = int(level)
        except (TypeError, ValueError):
            raise ValidationError("Correlation level must be a number.")
    
    if level not in [0, 1, 2, 3]:
        raise ValidationError(
            f"Invalid correlation level '{level}'. "
            "Must be 0 (None), 1 (Low), 2 (Medium), or 3 (High)."
        )


def validate_assessment_marks(marks_obtained, max_marks):
    """
    Validate assessment marks.
    
    Args:
        marks_obtained: Marks obtained by student
        max_marks: Maximum possible marks
        
    Raises:
        ValidationError: If marks are invalid
    """
    if marks_obtained is None or max_marks is None:
        raise ValidationError("Marks cannot be empty.")
    
    try:
        marks_obtained = float(marks_obtained)
        max_marks = float(max_marks)
    except (TypeError, ValueError):
        raise ValidationError("Marks must be numeric values.")
    
    if marks_obtained < 0:
        raise ValidationError("Marks obtained cannot be negative.")
    
    if max_marks <= 0:
        raise ValidationError("Maximum marks must be greater than zero.")
    
    if marks_obtained > max_marks:
        raise ValidationError(
            f"Marks obtained ({marks_obtained}) cannot exceed maximum marks ({max_marks})."
        )


def validate_date_range(start_date, end_date, field_names=('start_date', 'end_date')):
    """
    Validate that end date is after start date.
    
    Args:
        start_date: Start date
        end_date: End date
        field_names: Tuple of field names for error messages
        
    Returns:
        dict: Dictionary of field errors (empty if valid)
    """
    errors = {}
    
    if start_date and end_date:
        if start_date >= end_date:
            errors[field_names[1]] = ValidationError(
                f"{field_names[1].replace('_', ' ').title()} must be after "
                f"{field_names[0].replace('_', ' ').title()}."
            )
    
    return errors


def validate_unique_together(model_class, field_dict, exclude_pk=None, error_message=None):
    """
    Generic validation for unique_together constraints.
    
    Args:
        model_class: The model class to check
        field_dict: Dictionary of field names and values to check
        exclude_pk: Primary key to exclude (when updating)
        error_message: Custom error message (optional)
        
    Raises:
        ValidationError: If duplicate combination exists
    """
    query = Q(**field_dict)
    duplicates = model_class.objects.filter(query)
    
    if exclude_pk:
        duplicates = duplicates.exclude(pk=exclude_pk)
    
    if duplicates.exists():
        if not error_message:
            fields_str = ', '.join(f"{k}='{v}'" for k, v in field_dict.items())
            error_message = (
                f"A {model_class.__name__} with {fields_str} already exists. "
                "This combination must be unique."
            )
        raise ValidationError(error_message)


def validate_percentage(value, field_name="percentage"):
    """
    Validate percentage value (0-100).
    
    Args:
        value: The percentage value
        field_name: Name of the field for error messages
        
    Raises:
        ValidationError: If percentage is invalid
    """
    if value is None:
        return  # Allow None for optional fields
    
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a numeric value.")
    
    if value < 0 or value > 100:
        raise ValidationError(
            f"{field_name} must be between 0 and 100. Got: {value}"
        )


def validate_non_negative(value, field_name="value"):
    """
    Validate that a numeric value is non-negative.
    
    Args:
        value: The numeric value
        field_name: Name of the field for error messages
        
    Raises:
        ValidationError: If value is negative
    """
    if value is None:
        return  # Allow None for optional fields
    
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a numeric value.")
    
    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative.")


def validate_credits(credits):
    """
    Validate course credits.
    
    Args:
        credits: Number of credits
        
    Raises:
        ValidationError: If credits are invalid
    """
    if credits is None:
        raise ValidationError("Credits cannot be empty.")
    
    try:
        credits = int(credits)
    except (TypeError, ValueError):
        raise ValidationError("Credits must be a whole number.")
    
    if credits < 1:
        raise ValidationError("Credits must be at least 1.")
    
    if credits > 20:
        raise ValidationError(
            f"Credits ({credits}) seem unusually high. Maximum allowed is 20."
        )


def validate_rubric_score(score, max_score, criterion_name=""):
    """
    Validate rubric criterion score.
    
    Args:
        score: Score given
        max_score: Maximum possible score
        criterion_name: Name of the criterion (for error messages)
        
    Raises:
        ValidationError: If score is invalid
    """
    if score is None:
        raise ValidationError(
            f"Score for {criterion_name or 'criterion'} cannot be empty."
        )
    
    try:
        score = int(score)
        max_score = int(max_score)
    except (TypeError, ValueError):
        raise ValidationError("Scores must be numeric values.")
    
    if score < 0:
        raise ValidationError(
            f"Score for {criterion_name or 'criterion'} cannot be negative."
        )
    
    if score > max_score:
        raise ValidationError(
            f"Score for {criterion_name or 'criterion'} ({score}) cannot exceed "
            f"maximum score ({max_score})."
        )


def validate_co_po_mapping_completeness(course):
    """
    Check if all course outcomes are mapped to program outcomes.
    
    Args:
        course: Course object
        
    Returns:
        dict: Dictionary with validation results
            {
                'is_complete': bool,
                'unmapped_cos': list of CourseOutcome objects,
                'message': str
            }
    """
    from .models import CourseOutcome, COPOMapping
    
    course_outcomes = CourseOutcome.objects.filter(course=course)
    unmapped_cos = []
    
    for co in course_outcomes:
        mappings = COPOMapping.objects.filter(
            course_outcome=co
        ).exclude(correlation_level=0)  # Exclude "None" mappings
        
        if not mappings.exists():
            unmapped_cos.append(co)
    
    is_complete = len(unmapped_cos) == 0
    
    if is_complete:
        message = f"All {course_outcomes.count()} course outcomes are mapped to program outcomes."
    else:
        message = (
            f"{len(unmapped_cos)} out of {course_outcomes.count()} course outcomes "
            f"are not mapped to any program outcomes."
        )
    
    return {
        'is_complete': is_complete,
        'unmapped_cos': unmapped_cos,
        'total_cos': course_outcomes.count(),
        'mapped_cos': course_outcomes.count() - len(unmapped_cos),
        'message': message
    }


def validate_assessment_co_linkage(assessment):
    """
    Validate that an assessment is linked to at least one course outcome.
    
    Args:
        assessment: Assessment object
        
    Raises:
        ValidationError: If assessment has no CO linkage
    """
    if not assessment.assesses_cos.exists():
        raise ValidationError(
            f"Assessment '{assessment.name}' must be linked to at least one Course Outcome. "
            "This linkage is required for accurate attainment calculation."
        )


def get_validation_summary(obj):
    """
    Get a comprehensive validation summary for an object.
    
    Args:
        obj: The object to validate (Course, Assessment, etc.)
        
    Returns:
        dict: Validation summary with warnings and errors
    """
    from .models import Course, Assessment
    
    summary = {
        'errors': [],
        'warnings': [],
        'info': []
    }
    
    if isinstance(obj, Course):
        # Check if course has outcomes
        if obj.course_outcomes.count() == 0:
            summary['warnings'].append("Course has no Course Outcomes defined.")
        
        # Check CO-PO mapping completeness
        mapping_status = validate_co_po_mapping_completeness(obj)
        if not mapping_status['is_complete']:
            summary['warnings'].append(mapping_status['message'])
        
        # Check if course has faculty assigned
        if obj.faculty.count() == 0:
            summary['warnings'].append("No faculty assigned to this course.")
        
        # Check if course has students enrolled
        if obj.students.count() == 0:
            summary['info'].append("No students enrolled in this course yet.")
    
    elif isinstance(obj, Assessment):
        # Check CO linkage
        if obj.assesses_cos.count() == 0:
            summary['errors'].append("Assessment is not linked to any Course Outcomes.")
        
        # Check if marks have been entered
        if obj.student_marks.count() == 0:
            summary['info'].append("No student marks entered for this assessment yet.")
    
    return summary
