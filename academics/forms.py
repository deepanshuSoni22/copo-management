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
)
from users.models import UserProfile, UserRole  # Import UserProfile from the users app
from django.forms import (
    inlineformset_factory,
    modelformset_factory,
)  # Import formset factories
from django.forms import modelformset_factory
from django.contrib.auth.models import User  # <--- ADD THIS LINE


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


class DepartmentForm(forms.ModelForm):
    # Customizing the HOD field to use a select widget for UserProfile objects
    # This also allows for custom styling via attrs
    hod = forms.ModelChoiceField(
        queryset=UserProfile.objects.filter(role="HOD").select_related(
            "user"
        ),  # Only show HOD profiles
        empty_label="No HOD assigned",  # Optional: allow no HOD
        required=False,  # HOD assignment is optional
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="Head of Department",
    )

    class Meta:
        model = Department
        fields = ["name", "hod"]
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
        self.fields["hod"].label_from_instance = lambda obj: (
            f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"
            if obj.user.first_name
            else obj.user.username
        )


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
        required=False,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="Department",
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all().order_by(
            "-start_date"
        ),  # Latest years first
        empty_label="Select Academic Year",
        required=False,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="Academic Year",
    )
    # The 'faculty' field is a ManyToMany, so ModelForm by default uses a MultipleSelect widget.
    # We can customize its queryset and appearance.
    faculty = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.filter(role=UserRole.FACULTY).select_related(
            "user"
        ),
        widget=forms.SelectMultiple(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base h-32"
            }
        ),  # Increased height for multiple selection
        label="Assigned Faculty",
        required=False,
        help_text="Hold Ctrl/Cmd to select multiple faculty.",
    )

    class Meta:
        model = Course
        fields = ["name", "code", "department", "academic_year", "faculty"]
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
        super().__init__(*args, **kwargs)
        self.fields["faculty"].label_from_instance = lambda obj: (
            f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"
            if obj.user.first_name
            else obj.user.username
        )


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
