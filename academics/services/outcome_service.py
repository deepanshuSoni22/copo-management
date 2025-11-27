"""
Outcome management service.

Handles all business logic related to Course Outcomes (CO), Program Outcomes (PO),
and CO-PO mappings.
"""

from django.db import transaction
from django.db.models import Prefetch, Q, Count
from django.core.exceptions import ValidationError
from decimal import Decimal

from academics.models import (
    CourseOutcome,
    ProgramOutcome,
    COPOMapping,
    Course,
    Department,
    AcademicYear,
)


class OutcomeService:
    """
    Service class for handling outcome-related business logic.
    
    Provides methods for managing Course Outcomes, Program Outcomes,
    and their mappings.
    """
    
    # CO-PO Correlation levels
    CORRELATION_NONE = 0
    CORRELATION_LOW = 1
    CORRELATION_MEDIUM = 2
    CORRELATION_HIGH = 3
    
    @staticmethod
    def get_course_outcomes_for_course(course):
        """
        Get all course outcomes for a specific course.
        
        Args:
            course: Course object
        
        Returns:
            QuerySet: CourseOutcome objects ordered by code
        """
        return CourseOutcome.objects.filter(
            course=course
        ).select_related('course').order_by('code')
    
    @staticmethod
    def get_program_outcomes_for_department(department):
        """
        Get all program outcomes for a specific department.
        
        Args:
            department: Department object
        
        Returns:
            QuerySet: ProgramOutcome objects ordered by code
        """
        return ProgramOutcome.objects.filter(
            department=department
        ).select_related('department').order_by('code')
    
    @staticmethod
    def get_copo_mappings_for_course(course):
        """
        Get all CO-PO mappings for a specific course.
        
        Args:
            course: Course object
        
        Returns:
            QuerySet: COPOMapping objects
        """
        return COPOMapping.objects.filter(
            course_outcome__course=course
        ).select_related(
            'course_outcome',
            'program_outcome__department'
        ).order_by('course_outcome__code', 'program_outcome__code')
    
    @staticmethod
    @transaction.atomic
    def create_course_outcome(course, code, description, rbt_level=None):
        """
        Create a new course outcome.
        
        Args:
            course: Course object
            code: CO code (e.g., 'CO1')
            description: CO description
            rbt_level: Optional Revised Bloom's Taxonomy level
        
        Returns:
            CourseOutcome object
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate code format
        if not code.upper().startswith('CO'):
            raise ValidationError("Course Outcome code must start with 'CO'")
        
        # Check for duplicates
        if CourseOutcome.objects.filter(course=course, code=code).exists():
            raise ValidationError(f"Course Outcome {code} already exists for this course")
        
        return CourseOutcome.objects.create(
            course=course,
            code=code,
            description=description,
            rbt_level=rbt_level
        )
    
    @staticmethod
    @transaction.atomic
    def create_program_outcome(department, code, description):
        """
        Create a new program outcome.
        
        Args:
            department: Department object
            code: PO code (e.g., 'PO1')
            description: PO description
        
        Returns:
            ProgramOutcome object
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate code format
        if not code.upper().startswith('PO') and not code.upper().startswith('PSO'):
            raise ValidationError("Program Outcome code must start with 'PO' or 'PSO'")
        
        # Check for duplicates
        if ProgramOutcome.objects.filter(department=department, code=code).exists():
            raise ValidationError(f"Program Outcome {code} already exists for this department")
        
        return ProgramOutcome.objects.create(
            department=department,
            code=code,
            description=description
        )
    
    @staticmethod
    @transaction.atomic
    def create_or_update_copo_mapping(course_outcome, program_outcome, correlation_level):
        """
        Create or update a CO-PO mapping.
        
        Args:
            course_outcome: CourseOutcome object
            program_outcome: ProgramOutcome object
            correlation_level: Integer (0-3)
        
        Returns:
            COPOMapping object
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate correlation level
        if correlation_level not in [0, 1, 2, 3]:
            raise ValidationError("Correlation level must be 0, 1, 2, or 3")
        
        # Validate that course department matches PO department
        if course_outcome.course.department != program_outcome.department:
            raise ValidationError("Course and Program Outcome must belong to the same department")
        
        mapping, created = COPOMapping.objects.update_or_create(
            course_outcome=course_outcome,
            program_outcome=program_outcome,
            defaults={'correlation_level': correlation_level}
        )
        
        return mapping
    
    @staticmethod
    @transaction.atomic
    def bulk_create_copo_mappings(course, mappings_data):
        """
        Create multiple CO-PO mappings for a course.
        
        Args:
            course: Course object
            mappings_data: List of dicts with keys: co_id, po_id, correlation_level
        
        Returns:
            dict: Results with success/failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'updated': 0,
            'messages': []
        }
        
        for mapping_data in mappings_data:
            try:
                co = CourseOutcome.objects.get(
                    id=mapping_data['co_id'],
                    course=course
                )
                po = ProgramOutcome.objects.get(
                    id=mapping_data['po_id'],
                    department=course.department
                )
                
                mapping, created = COPOMapping.objects.update_or_create(
                    course_outcome=co,
                    program_outcome=po,
                    defaults={'correlation_level': mapping_data['correlation_level']}
                )
                
                if created:
                    results['success'] += 1
                else:
                    results['updated'] += 1
            
            except CourseOutcome.DoesNotExist:
                results['failed'] += 1
                results['messages'].append(f"CO ID {mapping_data['co_id']} not found")
            except ProgramOutcome.DoesNotExist:
                results['failed'] += 1
                results['messages'].append(f"PO ID {mapping_data['po_id']} not found")
            except Exception as e:
                results['failed'] += 1
                results['messages'].append(str(e))
        
        return results
    
    @staticmethod
    def get_copo_mapping_matrix(course):
        """
        Get CO-PO mapping as a matrix for display.
        
        Args:
            course: Course object
        
        Returns:
            dict: Matrix data with COs, POs, and correlation values
        """
        course_outcomes = OutcomeService.get_course_outcomes_for_course(course)
        program_outcomes = OutcomeService.get_program_outcomes_for_department(course.department)
        
        # Build matrix
        matrix = {}
        for co in course_outcomes:
            matrix[co.code] = {
                'co': co,
                'mappings': {}
            }
            
            for po in program_outcomes:
                try:
                    mapping = COPOMapping.objects.get(
                        course_outcome=co,
                        program_outcome=po
                    )
                    matrix[co.code]['mappings'][po.code] = mapping.correlation_level
                except COPOMapping.DoesNotExist:
                    matrix[co.code]['mappings'][po.code] = 0
        
        return {
            'course_outcomes': list(course_outcomes),
            'program_outcomes': list(program_outcomes),
            'matrix': matrix
        }
    
    @staticmethod
    def validate_copo_mapping_completeness(course):
        """
        Check if all COs are mapped to at least one PO.
        
        Args:
            course: Course object
        
        Returns:
            dict: Validation results
        """
        course_outcomes = CourseOutcome.objects.filter(course=course)
        unmapped_cos = []
        
        for co in course_outcomes:
            mappings = COPOMapping.objects.filter(
                course_outcome=co,
                correlation_level__gt=0  # Only count non-zero mappings
            )
            
            if not mappings.exists():
                unmapped_cos.append(co.code)
        
        return {
            'is_complete': len(unmapped_cos) == 0,
            'total_cos': course_outcomes.count(),
            'unmapped_cos': unmapped_cos,
            'unmapped_count': len(unmapped_cos)
        }
    
    @staticmethod
    def get_co_coverage_for_po(program_outcome, academic_year=None):
        """
        Get all Course Outcomes mapped to a specific Program Outcome.
        
        Args:
            program_outcome: ProgramOutcome object
            academic_year: Optional AcademicYear object to filter by
        
        Returns:
            QuerySet: COPOMapping objects
        """
        mappings = COPOMapping.objects.filter(
            program_outcome=program_outcome,
            correlation_level__gt=0
        ).select_related(
            'course_outcome__course__semester__academic_department'
        )
        
        if academic_year:
            mappings = mappings.filter(
                course_outcome__course__semester__academic_department__academic_year=academic_year
            )
        
        return mappings.order_by('course_outcome__course__code', 'course_outcome__code')
    
    @staticmethod
    def get_po_coverage_for_co(course_outcome):
        """
        Get all Program Outcomes mapped to a specific Course Outcome.
        
        Args:
            course_outcome: CourseOutcome object
        
        Returns:
            QuerySet: COPOMapping objects
        """
        return COPOMapping.objects.filter(
            course_outcome=course_outcome,
            correlation_level__gt=0
        ).select_related('program_outcome').order_by('program_outcome__code')
    
    @staticmethod
    def get_outcome_statistics(course):
        """
        Get statistics about outcomes and mappings for a course.
        
        Args:
            course: Course object
        
        Returns:
            dict: Outcome statistics
        """
        cos = CourseOutcome.objects.filter(course=course)
        pos = ProgramOutcome.objects.filter(department=course.department)
        
        total_possible_mappings = cos.count() * pos.count()
        actual_mappings = COPOMapping.objects.filter(
            course_outcome__course=course,
            correlation_level__gt=0
        ).count()
        
        return {
            'total_cos': cos.count(),
            'total_pos': pos.count(),
            'total_possible_mappings': total_possible_mappings,
            'actual_mappings': actual_mappings,
            'mapping_coverage_percentage': (
                (actual_mappings / total_possible_mappings * 100)
                if total_possible_mappings > 0 else 0
            ),
            'cos_with_mappings': cos.annotate(
                mapping_count=Count('copo_mappings', filter=Q(copo_mappings__correlation_level__gt=0))
            ).filter(mapping_count__gt=0).count(),
        }
    
    @staticmethod
    def can_user_access_outcomes(user, course_or_department):
        """
        Check if a user can access outcomes for a course or department.
        
        Args:
            user: User object
            course_or_department: Course or Department object
        
        Returns:
            bool: True if user can access
        """
        user_profile = user.profile
        
        if user_profile.role == 'ADMIN' or user.is_superuser:
            return True
        
        if user_profile.role == 'HOD':
            from academics.models import AcademicDepartment
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
                
                if isinstance(course_or_department, Course):
                    return course_or_department.semester.academic_department == hod_academic_department
                elif isinstance(course_or_department, Department):
                    return course_or_department == hod_academic_department.department
            except AcademicDepartment.DoesNotExist:
                return False
        
        if user_profile.role == 'FACULTY':
            if isinstance(course_or_department, Course):
                return course_or_department in user_profile.taught_courses.all()
            elif isinstance(course_or_department, Department):
                return course_or_department == user_profile.department
        
        return False
