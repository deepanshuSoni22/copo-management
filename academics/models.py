# academics/models.py
from django.db import models
# from users.models import UserProfile  # Import UserProfile from the users app
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
        'users.UserProfile',
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


class CourseType(models.TextChoices):
    THEORY = 'THEORY', 'Theory'
    PRACTICAL = 'PRACTICAL', 'Practical'
    INTEGRATED = 'INTEGRATED', 'Integrated'

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
        'users.UserProfile',
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

    # --- ADD THIS NEW FIELD ---
    students = models.ManyToManyField(
        'users.UserProfile',
        related_name='enrolled_courses',
        blank=True,
        limit_choices_to={'role': 'STUDENT'}
    )

    # --- NEW FIELDS FROM PDF ---
    course_type = models.CharField(
        max_length=20,
        choices=CourseType.choices,
        default=CourseType.THEORY,
        help_text="The type of the course, e.g., Theory or Practical"
    ) # 
    credits = models.PositiveIntegerField(
        default=4,
        help_text="Number of credits for the course"
    ) # 
    prerequisites = models.TextField(
        blank=True,
        null=True,
        help_text="Knowledge or skills required before taking this course"
    ) #

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

    # --- NEW FIELDS FOR REVISED BLOOM'S TAXONOMY (RBT) ---
    rbt_level_1 = models.BooleanField(default=False, verbose_name="RBT 1 (Remember)")
    rbt_level_2 = models.BooleanField(default=False, verbose_name="RBT 2 (Understand)")
    rbt_level_3 = models.BooleanField(default=False, verbose_name="RBT 3 (Apply)")
    rbt_level_4 = models.BooleanField(default=False, verbose_name="RBT 4 (Analyze)")
    rbt_level_5 = models.BooleanField(default=False, verbose_name="RBT 5 (Evaluate)")
    rbt_level_6 = models.BooleanField(default=False, verbose_name="RBT 6 (Create)")

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


# --- NEW: Course Plan Management Models ---

class CoursePlan(models.Model):
    """
    The main model representing a detailed Course Plan for a specific Course offering.
    """
    # Course plan is one-to-one with Course, as there's typically one plan per specific course offering (e.g., CS101-1st Sem-2024).
    # Making it primary_key=True ensures the CoursePlan's PK is the same as the Course's PK.
    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='course_plan' # Access CoursePlan from Course via course_instance.course_plan
    )
    title = models.CharField(max_length=255, help_text="e.g., Course Plan for AI (V SEM A & B)")
    
    # ADD these two new fields based on the PDF
    classes_per_week = models.PositiveIntegerField(
        default=4,
        help_text="Number of classes scheduled per week for this course."
    )

    total_hours_allotted = models.PositiveIntegerField(
        default=60,
        help_text="Total hours allotted for the entire course."
    )

    # Coordinator and Instructors (from PDF)
    course_coordinator = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='coordinated_course_plans',
        limit_choices_to={'role__in': ['FACULTY', 'HOD']}, # Only Faculty or HOD can be coordinators
        help_text="Primary person responsible for the course plan."
    )
    instructors = models.ManyToManyField(
        'users.UserProfile',
        related_name='instructed_course_plans',
        blank=True,
        help_text="Other instructors assigned to this course (if any)."
    )

    # --- THIS IS THE MISSING FIELD THAT CAUSED THE ERROR ---
    assessment_ratio = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="The ratio of internal to external assessment marks, e.g., 60:40"
    )
    
    # Administrative details
    created_by = models.ForeignKey( # Typically the HOD who created the plan
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_course_plans'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Course Plan for {self.course.code} - {self.course.name}"

    class Meta:
        verbose_name = "Course Plan"
        verbose_name_plural = "Course Plans"
        # Ordering based on the linked course's semester and academic department
        ordering = ['-course__semester__academic_department__academic_year__start_date', 'course__code']


class CourseObjective(models.Model):
    """
    Represents course objectives as described in the Course Plan document.
    These are distinct from CourseOutcomes (COs).
    """
    course_plan = models.ForeignKey(
        CoursePlan,
        on_delete=models.CASCADE,
        related_name='course_objectives'
    )
    unit_number = models.CharField(max_length=10, blank=True, null=True, help_text="e.g., 1, 2, Unit A, Unit B")
    objective_text = models.TextField(help_text="Detailed description of the course objective.")
    order = models.PositiveIntegerField(default=0, help_text="Order of the objective within the Course Plan")

    def __str__(self):
        return f"Obj for {self.course_plan.course.code} (Unit {self.unit_number}): {self.objective_text[:50]}..."

    class Meta:
        verbose_name = "Course Objective (Plan)"
        verbose_name_plural = "Course Objectives (Plan)"
        unique_together = ('course_plan', 'order')
        ordering = ['order']


class WeeklyLessonPlan(models.Model):
    """
    Represents a weekly entry in the Lesson Plan section of the Course Plan.
    """
    course_plan = models.ForeignKey(
        CoursePlan,
        on_delete=models.CASCADE,
        related_name='weekly_lesson_plans'
    )
    unit_number = models.CharField(max_length=10, help_text="e.g., I, II, Unit 1")
    unit_details = models.TextField(help_text="Topics covered in this unit/week.")
    start_date = models.DateField(blank=True, null=True, help_text="Start date for the weekly plan")
    end_date = models.DateField(blank=True, null=True, help_text="End date for the weekly plan")
    pedagogy = models.TextField(blank=True, null=True, help_text="Methods used for teaching (e.g., Lecture, Demo, Activity-Based Learning).")
    references = models.TextField(blank=True, null=True, help_text="Textbooks, web links for this unit.")
    order = models.PositiveIntegerField(default=0, help_text="Order of the weekly plan entry.")

    def __str__(self):
        return f"Lesson Plan for {self.course_plan.course.code} (Unit {self.unit_number})"

    class Meta:
        verbose_name = "Weekly Lesson Plan"
        verbose_name_plural = "Weekly Lesson Plans"
        unique_together = ('course_plan', 'order') # Unit number should be unique within a plan
        ordering = ['order']


class CIAComponent(models.Model):
    """
    Represents a Continuous Internal Assessment (CIA) Component defined in the Course Plan.
    """
    course_plan = models.ForeignKey(
        CoursePlan,
        on_delete=models.CASCADE,
        related_name='cia_components'
    )
    component_name = models.CharField(max_length=200, help_text="e.g., CIA-I Test (10 Marks), CIA-II Assignment (5 Marks)")
    units_covered = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., UNIT 1 & 2")
    # Link directly to CourseOutcome model for COs assessed by this component
    cos_covered = models.ManyToManyField(
        CourseOutcome,
        blank=True,
        related_name='cia_assessed_by'
    )
    order = models.PositiveIntegerField(default=0, help_text="Order of the CIA component.")

    def __str__(self):
        return f"CIA: {self.component_name} for {self.course_plan.course.code}"

    class Meta:
        verbose_name = "CIA Component"
        verbose_name_plural = "CIA Components"
        unique_together = ('course_plan', 'component_name')
        ordering = ['order']


class Rubric(models.Model):
    """A reusable rubric template created by a faculty member."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE, related_name='rubrics')
    
    def __str__(self):
        return self.name

class RubricCriterion(models.Model):
    """A single criterion within a Rubric (e.g., 'Content', 'Clarity')."""
    # Use a string reference for the ForeignKey
    rubric = models.ForeignKey('academics.Rubric', on_delete=models.CASCADE, related_name='criteria')
    criterion_text = models.CharField(max_length=500, help_text="e.g., 'Clarity and Organization'")
    max_score = models.PositiveIntegerField(default=5)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.criterion_text

    class Meta:
        ordering = ['order']


class RubricScore(models.Model):
    """The actual score given to a student's submission for a specific criterion."""
    # Use string references for the ForeignKeys
    submission = models.ForeignKey('academics.Submission', on_delete=models.CASCADE, related_name='rubric_scores')
    criterion = models.ForeignKey('academics.RubricCriterion', on_delete=models.CASCADE)
    score = models.PositiveIntegerField()

    def __str__(self):
        if self.criterion_id and self.criterion:
            return f"{self.criterion.criterion_text}: {self.score}"
        return f"Unlinked Score: {self.score}"
        
    class Meta:
        unique_together = ('submission', 'criterion')



class Assignment(models.Model):
    """Represents an assignment created by a faculty member for a specific course."""
    class AssignmentType(models.TextChoices):
        PDF_UPLOAD = 'pdf_upload', 'PDF/File Upload'
        RUBRIC_BASED = 'rubric_based', 'Rubric-Based Assessment'

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    created_by = models.ForeignKey('users.UserProfile', on_delete=models.SET_NULL, null=True, related_name='created_assignments')
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assignment_type = models.CharField(max_length=20, choices=AssignmentType.choices, default=AssignmentType.PDF_UPLOAD)
    due_date = models.DateTimeField()
    
    # Use a string reference for the ForeignKey
    rubric = models.ForeignKey('academics.Rubric', on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    cia_component = models.ForeignKey(CIAComponent, on_delete=models.SET_NULL, blank=True, null=True, related_name='assignments')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.course.code}"
    
    class Meta:
        ordering = ['-due_date']

class Submission(models.Model):
    """Represents a student's submission for a given assignment."""
    # Use a string reference for the ForeignKey
    assignment = models.ForeignKey('academics.Assignment', on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE, related_name='submissions', limit_choices_to={'role': 'STUDENT'})
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='%Y/%m/%d/', blank=True, null=True)
    
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    graded_by = models.ForeignKey('users.UserProfile', on_delete=models.SET_NULL, blank=True, null=True, related_name='graded_submissions')

    def __str__(self):
        return f"Submission by {self.student.user.username} for {self.assignment.title}"

    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']





