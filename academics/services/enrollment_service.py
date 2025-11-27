"""
Student enrollment service.

Handles all business logic related to student enrollment and course registration.
"""

from django.db import transaction
from django.db.models import Count, Q
from django.core.exceptions import ValidationError
import csv
from io import StringIO

from academics.models import (
    Course,
    AcademicYear,
    Department,
)
from users.models import UserProfile
from django.contrib.auth.models import User


class EnrollmentService:
    """
    Service class for handling student enrollment operations.
    
    Provides methods for enrolling students in courses, bulk operations,
    and enrollment validation.
    """
    
    @staticmethod
    def enroll_student(student_profile, course):
        """
        Enroll a single student in a course.
        
        Args:
            student_profile: UserProfile object of the student
            course: Course object
        
        Returns:
            dict: Status and message
        
        Raises:
            ValidationError: If enrollment validation fails
        """
        if student_profile.role != 'STUDENT':
            raise ValidationError("Only students can be enrolled in courses.")
        
        if course in student_profile.enrolled_courses.all():
            return {
                'success': False,
                'message': f'{student_profile.user.username} is already enrolled in {course.code}'
            }
        
        student_profile.enrolled_courses.add(course)
        
        return {
            'success': True,
            'message': f'{student_profile.user.username} enrolled in {course.code} successfully'
        }
    
    @staticmethod
    def unenroll_student(student_profile, course):
        """
        Unenroll a single student from a course.
        
        Args:
            student_profile: UserProfile object of the student
            course: Course object
        
        Returns:
            dict: Status and message
        """
        if course not in student_profile.enrolled_courses.all():
            return {
                'success': False,
                'message': f'{student_profile.user.username} is not enrolled in {course.code}'
            }
        
        student_profile.enrolled_courses.remove(course)
        
        return {
            'success': True,
            'message': f'{student_profile.user.username} unenrolled from {course.code} successfully'
        }
    
    @staticmethod
    @transaction.atomic
    def bulk_enroll_students(student_profiles, course):
        """
        Enroll multiple students in a course.
        
        Args:
            student_profiles: List or QuerySet of UserProfile objects
            course: Course object
        
        Returns:
            dict: Enrollment results with success/failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'already_enrolled': 0,
            'messages': []
        }
        
        for student_profile in student_profiles:
            if student_profile.role != 'STUDENT':
                results['failed'] += 1
                results['messages'].append(
                    f'{student_profile.user.username} is not a student'
                )
                continue
            
            if course in student_profile.enrolled_courses.all():
                results['already_enrolled'] += 1
                results['messages'].append(
                    f'{student_profile.user.username} already enrolled'
                )
                continue
            
            try:
                student_profile.enrolled_courses.add(course)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['messages'].append(
                    f'{student_profile.user.username}: {str(e)}'
                )
        
        return results
    
    @staticmethod
    @transaction.atomic
    def bulk_unenroll_students(student_profiles, course):
        """
        Unenroll multiple students from a course.
        
        Args:
            student_profiles: List or QuerySet of UserProfile objects
            course: Course object
        
        Returns:
            dict: Unenrollment results with success/failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'not_enrolled': 0,
            'messages': []
        }
        
        for student_profile in student_profiles:
            if course not in student_profile.enrolled_courses.all():
                results['not_enrolled'] += 1
                results['messages'].append(
                    f'{student_profile.user.username} not enrolled'
                )
                continue
            
            try:
                student_profile.enrolled_courses.remove(course)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['messages'].append(
                    f'{student_profile.user.username}: {str(e)}'
                )
        
        return results
    
    @staticmethod
    def get_enrolled_students(course):
        """
        Get all students enrolled in a specific course.
        
        Args:
            course: Course object
        
        Returns:
            QuerySet: UserProfile objects of enrolled students
        """
        return course.students.filter(role='STUDENT').select_related('user').order_by(
            'user__first_name',
            'user__last_name'
        )
    
    @staticmethod
    def get_unenrolled_students(course, department=None):
        """
        Get all students not enrolled in a specific course.
        
        Args:
            course: Course object
            department: Optional Department object to filter by
        
        Returns:
            QuerySet: UserProfile objects of unenrolled students
        """
        enrolled_student_ids = course.students.values_list('id', flat=True)
        
        unenrolled = UserProfile.objects.filter(
            role='STUDENT'
        ).exclude(
            id__in=enrolled_student_ids
        ).select_related('user')
        
        if department:
            unenrolled = unenrolled.filter(department=department)
        
        return unenrolled.order_by('user__first_name', 'user__last_name')
    
    @staticmethod
    def get_student_courses(student_profile):
        """
        Get all courses a student is enrolled in.
        
        Args:
            student_profile: UserProfile object
        
        Returns:
            QuerySet: Course objects
        """
        return student_profile.enrolled_courses.all().select_related(
            'department',
            'semester__academic_department__academic_year'
        ).order_by('-semester__academic_department__academic_year__start_date', 'code')
    
    @staticmethod
    def get_enrollment_statistics(course):
        """
        Get enrollment statistics for a course.
        
        Args:
            course: Course object
        
        Returns:
            dict: Enrollment statistics
        """
        enrolled_students = course.students.filter(role='STUDENT')
        
        return {
            'total_enrolled': enrolled_students.count(),
            'by_department': enrolled_students.values(
                'department__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count'),
        }
    
    @staticmethod
    @transaction.atomic
    def process_csv_enrollment(csv_file, course):
        """
        Process CSV file for bulk enrollment.
        
        CSV format: username or email in first column
        
        Args:
            csv_file: File object
            course: Course object
        
        Returns:
            dict: Processing results with success/failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'already_enrolled': 0,
            'not_found': 0,
            'not_student': 0,
            'messages': []
        }
        
        try:
            # Read CSV file
            csv_content = csv_file.read().decode('utf-8')
            csv_reader = csv.reader(StringIO(csv_content))
            
            # Skip header if present
            next(csv_reader, None)
            
            for row in csv_reader:
                if not row or not row[0].strip():
                    continue
                
                identifier = row[0].strip()
                
                # Try to find user by username or email
                try:
                    user = User.objects.get(
                        Q(username=identifier) | Q(email=identifier)
                    )
                except User.DoesNotExist:
                    results['not_found'] += 1
                    results['messages'].append(
                        f'{identifier}: User not found'
                    )
                    continue
                except User.MultipleObjectsReturned:
                    results['failed'] += 1
                    results['messages'].append(
                        f'{identifier}: Multiple users found'
                    )
                    continue
                
                student_profile = user.profile
                
                # Check if user is a student
                if student_profile.role != 'STUDENT':
                    results['not_student'] += 1
                    results['messages'].append(
                        f'{user.username}: Not a student'
                    )
                    continue
                
                # Check if already enrolled
                if course in student_profile.enrolled_courses.all():
                    results['already_enrolled'] += 1
                    results['messages'].append(
                        f'{user.username}: Already enrolled'
                    )
                    continue
                
                # Enroll student
                try:
                    student_profile.enrolled_courses.add(course)
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['messages'].append(
                        f'{user.username}: {str(e)}'
                    )
        
        except Exception as e:
            results['messages'].append(f'CSV processing error: {str(e)}')
        
        return results
    
    @staticmethod
    def validate_enrollment(student_profile, course):
        """
        Validate if a student can be enrolled in a course.
        
        Args:
            student_profile: UserProfile object
            course: Course object
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if student_profile.role != 'STUDENT':
            return False, "Only students can be enrolled in courses"
        
        if course in student_profile.enrolled_courses.all():
            return False, f"Student already enrolled in {course.code}"
        
        # Add additional validation logic here if needed
        # For example: check for schedule conflicts, prerequisites, etc.
        
        return True, None
    
    @staticmethod
    def can_user_manage_enrollment(user, course):
        """
        Check if a user can manage enrollment for a course.
        
        Args:
            user: User object
            course: Course object
        
        Returns:
            bool: True if user can manage enrollment
        """
        user_profile = user.profile
        
        if user_profile.role == 'ADMIN' or user.is_superuser:
            return True
        
        if user_profile.role == 'HOD':
            # Import here to avoid circular import
            from academics.models import AcademicDepartment
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
                return course.semester.academic_department == hod_academic_department
            except AcademicDepartment.DoesNotExist:
                return False
        
        if user_profile.role == 'FACULTY':
            return course in user_profile.taught_courses.all()
        
        return False
