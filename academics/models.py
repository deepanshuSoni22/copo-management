# academics/models.py
"""
Database models for the COPO Management System.

This module defines all database models for managing Course Outcomes (CO),
Program Outcomes (PO), assessments, attainment tracking, and related academic data.
"""
from django.db import models
# from users.models import UserProfile  # Import UserProfile from the users app
from django.contrib.auth.models import User  # <--- ADD THIS LINE


class Department(models.Model):
    """
    Represents an academic department within the institution.
    
    Attributes:
        name (str): Unique name of the department
        branch (str): Academic branch/stream of the department
    """
    BRANCH_CHOICES = [
        ('Computer Science', 'Computer Science'),
        ('Commerce', 'Commerce'),
        ('Management', 'Management'),
        ('Arts', 'Arts'),
        ('Science', 'Science'),
        ('Humanities', 'Humanities'),
    ]

    name = models.CharField(max_length=100, unique=True)
    branch = models.CharField(max_length=100, choices=BRANCH_CHOICES)

    def __str__(self):
        return f"{self.name} - {self.branch}"

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"


class AcademicYear(models.Model):
    """
    Represents an academic year period for the institution.
    
    Attributes:
        start_date (date): Start date of the academic year (must be unique)
        end_date (date): End date of the academic year (must be unique)
        is_current (bool): Flag indicating if this is the current active academic year
    
    Note:
        Only one academic year should have is_current=True at a time.
    """
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
    """
    Links a Department to an Academic Year with an assigned HOD.
    
    This model allows department leadership to change per academic year
    while maintaining historical records.
    
    Attributes:
        department (Department): The department
        academic_year (AcademicYear): The academic year
        hod (UserProfile): Head of Department for this year (optional)
    
    Constraints:
        A department can only exist once per academic year (unique_together).
    """
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
    """
    Represents a Program Outcome (PO) for a department's academic program.
    
    Program Outcomes are broad statements that describe what students should
    know and be able to do upon graduation from the program.
    
    Attributes:
        department (Department): The department this PO belongs to
        code (str): Unique code within department (e.g., PO1, PO2, PSO1)
        description (str): Detailed description of the program outcome
    
    Constraints:
        Code must be unique within each department.
    """
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='program_outcomes',
    )

    code = models.CharField(max_length=20, help_text="e.g., PO1, PO2")
    description = models.TextField()

    def __str__(self):
        return f"{self.department.name} - {self.code}"

    class Meta:
        verbose_name = "Program Outcome"
        verbose_name_plural = "Program Outcomes"
        # --- ADD THIS to ensure code is unique within a department ---
        unique_together = ('department', 'code')
        ordering = ["department__name", "code"]
        indexes = [
            models.Index(fields=['department', 'code']),
        ]



class CourseType(models.TextChoices):
    """Enumeration of course types."""
    THEORY = 'THEORY', 'Theory'
    PRACTICAL = 'PRACTICAL', 'Practical'
    INTEGRATED = 'INTEGRATED', 'Integrated'

class Course(models.Model):
    """
    Represents an academic course offered in a specific semester.
    
    Attributes:
        name (str): Full name of the course
        code (str): Unique course code (e.g., CS101, BA203)
        department (Department): Department offering the course
        faculty (M2M UserProfile): Faculty members teaching the course
        semester (Semester): Semester when course is offered
        students (M2M UserProfile): Students enrolled in the course
        course_type (str): Type of course (Theory/Practical/Integrated)
        credits (int): Number of credits for the course
        prerequisites (str): Required knowledge/skills before taking course
    
    Constraints:
        Course code must be unique per semester.
    """
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
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['department', 'semester']),
            models.Index(fields=['semester']),
        ]
        

class CourseOutcome(models.Model):
    """
    Represents a Course Outcome (CO) for a specific course.
    
    Course Outcomes are specific statements describing what students should
    be able to do by the end of the course. Each CO is mapped to one or more
    Program Outcomes with varying correlation strengths.
    
    Attributes:
        course (Course): The course this outcome belongs to
        outcome_number (int): Sequential number within the course (1, 2, 3...)
        description (str): Detailed description of what students will achieve
        rbt_level (str): Revised Bloom's Taxonomy cognitive level
    
    Constraints:
        Outcome number must be unique within each course.
    
    Related:
        Maps to ProgramOutcomes via COPOMapping model.
    """
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
        indexes = [
            models.Index(fields=['course', 'code']),
        ]


class CorrelationLevel(models.IntegerChoices):
    """
    Enumeration of CO-PO correlation strength levels.
    
    Used to indicate how strongly a Course Outcome maps to a Program Outcome.
    Higher values indicate stronger correlation and greater weight in PO attainment.
    """
    # Defining correlation levels as choices
    NONE = 0, "None"  # Added None explicitly for unmapped state
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"


class COPOMapping(models.Model):
    """
    Maps Course Outcomes to Program Outcomes with correlation strength.
    
    This model establishes the relationship between what students learn in
    individual courses (COs) and the broader program goals (POs). Correlation
    levels are used as weights in PO attainment calculations.
    
    Attributes:
        course_outcome (CourseOutcome): The CO being mapped
        program_outcome (ProgramOutcome): The PO being mapped to
        correlation_level (int): Strength of correlation (0-3)
    
    Constraints:
        Each CO-PO pair can only be mapped once.
    
    Calculation Impact:
        Used in calculate_po_attainment_for_department() as weights.
    """
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
        indexes = [
            models.Index(fields=['course_outcome', 'program_outcome']),
            models.Index(fields=['course_outcome', 'correlation_level']),
        ]


class AssessmentType(models.Model):
    """
    Categorizes different types of assessments.
    
    Examples: Midterm Exam, Quiz, Assignment, Project, Lab Test
    
    Attributes:
        name (str): Unique name of the assessment type
    """
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
    """
    Represents an assessment/evaluation within a course.
    
    Assessments evaluate student performance on specific Course Outcomes.
    Student marks in assessments are used to calculate CO attainment.
    
    Attributes:
        name (str): Descriptive name of the assessment
        course (Course): Course this assessment belongs to
        academic_year (AcademicYear): Year when assessment was conducted
        assessment_type (AssessmentType): Category of assessment
        max_marks (Decimal): Maximum possible marks
        date (Date): When the assessment was conducted/due
        assesses_cos (M2M CourseOutcome): Which COs this assessment evaluates
    
    Constraints:
        Name must be unique within course and academic year.
    
    Related:
        StudentMark records individual student scores on this assessment.
    """
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
        max_digits=5, decimal_places=0, help_text="Maximum marks for this assessment"
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
        indexes = [
            models.Index(fields=['course', 'academic_year']),
            models.Index(fields=['date']),
            models.Index(fields=['academic_year', '-date']),
        ]


class StudentMark(models.Model):
    """
    Records marks obtained by a student in a specific assessment.
    
    These marks are aggregated to calculate Course Outcome attainment.
    
    Attributes:
        assessment (Assessment): The assessment being graded
        student (User): The student who took the assessment
        marks_obtained (Decimal): Marks earned by the student
    
    Constraints:
        Each student can have only one mark record per assessment.
        Marks cannot exceed assessment.max_marks (validated in forms).
    
    Calculation Impact:
        Used in calculate_co_attainment_for_course() to determine
        percentage of students meeting success threshold.
    """
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
        indexes = [
            models.Index(fields=['assessment', 'student']),
            models.Index(fields=['student']),
        ]


class CourseOutcomeAttainment(models.Model):
    """
    Stores calculated attainment percentage for a Course Outcome.
    
    Represents how well students achieved a specific CO in a given year,
    calculated from StudentMark data.
    
    Attributes:
        course_outcome (CourseOutcome): The CO being measured
        academic_year (AcademicYear): Year of attainment calculation
        attainment_percentage (Decimal): Percentage of students meeting threshold
    
    Constraints:
        One attainment record per CO per year.
    
    Calculation:
        Updated by calculate_co_attainment_for_course() function.
        Formula: (Students above threshold / Total students) * 100
    """
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
        indexes = [
            models.Index(fields=['course_outcome', 'academic_year']),
            models.Index(fields=['academic_year', 'attainment_percentage']),
        ]


class ProgramOutcomeAttainment(models.Model):
    """
    Stores calculated attainment percentage for a Program Outcome.
    
    Represents how well the program achieved a PO in a given year,
    calculated as weighted average of related CO attainments.
    
    Attributes:
        program_outcome (ProgramOutcome): The PO being measured
        academic_year (AcademicYear): Year of attainment calculation
        attainment_percentage (Decimal): Weighted average attainment
    
    Constraints:
        One attainment record per PO per year.
    
    Calculation:
        Updated by calculate_po_attainment_for_department() function.
        Formula: SUM(CO_attainment * correlation_level) / SUM(correlation_level)
        Uses COPOMapping.correlation_level as weights.
    """
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
        indexes = [
            models.Index(fields=['program_outcome', 'academic_year']),
            models.Index(fields=['academic_year', 'attainment_percentage']),
        ]


# --- NEW: Course Plan Management Models ---

class CoursePlan(models.Model):
    """
    Detailed planning document for a course offering.
    
    Contains objectives, lesson plans, and CIA (Continuous Internal Assessment)
    components for a specific course. Each course has one course plan.
    
    Attributes:
        course (Course): The course this plan is for (OneToOne)
        course_objectives (str): Overall learning objectives
        course_summary (str): Brief summary of course content
        reference_books (str): Recommended reading materials
        course_website (str): Online resources URL
        created_at (DateTime): When plan was created
        updated_at (DateTime): Last modification timestamp
    
    Constraints:
        One course plan per course (OneToOne relationship).
    
    Related:
        Contains multiple WeeklyLessonPlan and CIAComponent entries.
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
    Specific learning objectives for course plan units.
    
    Different from CourseOutcomes - these are unit-level objectives
    described in the course planning document.
    
    Attributes:
        course_plan (CoursePlan): Parent course plan
        unit_number (str): Unit identifier (e.g., "1", "Unit A")
        objective_text (str): Detailed objective description
        order (int): Sequence within course plan
    
    Constraints:
        Order must be unique within each course plan.
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
    Weekly schedule entry in course lesson plan.
    
    Describes topics, teaching methods, and resources for each week/unit
    of the course.
    
    Attributes:
        course_plan (CoursePlan): Parent course plan
        unit_number (str): Unit identifier (e.g., "I", "II", "Unit 1")
        unit_details (str): Topics covered this week
        start_date (Date): Week start date
        end_date (Date): Week end date
        pedagogy (str): Teaching methods (Lecture, Demo, Activity-Based)
        references (str): Textbooks and web resources
        order (int): Sequence in lesson plan
    
    Constraints:
        Order must be unique within each course plan.
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
    Continuous Internal Assessment component definition.
    
    Defines the internal assessment structure (quizzes, assignments, etc.)
    planned for the course.
    
    Attributes:
        course_plan (CoursePlan): Parent course plan
        component_name (str): Name of assessment type
        weightage (Decimal): Weight in overall grade (percentage)
        description (str): Details about the component
        order (int): Sequence in CIA structure
    
    Constraints:
        Order must be unique within each course plan.
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
    # --- ADD THIS NEW FIELD ---
    evaluation_rubric = models.TextField(
        blank=True,
        null=True,
        help_text="Descriptive rubric for this component (e.g., criteria for Content, Neatness)."
    )

    def __str__(self):
        return f"CIA: {self.component_name} for {self.course_plan.course.code}"

    class Meta:
        verbose_name = "CIA Component"
        verbose_name_plural = "CIA Components"
        unique_together = ('course_plan', 'component_name')
        ordering = ['order']


class Rubric(models.Model):
    """
    Reusable grading rubric template.
    
    Faculty can create rubrics with multiple criteria for consistent
    evaluation of assignments/projects.
    
    Attributes:
        name (str): Descriptive name of rubric
        description (str): Purpose and usage notes
        created_by (UserProfile): Faculty who created the rubric
    
    Related:
        Contains multiple RubricCriterion entries.
        Used by Assignment model for grading.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE, related_name='rubrics')
    
    def __str__(self):
        return self.name

class RubricCriterion(models.Model):
    """
    Individual grading criterion within a rubric.
    
    Examples: Content Quality, Clarity, Organization, Code Style
    
    Attributes:
        rubric (Rubric): Parent rubric
        criterion_text (str): Name of criterion
        max_score (int): Maximum points for this criterion
        order (int): Display sequence
    
    Related:
        Scored via RubricScore for each student submission.
    """
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
    """
    Score awarded for a specific rubric criterion on a submission.
    
    Links a student's submission to individual criterion scores,
    enabling detailed feedback and grading transparency.
    
    Attributes:
        submission (Submission): Student's assignment submission
        criterion (RubricCriterion): Criterion being scored
        score (int): Points awarded (0 to criterion.max_score)
    
    Constraints:
        One score per criterion per submission.
    """
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
    """
    Assignment or project given to students in a course.
    
    Can be graded either with simple marks or detailed rubric scoring.
    Supports file uploads for submissions.
    
    Attributes:
        course (Course): Course this assignment belongs to
        created_by (UserProfile): Faculty who created the assignment
        title (str): Assignment title
        description (str): Instructions and requirements
        assignment_type (str): PDF_UPLOAD or RUBRIC_BASED
        due_date (DateTime): Submission deadline
        rubric (Rubric): Optional rubric for detailed grading
        cia_component (CIAComponent): Optional link to CIA structure
        max_marks (Decimal): Maximum points for the assignment
        assesses_cos (M2M CourseOutcome): COs evaluated by this assignment
    
    Related:
        Students submit via Submission model.
    """
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

    # ADD A FIELD FOR MAXIMUM MARKS
    max_marks = models.DecimalField(
        max_digits=6,
        decimal_places=0,
        default=0,
        help_text="The maximum marks for this assignment."
    )

    # ADD A MANY-TO-MANY FIELD TO LINK TO COURSE OUTCOMES
    assesses_cos = models.ManyToManyField(
        CourseOutcome,
        blank=True,
        related_name="assessed_by_assignments",
        help_text="Select the Course Outcomes that this assignment assesses."
    )

    def __str__(self):
        return f"{self.title} - {self.course.code}"
    
    class Meta:
        ordering = ['-due_date']

class Submission(models.Model):
    """
    Student's submission for an assignment.
    
    Stores uploaded files, marks, and feedback for each student's
    assignment attempt.
    
    Attributes:
        assignment (Assignment): The assignment being submitted
        student (UserProfile): Student submitting the work
        submitted_at (DateTime): Submission timestamp
        file (FileField): Uploaded submission file
        marks_obtained (Decimal): Points earned
        feedback (str): Instructor comments
        graded_at (DateTime): When grading was completed
        graded_by (UserProfile): Faculty who graded the submission
    
    Constraints:
        One submission per student per assignment (managed in views).
    
    Related:
        Rubric-based assignments have associated RubricScore entries.
    """
    # Use a string reference for the ForeignKey
    assignment = models.ForeignKey('academics.Assignment', on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE, related_name='submissions', limit_choices_to={'role': 'STUDENT'})
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='%Y/%m/%d/', blank=True, null=True)
    
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=0, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    graded_by = models.ForeignKey('users.UserProfile', on_delete=models.SET_NULL, blank=True, null=True, related_name='graded_submissions')

    def __str__(self):
        return f"Submission by {self.student.user.username} for {self.assignment.title}"

    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']


class AuditLog(models.Model):
    """
    Tracks all significant user activities across the system for accountability and debugging.
    Logs create, update, and delete operations on critical models.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('CALCULATE', 'Calculate'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        help_text="User who performed the action"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the model affected (e.g., 'Course', 'Assessment')"
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID of the affected object"
    )
    object_repr = models.CharField(
        max_length=500,
        blank=True,
        help_text="String representation of the affected object"
    )
    changes = models.TextField(
        blank=True,
        null=True,
        help_text="JSON string of changes made (for UPDATE actions)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred"
    )
    
    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action} {self.model_name} at {self.timestamp}"
    
    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'user']),
            models.Index(fields=['model_name', 'action']),
        ]





