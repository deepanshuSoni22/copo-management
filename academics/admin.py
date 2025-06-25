# academics/admin.py
from django.contrib import admin
from .models import (
    AcademicYear,
    Department,
    ProgramOutcome,
    Course,
    CourseOutcome,
    COPOMapping,
    AssessmentType,
    Assessment,
    StudentMark,
    CourseOutcomeAttainment,
    ProgramOutcomeAttainment,
    Semester,
    AcademicDepartment
)
from users.models import (
    UserProfile,
)  # Import UserProfile if needed for custom admin (e.g. Department HOD display)


# --- Academic Year Admin ---
@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("start_date", "end_date", "is_current")
    list_filter = ("is_current",)
    search_fields = ("start_date",)
    ordering = ["-start_date"]

# --- NEW: AcademicDepartment Admin ---
@admin.register(AcademicDepartment)
class AcademicDepartmentAdmin(admin.ModelAdmin):
    list_display = ('department', 'academic_year', 'hod')
    list_filter = ('department', 'academic_year')
    search_fields = (
        'department__name',           # Search by linked Department's name
        'academic_year__start_date__year', # Search by linked Academic Year's start year
        'hod__user__username',        # Search by HOD's username
        'hod__user__first_name',      # Search by HOD's first name
        'hod__user__last_name',       # Search by HOD's last name
    )
    raw_id_fields = ('department', 'academic_year', 'hod') # For cleaner selection of FKs
    autocomplete_fields = ['department', 'academic_year', 'hod'] # Enable autocompletion for these fields
    ordering = ['-academic_year__start_date', 'department__name']


# --- NEW: Semester Admin ---
@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    # CHANGED: list_display now uses 'academic_department'
    list_display = ('name', 'academic_department', 'order')
    # CHANGED: list_filter now uses 'academic_department__academic_year'
    list_filter = ('academic_department__academic_year',) # Filter by year through academic_department
    # CHANGED: search_fields now uses 'academic_department__academic_year'
    search_fields = ('name', 'academic_department__department__name', 'academic_department__academic_year__start_date__year')
    # CHANGED: raw_id_fields and autocomplete_fields now use 'academic_department'
    raw_id_fields = ('academic_department',)
    autocomplete_fields = ['academic_department']
    ordering = ['-academic_department__academic_year__start_date', 'order']

# --- Department Admin ---
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "get_hod_username", "get_hod_role")
    search_fields = ("name", "hod__user__username")
    raw_id_fields = (
        "hod",
    )  # Use a raw ID field for HOD for easier selection if many users
    autocomplete_fields = [
        "hod"
    ]  # For better UX with raw_id_fields (requires search_fields on UserProfile admin if custom)

    def get_hod_username(self, obj):
        return obj.hod.user.username if obj.hod else "N/A"

    get_hod_username.short_description = "HOD Username"

    def get_hod_role(self, obj):
        return obj.hod.get_role_display() if obj.hod else "N/A"

    get_hod_role.short_description = "HOD Role"


# --- Program Outcome Admin ---
@admin.register(ProgramOutcome)
class ProgramOutcomeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")
    ordering = ["code"]


# --- Course Admin ---
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    # CHANGED: 'academic_year' replaced by 'semester' in list_display
    list_display = ("code", "name", "department", "semester", "display_faculty")
    # CHANGED: list_filter now uses 'semester__academic_department__academic_year' and 'semester'
    list_filter = ("department", "semester__academic_department__academic_year", "semester", "faculty")
    # CHANGED: search_fields now uses 'semester__academic_department__academic_year__start_date__year'
    search_fields = (
        "code",
        "name",
        "department__name",
        "semester__academic_department__academic_year__start_date__year",
    )
    # CHANGED: raw_id_fields now uses 'semester'
    raw_id_fields = (
        "department",
        "semester", # <-- Changed from "academic_year"
    )
    filter_horizontal = ("faculty",)
    # CHANGED: autocomplete_fields now uses 'semester'
    autocomplete_fields = [
        "department",
        "semester", # <-- Changed from "academic_year"
    ]

    def display_faculty(self, obj):
        return ", ".join([str(f.user.username) for f in obj.faculty.all()])

    display_faculty.short_description = "Faculty"


# --- Course Outcome Admin ---
@admin.register(CourseOutcome)
class CourseOutcomeAdmin(admin.ModelAdmin):
    # CHANGED: get_course_academic_year is now based on semester and academic_department
    list_display = (
        "code",
        "description",
        "course",
        "get_course_department",
        "get_course_academic_year",
    )
    # CHANGED: list_filter now uses 'course__semester__academic_department__academic_year'
    list_filter = ("course__department", "course__semester__academic_department__academic_year", "course")
    search_fields = ("code", "description", "course__code", "course__name")
    raw_id_fields = ("course",)
    autocomplete_fields = ["course"]

    def get_course_department(self, obj):
        return obj.course.department.name if obj.course.department else "N/A"

    get_course_department.short_description = "Course Department"

    def get_course_academic_year(self, obj):
        return (
            f"{obj.course.semester.academic_department.academic_year.start_date.year}-{obj.course.semester.academic_department.academic_year.end_date.year}"
            if obj.course and obj.course.semester and obj.course.semester.academic_department and obj.course.semester.academic_department.academic_year
            else "N/A"
        ) # CHANGED: Traverses through semester to academic_department to academic_year

    get_course_academic_year.short_description = "Course Academic Year"

# --- CO-PO Mapping Admin ---
@admin.register(COPOMapping)
class COPOMappingAdmin(admin.ModelAdmin):
    list_display = (
        "course_outcome",
        "program_outcome",
        "get_correlation_level_display",
        "get_course_code",
    )
    # CHANGED: list_filter now uses 'course_outcome__course__semester__academic_department__academic_year'
    list_filter = (
        "correlation_level",
        "program_outcome",
        "course_outcome__course__department",
        "course_outcome__course__semester__academic_department__academic_year", # <-- CHANGED
    )
    search_fields = (
        "course_outcome__code",
        "program_outcome__code",
        "course_outcome__description",
        "program_outcome__description",
    )
    raw_id_fields = ("course_outcome", "program_outcome")
    autocomplete_fields = ["course_outcome", "program_outcome"]

    def get_course_code(self, obj):
        return (
            obj.course_outcome.course.code
            if obj.course_outcome and obj.course_outcome.course
            else "N/A"
        )

    get_course_code.short_description = "Course Code"
    get_course_code.admin_order_field = "course_outcome__course__code"


# --- Assessment Type Admin ---
@admin.register(AssessmentType)
class AssessmentTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ["name"]


# --- Assessment Admin ---
@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "course",
        "academic_year", # <-- This is direct FK, keep as is
        "assessment_type",
        "max_marks",
        "date",
        "display_assesses_cos",
    )
    # list_filter uses 'academic_year', which is direct FK, keep as is
    list_filter = ("course__department", "academic_year", "assessment_type", "course")
    search_fields = (
        "name",
        "course__code",
        "course__name",
        "academic_year__start_date__year", # <-- This is direct FK, keep as is
    )
    raw_id_fields = ("course", "academic_year", "assessment_type") # <-- Keep academic_year here
    filter_horizontal = ("assesses_cos",)
    autocomplete_fields = ["course", "academic_year", "assessment_type"] # <-- Keep academic_year here

    def display_assesses_cos(self, obj):
        return ", ".join([co.code for co in obj.assesses_cos.all()])

    display_assesses_cos.short_description = "Assesses COs"


# --- Student Mark Admin ---
@admin.register(StudentMark)
class StudentMarkAdmin(admin.ModelAdmin):
    list_display = (
        "assessment",
        "student",
        "marks_obtained",
        "get_assessment_course_code",
        "get_assessment_max_marks",
    )
    # list_filter: 'assessment__academic_year' is direct, keep as is
    list_filter = (
        "assessment__course__department",
        "assessment__academic_year",
        "assessment",
        "student__profile__role",
    )
    search_fields = (
        "student__username",
        "assessment__name",
        "assessment__course__code",
    )
    raw_id_fields = ("assessment", "student")
    autocomplete_fields = ["assessment", "student"]

    def get_assessment_course_code(self, obj):
        return (
            obj.assessment.course.code
            if obj.assessment and obj.assessment.course
            else "N/A"
        )

    get_assessment_course_code.short_description = "Course Code"
    get_assessment_course_code.admin_order_field = "assessment__course__code"

    def get_assessment_max_marks(self, obj):
        return obj.assessment.max_marks if obj.assessment else "N/A"

    get_assessment_max_marks.short_description = "Max Marks"


# --- Course Outcome Attainment Admin ---
@admin.register(CourseOutcomeAttainment)
class CourseOutcomeAttainmentAdmin(admin.ModelAdmin):
    list_display = (
        "course_outcome",
        "academic_year", # <-- This is direct FK, keep as is
        "attainment_percentage",
        "get_course_code",
        "get_department_name",
    )
    # CHANGED: list_filter now uses 'course_outcome__course__semester__academic_department__academic_year'
    list_filter = (
        "academic_year",
        "course_outcome__course__department",
        "course_outcome__course__semester__academic_department__academic_year", # <-- CHANGED
        "course_outcome__course",
    )
    # CHANGED: search_fields now uses 'semester__academic_department__academic_year__start_date__year' for Course related part
    search_fields = (
        "course_outcome__code",
        "course_outcome__description",
        "academic_year__start_date__year", # <-- This is direct FK, keep as is
    )
    raw_id_fields = ("course_outcome", "academic_year") # Keep AY
    autocomplete_fields = ["course_outcome", "academic_year"] # Keep AY

    def get_course_code(self, obj):
        return (
            obj.course_outcome.course.code
            if obj.course_outcome and obj.course_outcome.course
            else "N/A"
        )

    get_course_code.short_description = "Course Code"
    get_course_code.admin_order_field = "course_outcome__course__code"

    def get_department_name(self, obj):
        return (
            obj.course_outcome.course.department.name
            if obj.course_outcome
            and obj.course_outcome.course
            and obj.course_outcome.course.department
            else "N/A"
        )

    get_department_name.short_description = "Department"
    get_department_name.admin_order_field = "course_outcome__course__department__name"


# --- Program Outcome Attainment Admin ---
@admin.register(ProgramOutcomeAttainment)
class ProgramOutcomeAttainmentAdmin(admin.ModelAdmin):
    list_display = ("program_outcome", "academic_year", "attainment_percentage")
    list_filter = ("academic_year", "program_outcome") # Keep AY
    search_fields = (
        "program_outcome__code",
        "program_outcome__description",
        "academic_year__start_date__year", # Keep AY
    )
    raw_id_fields = ("program_outcome", "academic_year") # Keep AY
    autocomplete_fields = ["program_outcome", "academic_year"] # Keep AY
