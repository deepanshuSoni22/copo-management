# academics/models.py
from django.db import models
from users.models import UserProfile  # Import UserProfile from the users app
from django.contrib.auth.models import User  # <--- ADD THIS LINE


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # hod = models.OneToOneField(
    #     UserProfile,
    #     on_delete=models.SET_NULL,  # If HOD is deleted, department remains but HOD field becomes null
    #     related_name="headed_department",
    #     null=True,
    #     blank=True,
    #     limit_choices_to={
    #         "role__in": ["HOD", "FACULTY"]
    #     },  # This will show both HODs and Faculty
    #     verbose_name="Head of Department",
    # )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"


class AcademicYear(models.Model):
    start_date = models.DateField(unique=True)
    end_date = models.DateField(unique=True)
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return f"Academic Year: {self.start_date.year}-{self.end_date.year}"

    class Meta:
        verbose_name = "Academic Year"
        verbose_name_plural = "Academic Years"
        ordering = ["-start_date"]  # Order by latest academic year first


# --- NEW: AcademicDepartment Model ---
class AcademicDepartment(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='academic_departments'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='academic_departments'
    )
    # HOD is now assigned to an AcademicDepartment instance for a specific year
    hod = models.OneToOneField(
        UserProfile,
        on_delete=models.SET_NULL,
        related_name='academic_department_headed', # New related_name for clarity
        null=True, blank=True,
        limit_choices_to={'role__in': ['HOD', 'FACULTY']}, # HODs or Faculty can be HODs
        verbose_name="Head of Department (for this Academic Year)"
    )

    def __str__(self):
        hod_info = f" (HOD: {self.hod.user.username})" if self.hod else ""
        return f"{self.department.name} - {self.academic_year.start_date.year}-{self.academic_year.end_date.year}{hod_info}"

    class Meta:
        verbose_name = "Academic Department"
        verbose_name_plural = "Academic Departments"
        # A department can only exist once per academic year
        unique_together = ('department', 'academic_year')
        ordering = ['-academic_year__start_date', 'department__name']


class Semester(models.Model):
    name = models.CharField(max_length=100, help_text="e.g., 1st Semester, Spring 2024")
    # CHANGED: academic_year replaced by academic_department
    academic_department = models.ForeignKey( # NEW: Link to AcademicDepartment
        AcademicDepartment,
        on_delete=models.CASCADE,
        related_name='semesters',
        null=True, 
        blank=True
    )
    order = models.PositiveIntegerField(default=0, help_text="Order of the semester within the academic year")

    def __str__(self):
        # Update __str__ to reflect the new linkage
        return f"{self.name} ({self.academic_department.department.name} - {self.academic_department.academic_year.start_date.year}-{self.academic_department.academic_year.end_date.year})"

    class Meta:
        verbose_name = "Semester"
        verbose_name_plural = "Semesters"
        # Update unique_together to use academic_department
        unique_together = ('name', 'academic_department') # Semester name must be unique per academic_department
        # Update ordering to use academic_department's year and order
        ordering = ['-academic_department__academic_year__start_date', 'order']




class ProgramOutcome(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="e.g., PO1, PO2")
    description = models.TextField()

    def __str__(self):
        return f"{self.code}: {self.description[:50]}..."  # Display first 50 chars of description

    class Meta:
        verbose_name = "Program Outcome"
        verbose_name_plural = "Program Outcomes"
        ordering = ["code"]  # Order by code (e.g., PO1, PO2)


class Course(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, help_text="e.g., CS101, BA203")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    # Many-to-Many relationship for faculty, as a course can have multiple faculty over time/sections
    # and a faculty can teach multiple courses. Limit to FACULTY role.
    faculty = models.ManyToManyField(
        UserProfile,
        related_name="taught_courses",
        limit_choices_to={"role": "FACULTY"},
        blank=True,
    )
    # A course is usually offered in a specific academic year
    # Changed: A course is now linked to a Semester
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE, # If semester deleted, courses within it are deleted
        related_name='courses',
        null=True, blank=True # Allow courses not yet assigned to a semester initially
    )

    def __str__(self):
        if self.semester and self.semester.academic_department and self.semester.academic_department.academic_year:
            year = self.semester.academic_department.academic_year
            year_info = f" ({year.start_date.year}-{year.end_date.year})"
            semester_info = f" ({self.semester.name})"
        else:
            year_info = 'N/A'
            semester_info = 'N/A'
        return f"{self.code} - {self.name} {semester_info} {year_info}"


    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        # Update unique_together to use semester instead of academic_year
        unique_together = (
            "code",
            "semester",
        )  # A course code should be unique per semester
        # CHANGED: Update ordering to use semester's academic_department and then academic_year
        ordering = ["semester__academic_department__academic_year__start_date", "semester__order", "code"]

        

class CourseOutcome(models.Model):
    # Each CO belongs to a specific Course
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,  # If the course is deleted, its COs are deleted
        related_name="course_outcomes",
    )
    code = models.CharField(max_length=20, help_text="e.g., CO1, CO2")
    description = models.TextField()

    def __str__(self):
        return f"{self.course.code} - {self.code}: {self.description[:50]}..."

    class Meta:
        verbose_name = "Course Outcome"
        verbose_name_plural = "Course Outcomes"
        # A CO code must be unique within a given course
        unique_together = ("course", "code")
        ordering = ["course__code", "code"]  # Order by course code, then CO code


class CorrelationLevel(models.IntegerChoices):
    # Defining correlation levels as choices
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    NONE = 0, "None"  # Added None explicitly for unmapped state


class COPOMapping(models.Model):
    course_outcome = models.ForeignKey(
        CourseOutcome,
        on_delete=models.CASCADE,
        related_name="po_mappings",  # Allows accessing mappings from a CO
    )
    program_outcome = models.ForeignKey(
        ProgramOutcome,
        on_delete=models.CASCADE,
        related_name="co_mappings",  # Allows accessing mappings from a PO
    )
    correlation_level = models.IntegerField(
        choices=CorrelationLevel.choices,
        default=CorrelationLevel.NONE,  # Default to None (no mapping yet)
    )

    def __str__(self):
        level = self.get_correlation_level_display()
        return (
            f"{self.course_outcome.code} maps to {self.program_outcome.code} ({level})"
        )

    class Meta:
        verbose_name = "CO-PO Mapping"
        verbose_name_plural = "CO-PO Mappings"
        # Each Course Outcome can only be mapped to a specific Program Outcome once
        unique_together = ("course_outcome", "program_outcome")
        ordering = ["course_outcome__code", "program_outcome__code"]


class AssessmentType(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="e.g., Midterm Exam, Assignment, Project, Quiz",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Assessment Type"
        verbose_name_plural = "Assessment Types"
        ordering = ["name"]


class Assessment(models.Model):
    name = models.CharField(
        max_length=200, help_text="e.g., Midterm Exam - Unit 1, Assignment 2 - Loops"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,  # If course deleted, its assessments are deleted
        related_name="assessments",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,  # If academic year deleted, its assessments are deleted
        related_name="assessments",
    )
    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.SET_NULL,  # If type deleted, assessment remains but type becomes null
        null=True,
        blank=True,
        related_name="assessments",
    )
    max_marks = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Maximum marks for this assessment"
    )
    date = models.DateField(help_text="Date the assessment was conducted/due")

    # Many-to-Many relationship with CourseOutcome: an assessment can assess multiple COs,
    # and a CO can be assessed by multiple assessments.
    assesses_cos = models.ManyToManyField(
        CourseOutcome,
        blank=True,  # Optional to link to COs initially
        related_name="assessed_by_assessments",
    )

    def __str__(self):
        return f"{self.name} ({self.course.code}) - {self.academic_year.start_date.year}-{self.academic_year.end_date.year}"

    class Meta:
        verbose_name = "Assessment"
        verbose_name_plural = "Assessments"
        unique_together = (
            "name",
            "course",
            "academic_year",
        )  # Assessment name must be unique per course and year
        ordering = ["-academic_year__start_date", "course__code", "date"]


class StudentMark(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,  # If assessment deleted, marks are deleted
        related_name="student_marks",
    )
    student = models.ForeignKey(
        User,  # Assuming you are using Django's built-in User model
        on_delete=models.CASCADE,  # If user deleted, their marks are deleted
        related_name="assessment_marks",
    )
    marks_obtained = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Marks obtained by the student"
    )

    def __str__(self):
        return f"{self.student.username} - {self.assessment.name}: {self.marks_obtained}/{self.assessment.max_marks}"

    class Meta:
        verbose_name = "Student Mark"
        verbose_name_plural = "Student Marks"
        unique_together = (
            "assessment",
            "student",
        )  # Each student can only have one mark per assessment
        ordering = ["assessment__date", "student__username"]


class CourseOutcomeAttainment(models.Model):
    course_outcome = models.ForeignKey(
        CourseOutcome, on_delete=models.CASCADE, related_name="attainments"
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="co_attainments"
    )
    attainment_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    # Could add calculated_date, calculated_by (User) if needed for audit

    def __str__(self):
        return f"CO {self.course_outcome.code} Attainment for {self.academic_year} is {self.attainment_percentage}%"

    class Meta:
        verbose_name = "Course Outcome Attainment"
        verbose_name_plural = "Course Outcome Attainments"
        unique_together = ("course_outcome", "academic_year")
        ordering = [
            "academic_year__start_date",
            "course_outcome__course__code",
            "course_outcome__code",
        ]


class ProgramOutcomeAttainment(models.Model):
    program_outcome = models.ForeignKey(
        ProgramOutcome, on_delete=models.CASCADE, related_name="attainments"
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="po_attainments"
    )
    attainment_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    # Could add calculated_date, calculated_by (User)

    def __str__(self):
        return f"PO {self.program_outcome.code} Attainment for {self.academic_year} is {self.attainment_percentage}%"

    class Meta:
        verbose_name = "Program Outcome Attainment"
        verbose_name_plural = "Program Outcome Attainments"
        unique_together = ("program_outcome", "academic_year")
        ordering = ["academic_year__start_date", "program_outcome__code"]
