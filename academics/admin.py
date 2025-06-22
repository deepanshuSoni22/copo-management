# academics/admin.py
from django.contrib import admin
from .models import (
    AcademicYear, Department, ProgramOutcome, Course, CourseOutcome,
    COPOMapping, AssessmentType, Assessment, StudentMark,
    CourseOutcomeAttainment, ProgramOutcomeAttainment,
)
from users.models import UserProfile # Import UserProfile if needed for custom admin (e.g. Department HOD display)

# --- Academic Year Admin ---
@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('start_date',)
    ordering = ['-start_date']

# --- Department Admin ---
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_hod_username', 'get_hod_role')
    search_fields = ('name', 'hod__user__username')
    raw_id_fields = ('hod',) # Use a raw ID field for HOD for easier selection if many users
    autocomplete_fields = ['hod'] # For better UX with raw_id_fields (requires search_fields on UserProfile admin if custom)

    def get_hod_username(self, obj):
        return obj.hod.user.username if obj.hod else 'N/A'
    get_hod_username.short_description = 'HOD Username'

    def get_hod_role(self, obj):
        return obj.hod.get_role_display() if obj.hod else 'N/A'
    get_hod_role.short_description = 'HOD Role'

# --- Program Outcome Admin ---
@admin.register(ProgramOutcome)
class ProgramOutcomeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')
    search_fields = ('code', 'description')
    ordering = ['code']

# --- Course Admin ---
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department', 'academic_year', 'display_faculty')
    list_filter = ('department', 'academic_year', 'faculty')
    search_fields = ('code', 'name', 'department__name', 'academic_year__start_date__year') # Added year for search
    raw_id_fields = ('department', 'academic_year',) # Use raw_id for FKs
    filter_horizontal = ('faculty',) # For ManyToMany fields for better UI (uses a transfer widget)
    autocomplete_fields = ['department', 'academic_year'] # For better UX with raw_id_fields

    def display_faculty(self, obj):
        return ", ".join([str(f.user.username) for f in obj.faculty.all()])
    display_faculty.short_description = 'Faculty'

# --- Course Outcome Admin ---
@admin.register(CourseOutcome)
class CourseOutcomeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'course', 'get_course_department', 'get_course_academic_year')
    list_filter = ('course__department', 'course__academic_year', 'course')
    search_fields = ('code', 'description', 'course__code', 'course__name')
    raw_id_fields = ('course',)
    autocomplete_fields = ['course']

    def get_course_department(self, obj):
        return obj.course.department.name if obj.course.department else 'N/A'
    get_course_department.short_description = 'Course Department'

    def get_course_academic_year(self, obj):
        return f"{obj.course.academic_year.start_date.year}-{obj.course.academic_year.end_date.year}" if obj.course.academic_year else 'N/A'
    get_course_academic_year.short_description = 'Course Academic Year'

# --- CO-PO Mapping Admin ---
@admin.register(COPOMapping)
class COPOMappingAdmin(admin.ModelAdmin):
    list_display = ('course_outcome', 'program_outcome', 'get_correlation_level_display', 'get_course_code')
    list_filter = ('correlation_level', 'program_outcome', 'course_outcome__course__department', 'course_outcome__course__academic_year')
    search_fields = ('course_outcome__code', 'program_outcome__code', 'course_outcome__description', 'program_outcome__description')
    raw_id_fields = ('course_outcome', 'program_outcome')
    autocomplete_fields = ['course_outcome', 'program_outcome']

    def get_course_code(self, obj):
        return obj.course_outcome.course.code if obj.course_outcome and obj.course_outcome.course else 'N/A'
    get_course_code.short_description = 'Course Code'
    get_course_code.admin_order_field = 'course_outcome__course__code'


# --- Assessment Type Admin ---
@admin.register(AssessmentType)
class AssessmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ['name']

# --- Assessment Admin ---
@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'academic_year', 'assessment_type', 'max_marks', 'date', 'display_assesses_cos')
    list_filter = ('course__department', 'academic_year', 'assessment_type', 'course')
    search_fields = ('name', 'course__code', 'course__name', 'academic_year__start_date__year')
    raw_id_fields = ('course', 'academic_year', 'assessment_type')
    filter_horizontal = ('assesses_cos',) # For ManyToMany fields
    autocomplete_fields = ['course', 'academic_year', 'assessment_type']

    def display_assesses_cos(self, obj):
        return ", ".join([co.code for co in obj.assesses_cos.all()])
    display_assesses_cos.short_description = 'Assesses COs'

# --- Student Mark Admin ---
@admin.register(StudentMark)
class StudentMarkAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'student', 'marks_obtained', 'get_assessment_course_code', 'get_assessment_max_marks')
    list_filter = ('assessment__course__department', 'assessment__academic_year', 'assessment', 'student__profile__role') # Added filter by student role
    search_fields = ('student__username', 'assessment__name', 'assessment__course__code')
    raw_id_fields = ('assessment', 'student')
    autocomplete_fields = ['assessment', 'student']

    def get_assessment_course_code(self, obj):
        return obj.assessment.course.code if obj.assessment and obj.assessment.course else 'N/A'
    get_assessment_course_code.short_description = 'Course Code'
    get_assessment_course_code.admin_order_field = 'assessment__course__code'

    def get_assessment_max_marks(self, obj):
        return obj.assessment.max_marks if obj.assessment else 'N/A'
    get_assessment_max_marks.short_description = 'Max Marks'


# --- Course Outcome Attainment Admin ---
@admin.register(CourseOutcomeAttainment)
class CourseOutcomeAttainmentAdmin(admin.ModelAdmin):
    list_display = ('course_outcome', 'academic_year', 'attainment_percentage', 'get_course_code', 'get_department_name')
    list_filter = ('academic_year', 'course_outcome__course__department', 'course_outcome__course')
    search_fields = ('course_outcome__code', 'course_outcome__description', 'academic_year__start_date__year')
    raw_id_fields = ('course_outcome', 'academic_year')
    autocomplete_fields = ['course_outcome', 'academic_year']

    def get_course_code(self, obj):
        return obj.course_outcome.course.code if obj.course_outcome and obj.course_outcome.course else 'N/A'
    get_course_code.short_description = 'Course Code'
    get_course_code.admin_order_field = 'course_outcome__course__code'

    def get_department_name(self, obj):
        return obj.course_outcome.course.department.name if obj.course_outcome and obj.course_outcome.course and obj.course_outcome.course.department else 'N/A'
    get_department_name.short_description = 'Department'
    get_department_name.admin_order_field = 'course_outcome__course__department__name'


# --- Program Outcome Attainment Admin ---
@admin.register(ProgramOutcomeAttainment)
class ProgramOutcomeAttainmentAdmin(admin.ModelAdmin):
    list_display = ('program_outcome', 'academic_year', 'attainment_percentage')
    list_filter = ('academic_year', 'program_outcome')
    search_fields = ('program_outcome__code', 'program_outcome__description', 'academic_year__start_date__year')
    raw_id_fields = ('program_outcome', 'academic_year')
    autocomplete_fields = ['program_outcome', 'academic_year']