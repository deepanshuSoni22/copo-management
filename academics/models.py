# academics/models.py
from django.db import models
from users.models import UserProfile  # Import UserProfile from the users app
from django.contrib.auth.models import User  # <--- ADD THIS LINE


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


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    hod = models.OneToOneField(
        UserProfile,
        on_delete=models.SET_NULL,  # If HOD is deleted, department remains but HOD field becomes null
        related_name="headed_department",
        null=True,
        blank=True,
        limit_choices_to={
            "role__in": ["HOD", "FACULTY"]
        },  # This will show both HODs and Faculty
        verbose_name="Head of Department",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"


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
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,  # If academic year is deleted, courses within it are also deleted
        related_name="courses",
        null=True,  # Allow courses not yet assigned to a year initially
        blank=True,
    )

    def __str__(self):
        return f"{self.code} - {self.name} ({self.department.name if self.department else 'N/A'})"

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        unique_together = (
            "code",
            "academic_year",
        )  # A course code should be unique per academic year
        ordering = [
            "academic_year__start_date",
            "code",
        ]  # Order by academic year then code


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
