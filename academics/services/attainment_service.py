"""
Attainment calculation service.

Handles all business logic related to CO and PO attainment calculations.
"""

from decimal import Decimal
from django.db.models import Sum, Avg, Count, Q
from django.db import transaction

from academics.models import (
    Course,
    CourseOutcome,
    CourseOutcomeAttainment,
    ProgramOutcome,
    ProgramOutcomeAttainment,
    COPOMapping,
    Assessment,
    StudentMark,
    Assignment,
    Submission,
    AcademicYear,
    Department,
)


class AttainmentService:
    """
    Service class for handling attainment calculations.
    
    Provides methods for calculating Course Outcome (CO) and Program Outcome (PO)
    attainment based on student performance data.
    """
    
    DEFAULT_SUCCESS_THRESHOLD = 60.0
    
    @staticmethod
    def calculate_co_attainment_for_course(
        course_obj, 
        academic_year_obj, 
        success_threshold=None
    ):
        """
        Calculate attainment for each Course Outcome (CO) of a given course
        for a specific academic year.
        
        Args:
            course_obj (Course): The course for which to calculate attainment
            academic_year_obj (AcademicYear): The academic year for calculation
            success_threshold (float): Percentage threshold for success (default: 60.0)
        
        Returns:
            dict: Results containing success status and calculated attainments
        """
        if success_threshold is None:
            success_threshold = AttainmentService.DEFAULT_SUCCESS_THRESHOLD
        
        course_outcomes = CourseOutcome.objects.filter(course=course_obj)
        results = {
            'success': True,
            'course': course_obj.code,
            'academic_year': str(academic_year_obj),
            'attainments': [],
            'errors': []
        }
        
        with transaction.atomic():
            for co in course_outcomes:
                try:
                    attainment_data = AttainmentService._calculate_single_co_attainment(
                        co, 
                        academic_year_obj, 
                        success_threshold
                    )
                    results['attainments'].append(attainment_data)
                except Exception as e:
                    results['errors'].append({
                        'co_code': co.code,
                        'error': str(e)
                    })
        
        return results
    
    @staticmethod
    def _calculate_single_co_attainment(co, academic_year_obj, success_threshold):
        """
        Calculate attainment for a single Course Outcome.
        
        Args:
            co (CourseOutcome): Course Outcome to calculate
            academic_year_obj (AcademicYear): Academic year for calculation
            success_threshold (float): Success percentage threshold
        
        Returns:
            dict: Attainment data for the CO
        """
        # Find all assignments that assess this CO for the given academic year
        assignments_for_co = Assignment.objects.filter(
            assesses_cos=co,
            course__semester__academic_department__academic_year=academic_year_obj
        )
        
        if not assignments_for_co.exists():
            return {
                'co_code': co.code,
                'attainment_percentage': 0,
                'students_evaluated': 0,
                'message': 'No assignments found'
            }
        
        # Get all graded submissions for these assignments
        submissions = Submission.objects.filter(
            assignment__in=assignments_for_co,
            marks_obtained__isnull=False
        ).values('student').annotate(
            total_marks=Sum('marks_obtained'),
            max_marks=Sum('assignment__max_marks')
        )
        
        if not submissions:
            return {
                'co_code': co.code,
                'attainment_percentage': 0,
                'students_evaluated': 0,
                'message': 'No graded submissions found'
            }
        
        students_above_threshold = 0
        total_students_with_grades = submissions.count()
        
        for sub in submissions:
            if sub['max_marks'] > 0:
                percentage = (sub['total_marks'] / sub['max_marks']) * 100
                if percentage >= success_threshold:
                    students_above_threshold += 1
        
        if total_students_with_grades > 0:
            attainment_percentage = (students_above_threshold / total_students_with_grades) * 100
        else:
            attainment_percentage = 0
        
        # Update or create the attainment record
        CourseOutcomeAttainment.objects.update_or_create(
            course_outcome=co,
            academic_year=academic_year_obj,
            defaults={'attainment_percentage': Decimal(str(attainment_percentage))}
        )
        
        return {
            'co_code': co.code,
            'attainment_percentage': round(attainment_percentage, 2),
            'students_evaluated': total_students_with_grades,
            'students_above_threshold': students_above_threshold,
            'message': 'Success'
        }
    
    @staticmethod
    def calculate_po_attainment_for_department(department_obj, academic_year_obj):
        """
        Calculate attainment for each Program Outcome (PO) of a given department
        for a specific academic year.
        
        Args:
            department_obj (Department): The department for calculation
            academic_year_obj (AcademicYear): The academic year for calculation
        
        Returns:
            dict: Results containing success status and calculated attainments
        """
        program_outcomes = ProgramOutcome.objects.filter(department=department_obj)
        results = {
            'success': True,
            'department': department_obj.name,
            'academic_year': str(academic_year_obj),
            'attainments': [],
            'errors': []
        }
        
        with transaction.atomic():
            for po in program_outcomes:
                try:
                    attainment_data = AttainmentService._calculate_single_po_attainment(
                        po, 
                        department_obj, 
                        academic_year_obj
                    )
                    results['attainments'].append(attainment_data)
                except Exception as e:
                    results['errors'].append({
                        'po_code': po.code,
                        'error': str(e)
                    })
        
        return results
    
    @staticmethod
    def _calculate_single_po_attainment(po, department_obj, academic_year_obj):
        """
        Calculate attainment for a single Program Outcome.
        
        Args:
            po (ProgramOutcome): Program Outcome to calculate
            department_obj (Department): Department context
            academic_year_obj (AcademicYear): Academic year for calculation
        
        Returns:
            dict: Attainment data for the PO
        """
        total_weighted_attainment = 0
        total_weight = 0
        
        # Find all COs in this department that are mapped to this PO
        mappings = COPOMapping.objects.filter(
            program_outcome=po,
            course_outcome__course__department=department_obj,
            course_outcome__attainments__academic_year=academic_year_obj
        ).select_related(
            'course_outcome',
            'program_outcome'
        ).prefetch_related(
            'course_outcome__attainments'
        )
        
        for mapping in mappings:
            try:
                # Get the attainment for the specific academic year
                attainment_qs = mapping.course_outcome.attainments.filter(
                    academic_year=academic_year_obj
                )
                
                if attainment_qs.exists():
                    attainment = attainment_qs.first()
                    if attainment.attainment_percentage is not None:
                        weight = mapping.correlation_level
                        total_weighted_attainment += float(attainment.attainment_percentage * weight)
                        total_weight += weight
            except Exception:
                continue
        
        if total_weight > 0:
            attainment_percentage = total_weighted_attainment / total_weight
        else:
            attainment_percentage = 0
        
        # Update or create the PO attainment record
        ProgramOutcomeAttainment.objects.update_or_create(
            program_outcome=po,
            academic_year=academic_year_obj,
            defaults={'attainment_percentage': Decimal(str(attainment_percentage))}
        )
        
        return {
            'po_code': po.code,
            'attainment_percentage': round(attainment_percentage, 2),
            'mappings_count': mappings.count(),
            'total_weight': total_weight,
            'message': 'Success'
        }
    
    @staticmethod
    def get_co_attainments_for_course(course_obj, academic_year_obj):
        """
        Get all CO attainments for a specific course and academic year.
        
        Args:
            course_obj (Course): The course
            academic_year_obj (AcademicYear): The academic year
        
        Returns:
            QuerySet: CourseOutcomeAttainment objects
        """
        return CourseOutcomeAttainment.objects.filter(
            course_outcome__course=course_obj,
            academic_year=academic_year_obj
        ).select_related(
            'course_outcome',
            'academic_year'
        ).order_by('course_outcome__code')
    
    @staticmethod
    def get_po_attainments_for_department(department_obj, academic_year_obj):
        """
        Get all PO attainments for a specific department and academic year.
        
        Args:
            department_obj (Department): The department
            academic_year_obj (AcademicYear): The academic year
        
        Returns:
            QuerySet: ProgramOutcomeAttainment objects
        """
        return ProgramOutcomeAttainment.objects.filter(
            program_outcome__department=department_obj,
            academic_year=academic_year_obj
        ).select_related(
            'program_outcome',
            'academic_year'
        ).order_by('program_outcome__code')
    
    @staticmethod
    def get_student_co_attainment(student, course, academic_year_obj):
        """
        Calculate individual student's attainment for course outcomes.
        
        Args:
            student: Student User object
            course: Course object
            academic_year_obj: AcademicYear object
        
        Returns:
            dict: Student's CO attainment data
        """
        course_outcomes = CourseOutcome.objects.filter(course=course)
        student_attainments = []
        
        for co in course_outcomes:
            assignments = Assignment.objects.filter(
                assesses_cos=co,
                course__semester__academic_department__academic_year=academic_year_obj
            )
            
            if not assignments.exists():
                continue
            
            submissions = Submission.objects.filter(
                assignment__in=assignments,
                student__user=student,
                marks_obtained__isnull=False
            ).aggregate(
                total_marks=Sum('marks_obtained'),
                max_marks=Sum('assignment__max_marks')
            )
            
            if submissions['max_marks'] and submissions['max_marks'] > 0:
                percentage = (submissions['total_marks'] / submissions['max_marks']) * 100
            else:
                percentage = 0
            
            student_attainments.append({
                'co_code': co.code,
                'co_description': co.description,
                'percentage': round(percentage, 2),
                'assignments_count': assignments.count()
            })
        
        return {
            'student': student.username,
            'course': course.code,
            'attainments': student_attainments
        }
