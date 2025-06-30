# academics/forms.py
from django import forms
from .models import (
    AcademicYear,
    Department,
    ProgramOutcome,
    Course,
    CourseOutcome,
    COPOMapping,
    CorrelationLevel,
    AssessmentType,
    Assessment,
    StudentMark,
    Semester,
    AcademicDepartment, CoursePlan, CourseObjective, WeeklyLessonPlan, CIAComponent, Rubric, RubricCriterion, Assignment, Submission, RubricScore
)
from users.models import UserProfile, UserRole  # Import UserProfile from the users app
from django.forms import (
    inlineformset_factory,
    modelformset_factory,
)  # Import formset factories
from django.forms import modelformset_factory
from django.contrib.auth.models import User  # <--- ADD THIS LINE
from django.forms import inlineformset_factory


class AcademicYearForm(forms.ModelForm):
    # Optional: Add custom widgets or validation if needed
    start_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base",
            }
        ),
        label="Start Date",
    )
    end_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base",
            }
        ),
        label="End Date",
    )
    is_current = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-checkbox h-5 w-5 text-indigo-600 rounded focus:ring-indigo-500"
            }
        ),
        label="Set as Current Academic Year",
    )

    class Meta:
        model = AcademicYear
        fields = ["start_date", "end_date", "is_current"]
        # You can add custom styling for each field individually here as well
        widgets = {
            # Default text input styling (can be overridden by specific field definitions above)
            "name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        is_current = cleaned_data.get("is_current")

        if start_date and end_date:
            if start_date >= end_date:
                self.add_error("end_date", "End date must be after start date.")

        # Logic to ensure only one AcademicYear can be 'is_current'
        if is_current:
            existing_current = AcademicYear.objects.filter(is_current=True)
            if self.instance.pk:  # If updating an existing instance
                existing_current = existing_current.exclude(pk=self.instance.pk)
            if existing_current.exists():
                self.add_error(
                    "is_current",
                    "Another academic year is already set as current. Please unmark it first.",
                )

        return cleaned_data


SEMESTER_CHOICES = [
    ('', 'Select Semester'),  # Header/placeholder
    ('I Semester', 'I Semester'),
    ('II Semester', 'II Semester'),
    ('III Semester', 'III Semester'),
    ('IV Semester', 'IV Semester'),
    ('V Semester', 'V Semester'),
    ('VI Semester', 'VI Semester'),
    ('VII Semester', 'VII Semester'),
    ('VIII Semester', 'VIII Semester'),
]

class SemesterForm(forms.ModelForm):
    name = forms.ChoiceField(  # <-- Keep it as ChoiceField for dropdown + JS logic
        choices=SEMESTER_CHOICES,
        label='Semester',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'
        })
    )

    academic_department = forms.ModelChoiceField(
        queryset=AcademicDepartment.objects.all().select_related('department', 'academic_year').order_by('-academic_year__start_date', 'department__name'),
        empty_label="Select Academic Department",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'
        }),
        label='Academic Department'
    )

    order = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:focus:border-indigo-500 sm:text-base'
        }),
        label='Order in Year'
    )

    class Meta:
        model = Semester
        fields = ['name', 'academic_department', 'order']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.profile.role == 'HOD':
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=self.request.user.profile)
                self.fields['academic_department'].initial = hod_academic_department
                self.fields['academic_department'].queryset = AcademicDepartment.objects.filter(pk=hod_academic_department.pk)
                self.fields['academic_department'].disabled = True
                self.fields['academic_department'].widget.attrs['class'] += ' bg-gray-100 cursor-not-allowed'
                self.fields['academic_department'].help_text = "Your department is pre-selected based on your HOD assignment and cannot be changed."
            except AcademicDepartment.DoesNotExist:
                self.fields['academic_department'].disabled = True
                self.fields['academic_department'].queryset = AcademicDepartment.objects.none()
                self.fields['academic_department'].help_text = "Your HOD profile is not assigned to an Academic Department."
            except AcademicDepartment.MultipleObjectsReturned:
                self.fields['academic_department'].disabled = True
                self.fields['academic_department'].queryset = AcademicDepartment.objects.none()
                self.fields['academic_department'].help_text = "Data inconsistency: HOD assigned to multiple Academic Departments."

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        academic_department = cleaned_data.get('academic_department')

        if self.request and self.request.user.profile.role == 'HOD' and self.fields['academic_department'].disabled:
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=self.request.user.profile)
                cleaned_data['academic_department'] = hod_academic_department
            except AcademicDepartment.DoesNotExist:
                self.add_error('academic_department', "Associated Academic Department could not be found for your HOD profile.")
            except AcademicDepartment.MultipleObjectsReturned:
                self.add_error('academic_department', "Multiple Academic Departments found for your HOD profile.")

        if name and 'academic_department' in cleaned_data and cleaned_data['academic_department']:
            if Semester.objects.filter(name=name, academic_department=cleaned_data['academic_department']).exclude(pk=self.instance.pk).exists():
                self.add_error('name', f"A semester named '{name}' already exists for this Academic Department.")

        return cleaned_data



# --- NEW: AcademicDepartmentForm ---
class AcademicDepartmentForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all().order_by('name'), # Order by name for selection
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
        label='Department'
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all().order_by('-start_date'), # Latest years first
        empty_label="Select Academic Year",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:focus:border-indigo-500 sm:text-base'}),
        label='Academic Year'
    )
    hod = forms.ModelChoiceField(
        queryset=UserProfile.objects.filter(role__in=['HOD', 'FACULTY']).select_related('user').order_by('user__username'),
        empty_label="No HOD assigned",
        required=False,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
        label='Head of Department'
    )

    class Meta:
        model = AcademicDepartment
        fields = ['department', 'academic_year', 'hod']
        # No extra widgets needed here as fields are explicitly defined above

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure the user's full name is displayed for HOD selection
        self.fields['hod'].label_from_instance = lambda obj: f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})" if obj.user.first_name else obj.user.username

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        academic_year = cleaned_data.get('academic_year')

        # Custom validation for unique_together constraint
        if department and academic_year:
            if AcademicDepartment.objects.filter(department=department, academic_year=academic_year).exclude(pk=self.instance.pk).exists():
                self.add_error('department', 'This department is already associated with this academic year.')
                self.add_error('academic_year', 'This academic year is already associated with this department.')
        return cleaned_data


class DepartmentForm(forms.ModelForm):
    # Customizing the HOD field to use a select widget for UserProfile objects
    # This also allows for custom styling via attrs
    # hod = forms.ModelChoiceField(
    #     queryset=UserProfile.objects.filter(role="HOD").select_related(
    #         "user"
    #     ),  # Only show HOD profiles
    #     empty_label="No HOD assigned",  # Optional: allow no HOD
    #     required=False,  # HOD assignment is optional
    #     widget=forms.Select(
    #         attrs={
    #             "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
    #         }
    #     ),
    #     label="Head of Department",
    # )

    class Meta:
        model = Department
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Further filter HOD queryset in init if you want to ensure it only shows *active* HOD users if possible.
        # This is already done with limit_choices_to in the model and filter(role='HOD') in the form field.
        # Ensure the user's full name is displayed for HOD selection
        # self.fields["hod"].label_from_instance = lambda obj: (
        #     f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"
        #     if obj.user.first_name
        #     else obj.user.username
        # )


class ProgramOutcomeForm(forms.ModelForm):
    class Meta:
        model = ProgramOutcome
        fields = ["code", "description"]
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base",
                    "rows": 4,
                }
            ),
        }


class CourseForm(forms.ModelForm):
    # Customize fields with Tailwind classes
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
        label='Department'
    )
    # Changed: academic_year field is removed, now linked via semester
    semester = forms.ModelChoiceField( # NEW: Semester field
        queryset=Semester.objects.all().select_related('academic_department__department', 'academic_department__academic_year').order_by('-academic_department__academic_year__start_date', 'order'),
        empty_label="Select Semester",
        required=False, # Make it optional initially if course can exist without semester
        widget=forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
        label='Semester'
    )
    # The 'faculty' field is a ManyToMany (existing)
    faculty = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.filter(role__in=[UserRole.FACULTY, UserRole.HOD]).select_related("user"),
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "faculty-checkbox-list" # We'll style this with CSS
            }
        ),
        label="Assigned Faculty",
        required=False,
        help_text="Select all faculty members assigned to teach this course.",
    )

    # --- 1. ENSURE THIS FIELD IS DEFINED ---
    students = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.filter(role=UserRole.STUDENT),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Enrolled Students'
    )

    # Assesses COs field (fixed from previous errors)
    assesses_cos = forms.ModelMultipleChoiceField(
        queryset=CourseOutcome.objects.all().select_related("course").order_by("course__code", "code"),
        widget=forms.SelectMultiple(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base h-32"
            }
        ),
        label="Assesses Course Outcomes",
        required=False,
        help_text="Hold Ctrl/Cmd to select multiple Course Outcomes assessed by this."
    )


    class Meta:
        model = Course
        fields = ["name", "code", "department", "semester", "faculty", "assesses_cos", "students"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "code": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None) # Pop request out of kwargs
        super().__init__(*args, **kwargs)

        # HOD restriction logic
        if self.request and self.request.user.profile.role == 'HOD':
            try:
                hod_academic_department = AcademicDepartment.objects.get(hod=self.request.user.profile)
                # Filter queryset for 'department' field to only HOD's department
                self.fields['department'].queryset = Department.objects.filter(pk=hod_academic_department.department.pk)
                # Set initial value and disable the field
                self.fields['department'].initial = hod_academic_department.department
                self.fields['department'].disabled = True
                self.fields['department'].widget.attrs['class'] += ' bg-gray-100 cursor-not-allowed'
                self.fields['department'].help_text = "Your department is pre-selected based on your HOD assignment and cannot be changed."
                
                # Further filter semester queryset to only those belonging to HOD's department
                self.fields['semester'].queryset = Semester.objects.filter(academic_department=hod_academic_department).select_related('academic_department__department', 'academic_department__academic_year').order_by('-academic_department__academic_year__start_date', 'order')

            except AcademicDepartment.DoesNotExist:
                self.fields['department'].disabled = True
                self.fields['department'].queryset = Department.objects.none()
                self.fields['department'].help_text = "Your HOD profile is not assigned to an Academic Department. No department choices available."
                self.fields['semester'].disabled = True
                self.fields['semester'].queryset = Semester.objects.none()
                self.fields['semester'].help_text = ""
            except AcademicDepartment.MultipleObjectsReturned:
                self.fields['department'].disabled = True
                self.fields['department'].queryset = Department.objects.none()
                self.fields['department'].help_text = "Data inconsistency: HOD assigned to multiple Academic Departments."
                self.fields['semester'].disabled = True
                self.fields['semester'].queryset = Semester.objects.none()
                self.fields['semester'].help_text = ""

        self.fields["faculty"].label_from_instance = lambda obj: (
            f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"
            if obj.user.first_name
            else obj.user.username
        )
        # Pre-filter assesses_cos queryset based on selected course if instance exists
        if getattr(self.instance, "course", None): # This logic is fine, it applies to an *existing* Course instance
            self.fields["assesses_cos"].queryset = (
                self.instance.course.course_outcomes.all().order_by("code")
            )
        else: # For new Course forms or if no instance.course
            # If the Course doesn't have a semester yet, filter to no COs.
            # Otherwise, show all COs if no specific course instance is bound.
            # For new Course forms, semester is picked after department.
            # We want to show COs only if semester is selected.
            # This complex pre-filtering is typically better handled by JS on frontend or dynamic updates.
            # For a new form, without a semester selected, show no COs initially.
            self.fields["assesses_cos"].queryset = CourseOutcome.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        
        # If the department field was disabled for HOD, re-attach its value from the HOD's AcademicDepartment
        if self.request and self.request.user.profile.role == 'HOD' and self.fields['department'].disabled:
            try:
                hod_academic_department = AcademicDepartment.objects.select_related('department').get(hod=self.request.user.profile)
                cleaned_data['department'] = hod_academic_department.department
            except AcademicDepartment.DoesNotExist:
                # If HOD's department is missing, add an error if department is required.
                self.add_error('department', "Your assigned department could not be found.")
            except AcademicDepartment.MultipleObjectsReturned:
                self.add_error('department', "Data inconsistency: Multiple Academic Departments found for your HOD profile.")
        
        return cleaned_data


class CourseOutcomeForm(forms.ModelForm):
    # Customize fields with Tailwind classes
    course = forms.ModelChoiceField(
        queryset=Course.objects.all().order_by(
            "code"
        ),  # Order by course code for selection
        empty_label="Select Course",
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="Course",
    )

    class Meta:
        model = CourseOutcome
        fields = ["course", "code", "description"]
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base",
                    "rows": 4,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get("course")
        code = cleaned_data.get("code")

        # Custom validation for unique_together (though model handles it, this provides better feedback)
        if course and code:
            if (
                CourseOutcome.objects.filter(course=course, code=code)
                .exclude(pk=self.instance.pk)
                .exists()
            ):
                self.add_error("code", "This code is already used for this course.")
        return cleaned_data


# Form for a single CO-PO mapping entry (used within a formset)
class COPOMappingForm(forms.ModelForm):
    # Make program_outcome field hidden as it will be managed by the formset
    # and we only want correlation level to be editable per PO
    program_outcome = forms.ModelChoiceField(
        queryset=ProgramOutcome.objects.all(),
        widget=forms.HiddenInput(),  # Hidden input for PO
        required=True,
    )
    # Correlation level with specific styling
    correlation_level = forms.ChoiceField(
        choices=CorrelationLevel.choices,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            }
        ),
        label="Correlation",
    )

    class Meta:
        model = COPOMapping
        fields = ["program_outcome", "correlation_level"]
        # Do NOT exclude 'course_outcome' here; it will be set by the formset factory


# Formset factory for managing multiple COPOMapping instances for one CourseOutcome
# We are creating a formset that allows updating existing COPOMapping instances
# or creating new ones.
# COPO_Mapping_FormSet = inlineformset_factory(
#     CourseOutcome,           # Parent model: A formset for mappings related to a CourseOutcome
#     COPOMapping,             # Child model: COPOMapping instances
#     form=COPOMappingForm,    # Use our custom COPOMappingForm
#     extra=0,                 # We will add POs dynamically, no extra empty forms by default
#     can_delete=False,        # We don't want to delete mappings directly, just change correlation
#     fields=['program_outcome', 'correlation_level'],
#     labels={
#         'program_outcome': '', # Label will be displayed in template headers
#         'correlation_level': 'Level'
#     }
# )


class AssessmentTypeForm(forms.ModelForm):
    class Meta:
        model = AssessmentType
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
        }


class AssessmentForm(forms.ModelForm):
    # Customize fields with Tailwind classes
    course = forms.ModelChoiceField(
        queryset=Course.objects.all().order_by("code"),
        empty_label="Select Course",
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="Course",
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all().order_by("-start_date"),
        empty_label="Select Academic Year",
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="Academic Year",
    )
    assessment_type = forms.ModelChoiceField(
        queryset=AssessmentType.objects.all().order_by("name"),
        empty_label="Select Type",
        required=False,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="Assessment Type",
    )
    date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base",
            }
        ),
        label="Date",
    )
    assesses_cos = forms.ModelMultipleChoiceField(
        queryset=CourseOutcome.objects.all()
        .select_related("course")
        .order_by("course__code", "code"),
        widget=forms.SelectMultiple(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base h-32"
            }
        ),
        label="Assesses Course Outcomes",
        required=False,
        help_text="Hold Ctrl/Cmd to select multiple Course Outcomes assessed by this.",
    )

    class Meta:
        model = Assessment
        fields = [
            "name",
            "course",
            "academic_year",
            "assessment_type",
            "max_marks",
            "date",
            "assesses_cos",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "max_marks": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-filter assesses_cos queryset based on selected course if instance exists
        if getattr(self.instance, "course", None):
            self.fields["assesses_cos"].queryset = (
                self.instance.course.course_outcomes.all().order_by("code")
            )
        else:
            # Initially, if no course is selected, or for create, filter by a common (or no) course
            # or handle with JS on frontend for dynamic filtering
            pass  # Keep it as all COs for now, or consider dynamic JS filtering if needed


class StudentMarkForm(forms.ModelForm):
    id = forms.IntegerField(widget=forms.HiddenInput(), required=False)  # ADD THIS LINE

    student = forms.ModelChoiceField(
        queryset=User.objects.all().order_by(
            "username"
        ),  # Customize this if you have a Student profile
        widget=forms.HiddenInput(),  # Hidden input for student
        required=True,
    )
    marks_obtained = forms.DecimalField(
        widget=forms.NumberInput(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base",
                "step": "0.01",
            }
        ),
        label="Marks Obtained",
    )

    class Meta:
        model = StudentMark
        fields = ["id", "student", "marks_obtained"]


# Formset factory for managing multiple StudentMark instances for one Assessment
# We are creating a formset that allows updating existing StudentMark instances
# or creating new ones.
from django.forms import formset_factory

StudentMarkFormSet = formset_factory(StudentMarkForm, extra=0)


# --- NEW: CoursePlan Management Forms ---

class CoursePlanForm(forms.ModelForm):
    # The 'course' field is a OneToOne, so it will be rendered automatically.
    # We will need to customize its queryset in the view for context-specific creation.
    
    course_coordinator = forms.ModelChoiceField(
        queryset=UserProfile.objects.filter(role__in=[UserRole.FACULTY, UserRole.HOD]).select_related('user').order_by('user__username'),
        empty_label="Select Coordinator (Optional)",
        required=False,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
        label='Course Coordinator'
    )
    instructors = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.filter(role__in=[UserRole.FACULTY, UserRole.HOD]).select_related('user').order_by('user__username'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'mt-1 block'}), # Standard checkbox list
        label='Additional Instructors'
    )

    class Meta:
        model = CoursePlan
        # Note: 'course' field is automatically handled by ModelForm due to primary_key=True on the model
        fields = ['title', 'description', 'course_coordinator', 'instructors']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
            'description': forms.Textarea(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base', 'rows': 4}),
        }

    # --- UPDATED __init__ METHOD ---
    def __init__(self, *args, **kwargs):
        # Pop the custom permission flag from kwargs
        can_edit = kwargs.pop('can_edit_full_plan', True) # Default to True
        super().__init__(*args, **kwargs)

        # Set the labels for choice fields
        self.fields['course_coordinator'].label_from_instance = lambda obj: f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})" if obj.user.first_name else obj.user.username
        self.fields['instructors'].label_from_instance = lambda obj: f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})" if obj.user.first_name else obj.user.username
        
        # If the user cannot edit, disable all the fields in this form
        if not can_edit:
            for field_name in self.fields:
                self.fields[field_name].disabled = True
                self.fields[field_name].widget.attrs['class'] += ' bg-gray-100 cursor-not-allowed'


class CourseObjectiveForm(forms.ModelForm):
    # --- NEW: Add this __init__ method ---
    def __init__(self, *args, **kwargs):
        can_edit = kwargs.pop('can_edit', True)  # Default to True
        super().__init__(*args, **kwargs)

        if not can_edit:
            for field_name in self.fields:
                self.fields[field_name].disabled = True
                self.fields[field_name].widget.attrs['class'] += ' bg-gray-100 cursor-not-allowed'

    class Meta:
        model = CourseObjective
        fields = ['order', 'unit_number', 'objective_text']
        widgets = {
            'order': forms.NumberInput(attrs={'class': 'mt-1 block w-16 px-2 py-1 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
            'unit_number': forms.TextInput(attrs={'class': 'mt-1 block w-24 px-2 py-1 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
            'objective_text': forms.Textarea(attrs={
                'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base', 
                'rows': 4}),
        }

# Formset for Course Objectives
CourseObjectiveFormSet = inlineformset_factory(
    CoursePlan,        # Parent model
    CourseObjective,   # Child model
    form=CourseObjectiveForm,
    extra=0,           # One empty form by default
    can_delete=True,   # Allow deleting objectives
    fields=['order', 'unit_number', 'objective_text']
)


class WeeklyLessonPlanForm(forms.ModelForm):
    class Meta:
        model = WeeklyLessonPlan
        fields = ['order', 'unit_number', 'unit_details', 'week_dates', 'pedagogy', 'references']
        widgets = {
            'order': forms.NumberInput(attrs={'class': 'mt-1 block w-16 px-2 py-1 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'}),
            'unit_number': forms.TextInput(attrs={'class': 'mt-1 block w-24 px-2 py-1 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'}),
            'unit_details': forms.Textarea(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base', 'rows': 4}),
            'week_dates': forms.TextInput(attrs={'class': 'mt-1 block w-full px-2 py-1 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base', 'placeholder': 'e.g., JULY 17TH - AUG 10TH'}),
            'pedagogy': forms.Textarea(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base', 'rows': 4}),
            'references': forms.Textarea(attrs={'class': 'mt-1 block w-full px-4 py- border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base', 'rows': 4}),
        }

# Formset for Weekly Lesson Plans
WeeklyLessonPlanFormSet = inlineformset_factory(
    CoursePlan,        # Parent model
    WeeklyLessonPlan,  # Child model
    form=WeeklyLessonPlanForm,
    extra=0,           # One empty form by default
    can_delete=True,   # Allow deleting entries
    fields=['order', 'unit_number', 'unit_details', 'week_dates', 'pedagogy', 'references']
)


class CIAComponentForm(forms.ModelForm):
     # --- UPDATED __init__ method ---
    def __init__(self, *args, **kwargs):
        # Pop the custom arguments from the kwargs
        cos_queryset = kwargs.pop('cos_queryset', None)
        can_edit = kwargs.pop('can_edit', True) # Add this line
        super().__init__(*args, **kwargs)

        # Apply the queryset filter if it exists
        if cos_queryset is not None:
            self.fields['cos_covered'].queryset = cos_queryset

        # Apply the disabled logic if user cannot edit
        if not can_edit: # Add this block
            for field_name in self.fields:
                self.fields[field_name].disabled = True
                self.fields[field_name].widget.attrs['class'] += ' bg-gray-100 cursor-not-allowed'

    class Meta:
        model = CIAComponent
        fields = ['order', 'component_name', 'units_covered', 'cos_covered']
        widgets = {
            'order': forms.NumberInput(attrs={'class': 'mt-1 block w-16 px-2 py-1 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
            'component_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
            'units_covered': forms.TextInput(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base', 'placeholder': 'e.g., UNIT 1 & 2'}),
            'cos_covered': forms.CheckboxSelectMultiple(attrs={'class': 'mt-1 block'}),
        }

# Formset for CIA Components
CIAComponentFormSet = inlineformset_factory(
    CoursePlan,     # Parent model
    CIAComponent,   # Child model
    form=CIAComponentForm,
    extra=0,        # One empty form by default
    can_delete=True, # Allow deleting components
    fields=['order', 'component_name', 'units_covered', 'cos_covered']
)


class StudentCreationForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
        }))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
        }))
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
        }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
        }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
        }), required=True)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), empty_label="Select Department", widget=forms.Select(attrs={
        "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
        }))

    # Add appropriate styling classes to the widgets as needed to match your project

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username
    

class AssignmentForm(forms.ModelForm):
    # Use a datetime-local widget for a better user experience in modern browsers
    due_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base'}),
        label="Due Date"
    )

    class Meta:
        model = Assignment
        fields = ['title', 'description', 'course', 'assignment_type', 'due_date', 'rubric', 'cia_component']
        # Apply standard styling to all widgets
        widgets = {
            'title': forms.TextInput(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
            'description': forms.Textarea(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm', 'rows': 4}),
            'course': forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
            'assignment_type': forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm', 'id': 'id_assignment_type'}),
            'rubric': forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
            'cia_component': forms.Select(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop the user object passed from the view to filter querysets
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'profile'):
            # Filter the 'course' dropdown to only show courses taught by this faculty member
            self.fields['course'].queryset = Course.objects.filter(faculty=user.profile)
            # Filter the 'rubric' dropdown to only show rubrics created by this faculty member
            self.fields['rubric'].queryset = Rubric.objects.filter(created_by=user.profile)
        
        # Make rubric and cia_component not required by default
        self.fields['rubric'].required = False
        self.fields['cia_component'].required = False


class RubricForm(forms.ModelForm):
    class Meta:
        model = Rubric
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
            'description': forms.Textarea(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm', 'rows': 3}),
        }

class RubricCriterionForm(forms.ModelForm):
    class Meta:
        model = RubricCriterion
        fields = ['criterion_text', 'max_score', 'order']
        widgets = {
            'criterion_text': forms.TextInput(attrs={'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
            'max_score': forms.NumberInput(attrs={'class': 'mt-1 block w-24 px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
            'order': forms.NumberInput(attrs={'class': 'mt-1 block w-24 px-4 py-2 border border-gray-300 rounded-lg shadow-sm'}),
        }

# Formset for adding multiple criteria to a rubric at once
RubricCriterionFormSet = inlineformset_factory(
    Rubric,
    RubricCriterion,
    form=RubricCriterionForm,
    extra=0, # Show 1 extra form by default
    can_delete=True,
    fields=['criterion_text', 'max_score', 'order']
)


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-brand-purple hover:file:bg-violet-100'})
        }


class GradingForm(forms.ModelForm):
    """Form for entering overall marks and feedback."""
    class Meta:
        model = Submission
        fields = ['marks_obtained', 'feedback']
        widgets = {
            'marks_obtained': forms.NumberInput(attrs={'class': 'mt-1 block w-full px-4 py-2 border ...'}),
            'feedback': forms.Textarea(attrs={'class': 'mt-1 block w-full px-4 py-2 border ...', 'rows': 4}),
        }
        labels = {
            'marks_obtained': 'Overall Marks',
            'feedback': 'General Feedback'
        }

class RubricScoreForm(forms.ModelForm):
    class Meta:
        model = RubricScore
        fields = ['score', 'criterion']
        widgets = {
            'score': forms.NumberInput(attrs={
                'class': 'block w-24 px-3 py-2 border border-gray-300 rounded-md shadow-sm'
            }),
            'criterion': forms.HiddenInput()  # This is critical
        }

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score')
        criterion = cleaned_data.get('criterion')

        if score is not None and criterion:
            max_score = criterion.max_score
            if score > max_score:
                raise forms.ValidationError(
                    f"Score cannot be greater than the maximum of {max_score}.",
                    code='score_too_high'
                )
        return cleaned_data




class StudentUpdateByFacultyForm(forms.ModelForm):
    # We define the fields we want to manage from both User and UserProfile models
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), empty_label="Select Department")

    class Meta:
        model = User # The form is based on the User model
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate the department field from the student's existing profile
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['department'].initial = self.instance.profile.department
        
        # Apply styling to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm'

    def save(self, commit=True):
        # Save the User model instance
        user = super().save(commit=commit)
        
        # Now, update the related UserProfile model
        user.profile.department = self.cleaned_data['department']
        
        if commit:
            user.profile.save()
            
        return user