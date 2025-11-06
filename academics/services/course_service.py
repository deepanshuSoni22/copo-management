"""
Course management service.

Handles all business logic related to courses, semesters, and course plans.
"""

from django.db import transaction
from django.db.models import Q, Prefetch

from academics.models import (
    Course,
    Semester,
    CoursePlan,
    Department,
    AcademicDepartment,
    AcademicYear,
)
from users.models import UserProfile


class CourseService:
    """
    Service class for handling course-related business logic.
    
    Provides methods for course management, semester handling, and course plans.
    """
    
    @staticmethod
    def get_courses_for_user(user):
        """
        Get courses based on user role.
        
        Args:
            user: User object
        
        Returns:
            QuerySet: Filtered Course objects
        """
        user_profile = user.profile
        
        if user_profile.role == 'ADMIN' or user.is_superuser:
            return Course.objects.all().select_related(
                'department',
                'semester__academic_department__academic_year'
            ).order_by('-semester__academic_department__academic_year__start_date', 'code')
        
        elif user_profile.role == 'HOD':
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
                return Course.objects.filter(
                    semester__academic_department=hod_academic_department
                ).select_related(
                    'department',
                    'semester__academic_department__academic_year'
                ).order_by('-semester__academic_department__academic_year__start_date', 'code')
            except AcademicDepartment.DoesNotExist:
                return Course.objects.none()
        
        elif user_profile.role == 'FACULTY':
            return user_profile.taught_courses.all().select_related(
                'department',
                'semester__academic_department__academic_year'
            ).order_by('-semester__academic_department__academic_year__start_date', 'code')
        
        elif user_profile.role == 'STUDENT':
            return user_profile.enrolled_courses.all().select_related(
                'department',
                'semester__academic_department__academic_year'
            ).order_by('-semester__academic_department__academic_year__start_date', 'code')
        
        return Course.objects.none()
    
    @staticmethod
    def get_semesters_for_user(user):
        """
        Get semesters based on user role.
        
        Args:
            user: User object
        
        Returns:
            QuerySet: Filtered Semester objects
        """
        user_profile = user.profile
        
        if user_profile.role == 'ADMIN' or user.is_superuser:
            return Semester.objects.all().select_related(
                'academic_department__department',
                'academic_department__academic_year'
            ).order_by('-academic_department__academic_year__start_date', 'order')
        
        elif user_profile.role == 'HOD':
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
                return Semester.objects.filter(
                    academic_department=hod_academic_department
                ).select_related(
                    'academic_department__department',
                    'academic_department__academic_year'
                ).order_by('-academic_department__academic_year__start_date', 'order')
            except AcademicDepartment.DoesNotExist:
                return Semester.objects.none()
        
        return Semester.objects.none()
    
    @staticmethod
    def get_course_plans_for_user(user):
        """
        Get course plans based on user role.
        
        Args:
            user: User object
        
        Returns:
            QuerySet: Filtered CoursePlan objects
        """
        user_profile = user.profile
        
        course_plans = CoursePlan.objects.all().select_related(
            'course__semester__academic_department__academic_year',
            'course_coordinator__user'
        ).prefetch_related('instructors__user')
        
        if user_profile.role == 'ADMIN' or user.is_superuser:
            return course_plans.order_by(
                '-course__semester__academic_department__academic_year__start_date',
                'course__code'
            )
        
        elif user_profile.role == 'HOD':
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
                return course_plans.filter(
                    course__semester__academic_department=hod_academic_department
                ).order_by(
                    '-course__semester__academic_department__academic_year__start_date',
                    'course__code'
                )
            except AcademicDepartment.DoesNotExist:
                return CoursePlan.objects.none()
        
        elif user_profile.role == 'FACULTY':
            return course_plans.filter(
                Q(course_coordinator=user_profile) | Q(instructors=user_profile)
            ).distinct().order_by(
                '-course__semester__academic_department__academic_year__start_date',
                'course__code'
            )
        
        return CoursePlan.objects.none()
    
    @staticmethod
    def get_courses_by_department(department_id):
        """
        Get all courses for a specific department.
        
        Args:
            department_id: Department ID
        
        Returns:
            QuerySet: Course objects for the department
        """
        return Course.objects.filter(
            department_id=department_id
        ).select_related(
            'department',
            'semester__academic_department__academic_year'
        ).order_by('code')
    
    @staticmethod
    def can_user_access_course(user, course):
        """
        Check if a user can access a specific course.
        
        Args:
            user: User object
            course: Course object
        
        Returns:
            bool: True if user can access, False otherwise
        """
        user_profile = user.profile
        
        if user_profile.role == 'ADMIN' or user.is_superuser:
            return True
        
        if user_profile.role == 'HOD':
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
                return course.semester.academic_department == hod_academic_department
            except AcademicDepartment.DoesNotExist:
                return False
        
        if user_profile.role == 'FACULTY':
            return course in user_profile.taught_courses.all()
        
        if user_profile.role == 'STUDENT':
            return course in user_profile.enrolled_courses.all()
        
        return False
    
    @staticmethod
    def can_user_access_semester(user, semester):
        """
        Check if a user can access a specific semester.
        
        Args:
            user: User object
            semester: Semester object
        
        Returns:
            bool: True if user can access, False otherwise
        """
        user_profile = user.profile
        
        if user_profile.role == 'ADMIN' or user.is_superuser:
            return True
        
        if user_profile.role == 'HOD':
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
                return semester.academic_department == hod_academic_department
            except AcademicDepartment.DoesNotExist:
                return False
        
        return False
    
    @staticmethod
    def get_course_statistics(course):
        """
        Get statistics for a course.
        
        Args:
            course: Course object
        
        Returns:
            dict: Course statistics
        """
        return {
            'code': course.code,
            'name': course.name,
            'credits': course.credits,
            'enrolled_students': course.students.count(),
            'course_outcomes_count': course.course_outcomes.count(),
            'assessments_count': course.assessments.count(),
            'assignments_count': course.assignments.count(),
            'has_course_plan': hasattr(course, 'course_plan'),
        }
    
    @staticmethod
    @transaction.atomic
    def create_course_with_plan(course_data, plan_data, user):
        """
        Create a course along with its course plan in a transaction.
        
        Args:
            course_data: Dictionary of course fields
            plan_data: Dictionary of course plan fields
            user: User creating the course
        
        Returns:
            tuple: (Course object, CoursePlan object)
        """
        course = Course.objects.create(**course_data)
        
        plan_data['course'] = course
        if 'course_coordinator' not in plan_data:
            plan_data['course_coordinator'] = user.profile
        
        course_plan = CoursePlan.objects.create(**plan_data)
        
        return course, course_plan
    
    @staticmethod
    def get_available_faculty_for_department(department):
        """
        Get all faculty members for a specific department.
        
        Args:
            department: Department object
        
        Returns:
            QuerySet: UserProfile objects with FACULTY or HOD role
        """
        return UserProfile.objects.filter(
            department=department,
            role__in=['FACULTY', 'HOD']
        ).select_related('user').order_by('user__first_name', 'user__last_name')
    
    @staticmethod
    def get_students_enrolled_in_course(course):
        """
        Get all students enrolled in a course.
        
        Args:
            course: Course object
        
        Returns:
            QuerySet: UserProfile objects with STUDENT role
        """
        return course.students.select_related('user').order_by(
            'user__first_name',
            'user__last_name'
        )
