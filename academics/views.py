# academics/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages  # For displaying feedback messages
from django.views.generic import View  # For class-based views if preferred
from django.http import JsonResponse # <-- Add this import at the top
from .forms import (
    AcademicYearForm,
    DepartmentForm,
    ProgramOutcomeForm,
    CourseForm,
    CourseOutcomeForm,
    AssessmentTypeForm,
    AssessmentForm,
    StudentMarkForm,
    StudentMarkFormSet,
    AcademicDepartmentForm,
    SemesterForm, CoursePlanForm, CourseObjectiveFormSet, WeeklyLessonPlanFormSet, CIAComponentFormSet, StudentCreationForm, RubricForm, RubricCriterionFormSet, AssignmentForm, RubricScore,
    SubmissionForm, GradingForm, RubricScoreForm, StudentUpdateByFacultyForm, EnrollStudentForm, BulkEnrollmentForm, CourseOutcomeFormSet
)  # Form

# Import models and forms
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
    CourseOutcomeAttainment,
    ProgramOutcomeAttainment,
    AcademicDepartment,
    Semester, CoursePlan, CourseObjective, WeeklyLessonPlan, CIAComponent, Rubric, RubricCriterion, Assignment, Submission
)
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db import transaction  # For atomic operations
from django.contrib.auth.models import User  # <--- ADD THIS LINE
from users.models import UserProfile, UserRole  # Import UserProfile from the users app
import csv  # Import the csv module for CSV export
from django.http import HttpResponse  # Import HttpResponse for serving files
from django.db.models import Q



# --- User Role Check Helper Functions ---
def is_admin(user):
    return user.is_authenticated and user.profile.role == "ADMIN"


def is_hod(user):
    return user.is_authenticated and user.profile.role == "HOD"


def is_faculty(user):
    return user.is_authenticated and user.profile.role in ['FACULTY', 'HOD']

def is_student(user):
    return user.is_authenticated and user.profile.role == "STUDENT"


# Test if user is Admin or Superuser (for managing Academic Years)
def is_admin_or_superuser(user):
    return user.is_superuser or (user.is_authenticated and user.profile.role == "ADMIN")


# --- Helper for Admin or HOD permission ---
def is_admin_or_hod(user):
    return user.is_authenticated and (
        user.is_superuser or user.profile.role in ["ADMIN", "HOD"]
    )


# --- New User Role Check Helper ---
def is_admin_or_hod_or_faculty(user):
    return user.is_authenticated and (
        user.is_superuser or user.profile.role in ["ADMIN", "HOD", "FACULTY"]
    )

from django.db.models import Max  # Ensure Max is imported for latest attainment


@login_required
def home_view(request):
    context = {}

    # --- Global Counts (for Admin/HOD) ---
    if request.user.is_superuser or request.user.profile.role in ["ADMIN", "HOD"]:
        context["total_academic_years"] = AcademicYear.objects.count()
        context["total_departments"] = Department.objects.count()
        context["total_courses"] = Course.objects.count()
        context["total_faculty"] = UserProfile.objects.filter(role="FACULTY").count()
        context["total_students"] = UserProfile.objects.filter(role="STUDENT").count()

        # Latest PO Attainment for dashboard overview
        latest_po_attainment_year_date = ProgramOutcomeAttainment.objects.aggregate(
            Max("academic_year__start_date")
        )["academic_year__start_date__max"]

        if latest_po_attainment_year_date:
            latest_po_academic_year = AcademicYear.objects.get(
                start_date=latest_po_attainment_year_date
            )

            latest_po_attainments = (
                ProgramOutcomeAttainment.objects.filter(
                    academic_year=latest_po_academic_year
                )
                .select_related("program_outcome", "academic_year")
                .order_by("program_outcome__code")
            )

            context["latest_po_attainments"] = latest_po_attainments

            # --- NEW: Data for Program Outcome Attainment Chart ---
            chart_labels = []
            chart_data = []
            for po_att in latest_po_attainments:
                chart_labels.append(po_att.program_outcome.code)
                # Use 0 if attainment is None for chart display
                chart_data.append(
                    float(po_att.attainment_percentage)
                    if po_att.attainment_percentage is not None
                    else 0
                )

            context["po_chart_labels"] = chart_labels
            context["po_chart_data"] = chart_data
            context["po_chart_year"] = (
                f"{latest_po_academic_year.start_date.year}-{latest_po_academic_year.end_date.year}"
            )
            # --- END NEW CHART DATA ---
        else:
            context["latest_po_attainments"] = None
            context["po_chart_labels"] = []  # Ensure empty lists if no data
            context["po_chart_data"] = []
            context["po_chart_year"] = "N/A"

    # --- Faculty Specific Data ---
    if (
        request.user.profile.role == "FACULTY"
        and not request.user.is_superuser
        and request.user.profile.role not in ["ADMIN", "HOD"]
    ):
        context["faculty_taught_courses_count"] = (
            request.user.profile.taught_courses.count()
        )

    # --- Student Specific Data ---
    if request.user.profile.role == "STUDENT":
        pass

    # --- NEW: HOD Specific Data ---
    if request.user.profile.role == 'HOD':
        # Retrieve the AcademicDepartment this HOD is heading
        # UserProfile.academic_department_headed (related_name) links to AcademicDepartment.hod
        try:
            hod_department_instance = AcademicDepartment.objects.select_related('department', 'academic_year').get(hod=request.user.profile)
            context['hod_department'] = hod_department_instance
        except AcademicDepartment.DoesNotExist:
            context['hod_department'] = None
            messages.warning(request, "Your HOD profile is not currently assigned to any Academic Department. Please contact an Admin.")
        except AcademicDepartment.MultipleObjectsReturned: # Should not happen with OneToOneField
            context['hod_department'] = None
            messages.error(request, "Multiple Academic Departments found for your HOD profile. Data inconsistency detected!")
    
    if request.user.profile.role == 'FACULTY':
        faculty_profile = request.user.profile
        context['faculty_department'] = faculty_profile.department

    return render(request, "home.html", context)


# --- Academic Year Management Views ---


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def academic_year_list(request):
    academic_years = AcademicYear.objects.all().order_by("-start_date")
    return render(
        request, "academics/academic_year_list.html", {"academic_years": academic_years}
    )


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def academic_year_create(request):
    if request.method == "POST":
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic Year created successfully!")
            return redirect("academic_year_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AcademicYearForm()
    return render(
        request,
        "academics/academic_year_form.html",
        {"form": form, "form_title": "Create Academic Year"},
    )


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def academic_year_update(request, pk):
    academic_year = get_object_or_404(AcademicYear, pk=pk)
    if request.method == "POST":
        form = AcademicYearForm(request.POST, instance=academic_year)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic Year updated successfully!")
            return redirect("academic_year_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AcademicYearForm(instance=academic_year)
    return render(
        request,
        "academics/academic_year_form.html",
        {"form": form, "form_title": "Update Academic Year"},
    )


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def academic_year_delete(request, pk):
    academic_year = get_object_or_404(AcademicYear, pk=pk)
    if request.method == "POST":
        academic_year.delete()
        messages.success(request, "Academic Year deleted successfully!")
        return redirect("academic_year_list")
    # If accessed via GET, render a confirmation page (optional, but good UX)
    return render(
        request,
        "academics/academic_year_confirm_delete.html",
        {"academic_year": academic_year},
    )


# (Continue with Department views later in this file)


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def department_list(request):
    departments = Department.objects.all().order_by('name')
    return render(
        request, "academics/department_list.html", {"departments": departments}
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def department_create(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created successfully!")
            return redirect("department_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DepartmentForm()
    return render(
        request,
        "academics/department_form.html",
        {"form": form, "form_title": "Create Department"},
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def department_update(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully!")
            return redirect("department_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DepartmentForm(instance=department)
    return render(
        request,
        "academics/department_form.html",
        {"form": form, "form_title": "Update Department"},
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        department.delete()
        messages.success(request, "Department deleted successfully!")
        return redirect("department_list")
    return render(
        request, "academics/department_confirm_delete.html", {"department": department}
    )


# --- AcademicDepartment Management Views (Admin/HOD) ---

@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/') # Admin or HOD can manage AcademicDepartments
def academic_department_list(request):
    academic_departments = AcademicDepartment.objects.all().select_related('department', 'academic_year', 'hod__user').order_by('-academic_year__start_date', 'department__name')
    
    can_manage_depts = is_admin(request.user)

    context = {
        'academic_departments': academic_departments,
        'form_title': 'Academic Departments',
        'can_manage_depts': can_manage_depts, # Pass the flag to the template
    }
    return render(request, 'academics/academic_department_list.html', context)

@login_required
@user_passes_test(is_admin, login_url='/accounts/login/')
def academic_department_create(request):
    if request.method == 'POST':
        form = AcademicDepartmentForm(request.POST)
        if form.is_valid():
            academic_department = form.save()
            messages.success(request, f'Academic Department "{academic_department.department.name} - {academic_department.academic_year.start_date.year}" created successfully!')
            return redirect('academic_department_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # NEW: Check for academic_year_id in GET parameters to pre-populate
        initial_data = {}
        academic_year_id = request.GET.get('academic_year_id')
        if academic_year_id:
            try:
                academic_year_obj = AcademicYear.objects.get(pk=academic_year_id)
                initial_data['academic_year'] = academic_year_obj
            except AcademicYear.DoesNotExist:
                messages.error(request, "Selected Academic Year does not exist.")
        
        form = AcademicDepartmentForm(initial=initial_data) # Pass initial data to the form
    
    context = {
        'form': form,
        'form_title': 'Create New Academic Department',
    }
    return render(request, 'academics/academic_department_form.html', context)

@login_required
@user_passes_test(is_admin, login_url='/accounts/login/')
def academic_department_update(request, pk):
    academic_department = get_object_or_404(AcademicDepartment, pk=pk)
    if request.method == 'POST':
        form = AcademicDepartmentForm(request.POST, instance=academic_department)
        if form.is_valid():
            academic_department = form.save()
            messages.success(request, f'Academic Department "{academic_department.department.name} - {academic_department.academic_year.start_date.year}" updated successfully!')
            return redirect('academic_department_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AcademicDepartmentForm(instance=academic_department)
    context = {
        'form': form,
        'form_title': f'Update Academic Department: {academic_department.department.name} - {academic_department.academic_year.start_date.year}',
    }
    return render(request, 'academics/academic_department_form.html', context)

@login_required
@user_passes_test(is_admin, login_url='/accounts/login/')
def academic_department_delete(request, pk):
    academic_department = get_object_or_404(AcademicDepartment, pk=pk)
    if request.method == 'POST':
        academic_department.delete()
        messages.success(request, f'Academic Department "{academic_department.department.name} - {academic_department.academic_year.start_date.year}" deleted successfully!')
        return redirect('academic_department_list')
    context = {
        'academic_department': academic_department,
    }
    return render(request, 'academics/academic_department_confirm_delete.html', context)


# --- Semester Management Views (Admin/HOD) ---

@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/') # Admin or HOD can manage Semesters
def semester_list(request):
    # Base queryset for all semesters, optimized for related lookups
    semesters = Semester.objects.all().select_related('academic_department__department', 'academic_department__academic_year').order_by('-academic_department__academic_year__start_date', 'order')

    # NEW: Filter semesters based on user role
    if request.user.profile.role == 'HOD':
        try:
            # Get the AcademicDepartment instance this HOD is assigned to
            hod_academic_department = AcademicDepartment.objects.get(hod=request.user.profile)
            # Filter semesters to only those belonging to this HOD's AcademicDepartment
            semesters = semesters.filter(academic_department=hod_academic_department)
        except AcademicDepartment.DoesNotExist:
            # If an HOD is not assigned to any AcademicDepartment, they see no semesters
            semesters = Semester.objects.none() # Return an empty queryset
            messages.warning(request, "Your HOD profile is not assigned to an Academic Department. No semesters displayed.")
        except AcademicDepartment.MultipleObjectsReturned:
            # Should not happen with OneToOneField, but good to handle
            semesters = Semester.objects.none()
            messages.error(request, "Data inconsistency: HOD assigned to multiple Academic Departments. Please contact an Admin.")
    # Admins (user.is_superuser or user.profile.role == 'ADMIN') will bypass this 'if' block and see all semesters.

    # NEW: Get all departments for filter dropdown (if filtering is enabled for Admin)
    departments = Department.objects.all().order_by('name')
    selected_department_id = request.GET.get('department') # Get selected department ID from GET param

    # NEW: Apply filter by department if selected by Admin (only if Admin)
    if (request.user.is_superuser or request.user.profile.role == 'ADMIN') and selected_department_id:
        semesters = semesters.filter(academic_department__department__id=selected_department_id)


    context = {
        'semesters': semesters,
        'form_title': 'Semesters',
        'departments': departments, # Pass departments for the filter dropdown
        'selected_department_id': selected_department_id, # Pass selected ID to pre-select dropdown
    }
    return render(request, 'academics/semester_list.html', context)

@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/')
def semester_create(request):
    # Determine if user is HOD and get their AcademicDepartment
    hod_academic_department = None
    if request.user.profile.role == 'HOD':
        try:
            # Assumes an HOD is assigned to one AcademicDepartment
            hod_academic_department = AcademicDepartment.objects.get(hod=request.user.profile)
        except AcademicDepartment.DoesNotExist:
            messages.error(request, "Your HOD profile is not assigned to an Academic Department. Cannot create semester.")
            return redirect('semester_list') # Redirect if HOD has no assigned department
        except AcademicDepartment.MultipleObjectsReturned:
            messages.error(request, "Data inconsistency: HOD assigned to multiple Academic Departments.")
            return redirect('semester_list')

    if request.method == 'POST':
        # Pass the request object to the form, as it needs to know the user for disabling logic
        form = SemesterForm(request.POST, request=request) 
        if form.is_valid():
            semester = form.save(commit=False) # Get instance to assign academic_department if needed
            # If HOD, ensure semester belongs to their AcademicDepartment (in case field was disabled)
            if request.user.profile.role == 'HOD' and hod_academic_department:
                semester.academic_department = hod_academic_department # Force assignment
            semester.save()

            messages.success(request, f'Semester "{semester.name}" for {semester.academic_department.department.name} - {semester.academic_department.academic_year.start_date.year} created successfully!')
            return redirect('semester_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else: # GET request
        initial_data = {}
        if request.user.profile.role == 'HOD' and hod_academic_department:
            initial_data['academic_department'] = hod_academic_department # Pre-select HOD's department
        
        # Pass initial data AND the request object to the form
        form = SemesterForm(initial=initial_data, request=request) 
    
    context = {
        'form': form,
        'form_title': 'Create New Semester',
    }
    return render(request, 'academics/semester_form.html', context)

@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/')
def semester_update(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == 'POST':
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            semester = form.save()
            messages.success(request, f'Semester "{semester.name}" for {semester.academic_department.department.name} - {semester.academic_department.academic_year.start_date.year} updated successfully!')
            return redirect('semester_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SemesterForm(instance=semester)
    
    context = {
        'form': form,
        'form_title': f'Update Semester: {semester.name}',
    }
    return render(request, 'academics/semester_form.html', context)

@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/')
def semester_delete(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == 'POST':
        semester.delete()
        messages.success(request, f'Semester "{semester.name}" deleted successfully!')
        return redirect('semester_list')
    context = {
        'semester': semester,
    }
    return render(request, 'academics/semester_confirm_delete.html', context)


# --- CoursePlan Management Views (HOD/Admin) ---

@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url='/accounts/login/')
def course_plan_list(request):
    # Base queryset
    course_plans = CoursePlan.objects.all().select_related(
        'course__semester__academic_department__academic_year',
        'course_coordinator__user'
    ).prefetch_related('instructors__user')

    user_profile = request.user.profile

    # Filter for HODs
    if user_profile.role == 'HOD':
        try:
            hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
            course_plans = course_plans.filter(course__semester__academic_department=hod_academic_department)
        except AcademicDepartment.DoesNotExist:
            course_plans = CoursePlan.objects.none()

    # --- NEW: Filter for Faculty ---
    elif user_profile.role == 'FACULTY':
        # Show plans where the user is either the coordinator OR in the list of instructors
        course_plans = course_plans.filter(
            Q(course_coordinator=user_profile) | Q(instructors=user_profile)
        ).distinct()

    # Admins see all plans, so no filter is applied for them.

    context = {
        'course_plans': course_plans.order_by('-course__semester__academic_department__academic_year__start_date', 'course__code'),
        'form_title': 'Course Plans',
    }
    # Remember to import Q from django.db.models at the top of your views.py
    # from django.db.models import Q
    return render(request, 'academics/course_plan_list.html', context)


@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/')
def course_plan_create(request):
    course_id = request.GET.get('course_id')
    pre_selected_course = None
    if course_id:
        try:
            pre_selected_course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            messages.error(request, "Selected Course does not exist.")
            return redirect('course_list')

    # --- NEW: Get the correct queryset for this course's outcomes ---
    # We do this here to pass it to the formset below.
    course_outcomes_for_this_course = CourseOutcome.objects.filter(course=pre_selected_course) if pre_selected_course else CourseOutcome.objects.none()

    if request.method == 'POST':
        course_plan_form = CoursePlanForm(request.POST)
        course_objective_formset = CourseObjectiveFormSet(request.POST, prefix='objectives')
        weekly_lesson_formset = WeeklyLessonPlanFormSet(request.POST, prefix='lessons')
        # -- UPDATED: Pass form_kwargs to the formset on POST --
        cia_component_formset = CIAComponentFormSet(
            request.POST,
            prefix='cia_components',
            form_kwargs={'cos_queryset': course_outcomes_for_this_course}
        )

        if (course_plan_form.is_valid() and
                course_objective_formset.is_valid() and
                weekly_lesson_formset.is_valid() and
                cia_component_formset.is_valid()):
            
            with transaction.atomic():
                # Logic remains the same...
                course_plan = course_plan_form.save(commit=False)
                course_plan.created_by = request.user
                if pre_selected_course:
                    course_plan.course = pre_selected_course
                course_plan.save()

                course_objective_formset.instance = course_plan
                course_objective_formset.save()

                weekly_lesson_formset.instance = course_plan
                weekly_lesson_formset.save()

                cia_component_formset.instance = course_plan
                cia_component_formset.save()

                messages.success(request, f"Course Plan for '{course_plan.course.code}' created successfully!")
                return redirect('course_plan_list')
        else:
            messages.error(request, 'Please correct the errors in the forms below.')
    else:  # GET request
        course_plan_form = CoursePlanForm(initial={'course': pre_selected_course})
        course_objective_formset = CourseObjectiveFormSet(prefix='objectives')
        weekly_lesson_formset = WeeklyLessonPlanFormSet(prefix='lessons')
        # -- UPDATED: Pass form_kwargs to the formset on GET --
        cia_component_formset = CIAComponentFormSet(
            prefix='cia_components',
            form_kwargs={'cos_queryset': course_outcomes_for_this_course}
        )
    
    context = {
        'course_plan_form': course_plan_form,
        'course_objective_formset': course_objective_formset,
        'weekly_lesson_formset': weekly_lesson_formset,
        'cia_component_formset': cia_component_formset,
        'form_title': 'Create Course Plan',
        'pre_selected_course': pre_selected_course,
        
        # --- FIX: Add these permission flags to the context ---
        'can_edit_full_plan': True,
        'can_edit_weekly_lessons': True,
    }
    return render(request, 'academics/course_plan_form.html', context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url='/accounts/login/')
def course_plan_update(request, pk):
    course_plan = get_object_or_404(CoursePlan, pk=pk)
    user_profile = request.user.profile

    is_hod_or_admin = user_profile.role in ['HOD', 'ADMIN'] or request.user.is_superuser
    is_course_instructor = user_profile == course_plan.course_coordinator or user_profile in course_plan.instructors.all()

    # --- START OF NEW LOGIC ---
    # This new flag determines who can edit the core components of the plan.
    can_edit_main_components = is_hod_or_admin or is_course_instructor
    # --- END OF NEW LOGIC ---

    if not can_edit_main_components: # Simplified permission check
        messages.error(request, "You do not have permission to update this Course Plan.")
        return redirect('course_plan_list')

    if user_profile.role == 'HOD':
        try:
            hod_academic_department = AcademicDepartment.objects.get(hod=user_profile)
            if course_plan.course.semester.academic_department != hod_academic_department:
                messages.error(request, "You can only update Course Plans for your own department.")
                return redirect('course_plan_list')
        except AcademicDepartment.DoesNotExist:
            messages.error(request, "Your HOD profile is not assigned to an Academic Department.")
            return redirect('course_plan_list')
            
    course_outcomes_for_this_course = CourseOutcome.objects.filter(course=course_plan.course)
    # Define the form kwargs dictionary based on permission
    objective_and_cia_kwargs = {'can_edit': can_edit_main_components}
    cia_kwargs = {'cos_queryset': course_outcomes_for_this_course, 'can_edit': can_edit_main_components}

    if request.method == 'POST':
        form = CoursePlanForm(request.POST, instance=course_plan, can_edit_full_plan=is_hod_or_admin)
        # Pass kwargs to formsets during POST as well
        objective_formset = CourseObjectiveFormSet(request.POST, instance=course_plan, prefix='objectives', form_kwargs=objective_and_cia_kwargs)
        lesson_formset = WeeklyLessonPlanFormSet(request.POST, instance=course_plan, prefix='lessons') # No permissions needed here
        cia_formset = CIAComponentFormSet(request.POST, instance=course_plan, prefix='cia_components', form_kwargs=cia_kwargs)

        # --- UPDATED: Simplified validation logic ---
        forms_to_validate = []
        forms_to_save = []

        if is_hod_or_admin:
            # Admins/HODs validate and save everything
            forms_to_validate = [form, objective_formset, lesson_formset, cia_formset]
            forms_to_save = [form, objective_formset, lesson_formset, cia_formset]
        elif is_course_instructor:
            # Faculty instructors validate and save their permitted sections
            forms_to_validate = [objective_formset, lesson_formset, cia_formset]
            forms_to_save = [objective_formset, lesson_formset, cia_formset]

        all_forms_valid = all(f.is_valid() for f in forms_to_validate)

        if all_forms_valid:
            with transaction.atomic():
                # Loop through and save all the forms that were designated for saving
                for f in forms_to_save:
                    f.save()
            messages.success(request, f"Course Plan for '{course_plan.course.code}' updated successfully!")
            return redirect('course_plan_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:  # GET request
        form = CoursePlanForm(instance=course_plan, can_edit_full_plan=is_hod_or_admin)
        # --- UPDATED: Pass form_kwargs to the relevant formsets ---
        objective_formset = CourseObjectiveFormSet(instance=course_plan, prefix='objectives', form_kwargs=objective_and_cia_kwargs)
        lesson_formset = WeeklyLessonPlanFormSet(instance=course_plan, prefix='lessons') # Remains editable
        cia_formset = CIAComponentFormSet(instance=course_plan, prefix='cia_components', form_kwargs=cia_kwargs)

    # --- UPDATED: Conditional form title ---
    if is_hod_or_admin:
        title = f'Update Course Plan for {course_plan.course.code}'
    else:
        title = f'View/Edit Course Plan for {course_plan.course.code}'

    context = {
        'course_plan_form': form,
        'course_objective_formset': objective_formset,
        'weekly_lesson_formset': lesson_formset,
        'cia_component_formset': cia_formset,
        'form_title': title, # Use the new conditional title
        'pre_selected_course': course_plan.course,
        'can_edit_full_plan': is_hod_or_admin,
        'can_edit_weekly_lessons': can_edit_main_components,
    }
    return render(request, 'academics/course_plan_form.html', context)

@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/')
def course_plan_delete(request, pk):
    course_plan = get_object_or_404(CoursePlan, pk=pk)

    # Permission check: HOD can only delete plans for their department
    if request.user.profile.role == 'HOD':
        try:
            hod_academic_department = AcademicDepartment.objects.get(hod=request.user.profile)
            if course_plan.course.semester.academic_department != hod_academic_department:
                messages.error(request, "You do not have permission to delete this Course Plan.")
                return redirect('course_plan_list')
        except AcademicDepartment.DoesNotExist:
            messages.error(request, "Your HOD profile is not assigned to an Academic Department.")
            return redirect('course_plan_list')

    if request.method == 'POST':
        course_code = course_plan.course.code
        course_plan.delete()
        messages.success(request, f"Course Plan for '{course_code}' deleted successfully.")
        return redirect('course_plan_list')
    
    context = {
        'course_plan': course_plan,
    }
    return render(request, 'academics/course_plan_confirm_delete.html', context)


# --- Program Outcome Management Views ---


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def program_outcome_list(request):
    program_outcomes = ProgramOutcome.objects.all().select_related('department')
    departments_for_filter = Department.objects.all().order_by('name')

    # If user is an HOD, filter to their department only
    if is_hod(request.user):
        program_outcomes = program_outcomes.filter(department=request.user.profile.department)

    # --- START: NEW FILTER LOGIC ---
    selected_department_id = request.GET.get('department')
    if selected_department_id:
        program_outcomes = program_outcomes.filter(department_id=selected_department_id)
    # --- END: NEW FILTER LOGIC ---
    
    context = {
        "program_outcomes": program_outcomes.order_by("department__name", "code"),
        "departments": departments_for_filter, # For the admin's filter dropdown
        "selected_department_id": selected_department_id, # To keep the filter selection
        "form_title": "Program Outcomes"
    }
    return render(request, "academics/program_outcome_list.html", context)


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def program_outcome_create(request):
    if request.method == "POST":
        form = ProgramOutcomeForm(request.POST, user=request.user)
        if form.is_valid():
            form.save() # The form's clean() method handles HOD logic
            messages.success(request, "Program Outcome created successfully!")
            return redirect("program_outcome_list")
    else:
        form = ProgramOutcomeForm(user=request.user)

    return render(
        request,
        "academics/program_outcome_form.html",
        {"form": form, "form_title": "Create Program Outcome"},
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def program_outcome_update(request, pk):
    program_outcome = get_object_or_404(ProgramOutcome, pk=pk)

    # HOD can only edit POs in their own department
    if is_hod(request.user) and program_outcome.department != request.user.profile.department:
        messages.error(request, "You do not have permission to edit this Program Outcome.")
        return redirect("program_outcome_list")

    if request.method == "POST":
        form = ProgramOutcomeForm(request.POST, instance=program_outcome, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Program Outcome updated successfully!")
            return redirect("program_outcome_list")
    else:
        form = ProgramOutcomeForm(instance=program_outcome, user=request.user)
        
    return render(
        request,
        "academics/program_outcome_form.html",
        {"form": form, "form_title": "Update Program Outcome"},
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def program_outcome_delete(request, pk):
    program_outcome = get_object_or_404(ProgramOutcome, pk=pk)

    # HOD can only delete POs in their own department
    if is_hod(request.user) and program_outcome.department != request.user.profile.department:
        messages.error(request, "You do not have permission to delete this Program Outcome.")
        return redirect("program_outcome_list")

    if request.method == "POST":
        program_outcome.delete()
        messages.success(request, "Program Outcome deleted successfully!")
        return redirect("program_outcome_list")

    return render(
        request,
        "academics/program_outcome_confirm_delete.html",
        {"program_outcome": program_outcome},
    )


# --- Course Management Views ---


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url='/accounts/login/')
def course_list(request):
    user_profile = request.user.profile

    # --- START: CORRECTED PERMISSION LOGIC ---
    # Determine the base queryset for courses and filters based on user role
    if is_admin(user_profile.user):
        # Admins see all courses and can filter by any department/semester
        courses_qs = Course.objects.all()
        semesters_qs = Semester.objects.all()
        departments_qs = Department.objects.all()
    elif is_hod(user_profile.user):
        # HODs see courses in their department and can filter by semesters in their department
        try:
            hod_academic_dept = AcademicDepartment.objects.get(hod=user_profile)
            department = hod_academic_dept.department
            
            courses_qs = Course.objects.filter(department=department)
            semesters_qs = Semester.objects.filter(academic_department=hod_academic_dept)
            departments_qs = Department.objects.filter(pk=department.pk)
        except AcademicDepartment.DoesNotExist:
            messages.warning(request, "Your HOD profile is not assigned to an Academic Department.")
            courses_qs = semesters_qs = departments_qs = Course.objects.none() # Show nothing
    else: # is_faculty
        # Faculty ONLY see courses they are assigned to
        courses_qs = user_profile.taught_courses.all()
        # The filters should only show relevant departments and semesters
        taught_course_semesters = courses_qs.values_list('semester', flat=True).distinct()
        taught_course_depts = courses_qs.values_list('department', flat=True).distinct()
        semesters_qs = Semester.objects.filter(pk__in=taught_course_semesters)
        departments_qs = Department.objects.filter(pk__in=taught_course_depts)
    # --- END: CORRECTED PERMISSION LOGIC ---

    # Apply filters from GET parameters
    selected_semester_id = request.GET.get('semester')
    selected_department_id = request.GET.get('department')

    if selected_department_id:
        courses_qs = courses_qs.filter(department__id=selected_department_id)
    if selected_semester_id:
        courses_qs = courses_qs.filter(semester__id=selected_semester_id)

    context = {
        'courses': courses_qs.select_related('department', 'semester__academic_department__academic_year').prefetch_related('faculty__user').order_by('code'),
        'form_title': 'Courses',
        'semesters': semesters_qs.order_by('-academic_department__academic_year__start_date', 'order'),
        'departments': departments_qs.order_by('name'),
        'selected_semester_id': selected_semester_id,
        'selected_department_id': selected_department_id,
    }
    return render(request, 'academics/course_list.html', context)


@login_required
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/')
def course_create(request):
    # Determine if user is HOD and get their AcademicDepartment (and thus their Department)
    hod_assigned_department = None
    if request.user.profile.role == 'HOD':
        try:
            # Get the AcademicDepartment instance this HOD is assigned to
            # This links them to a specific Department for a specific Academic Year
            hod_academic_department_instance = AcademicDepartment.objects.select_related('department').get(hod=request.user.profile)
            hod_assigned_department = hod_academic_department_instance.department # Get the generic Department object
        except AcademicDepartment.DoesNotExist:
            messages.error(request, "Your HOD profile is not assigned to an Academic Department. Cannot create courses for a specific department.")
            return redirect('course_list') # Redirect if HOD has no assigned department
        except AcademicDepartment.MultipleObjectsReturned:
            messages.error(request, "Data inconsistency: HOD assigned to multiple Academic Departments.")
            return redirect('course_list')

    # Prepare initial data for the form. This can include pre-filling semester from URL, etc.
    initial_data = {}
    semester_id = request.GET.get('semester_id')
    if semester_id:
        try:
            semester_obj = Semester.objects.get(pk=semester_id)
            initial_data['semester'] = semester_obj
        except Semester.DoesNotExist:
            messages.error(request, "Selected Semester does not exist.")
    
    # If HOD, pre-fill department and set flag to disable it
    if request.user.profile.role == 'HOD' and hod_assigned_department:
        initial_data['department'] = hod_assigned_department

    if request.method == 'POST':
        # Pass the request object to the form, as it needs to know the user for disabling logic
        form = CourseForm(request.POST, request=request)
        if form.is_valid():
            course = form.save()
            
            messages.success(request, f'Course "{course.code} - {course.name}" created successfully! You can now add its outcomes.')
            return redirect('course_update', pk=course.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else: # GET request
        # Pass initial data and request object to the form
        form = CourseForm(initial=initial_data, request=request)
    
    context = {
        'form': form,
        'form_title': 'Create New Course',
    }
    return render(request, 'academics/course_form.html', context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url='/accounts/login/')
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    user_profile = request.user.profile

     # --- START: NEW PERMISSION LOGIC ---
    # Check if the user has permission to be on this page at all.
    is_admin_or_hod_user = is_admin(user_profile.user) or is_hod(user_profile.user)
    is_assigned_faculty = user_profile in course.faculty.all()
  
    if not (is_admin_or_hod_user or is_assigned_faculty):
        messages.error(request, 'You do not have permission to view this course.')
        return redirect('course_list')
    # --- END: NEW PERMISSION LOGIC ---

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course, request=request)
        formset = CourseOutcomeFormSet(request.POST, instance=course, prefix='outcomes')

        if form.is_valid() and formset.is_valid():
            with transaction.atomic(): # Use a transaction for data integrity
                form.save()
                formset.save()
                messages.success(request, f'Course "{course.code} - {course.name}" updated successfully!')
                return redirect('course_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm(instance=course, request=request)
        formset = CourseOutcomeFormSet(instance=course, prefix='outcomes')
        # Prefilter course choices for faculty users (existing logic)

    context = {
        'form': form,
        'outcome_formset': formset, # <-- Add formset to context
        'form_title': 'Update Course',
    }
    return render(request, 'academics/course_form.html', context)


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        course.delete()
        messages.success(
            request, f'Course "{course.code} - {course.name}" deleted successfully!'
        )
        return redirect("course_list")
    return render(request, "academics/course_confirm_delete.html", {"course": course})


# --- Course Outcome Management Views ---


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def course_outcome_list(request):
    user_profile = request.user.profile
    
    # --- START OF NEW LOGIC ---
    # Determine the base querysets for filtering and listing, based on user role
    if is_admin(request.user) or is_hod(request.user):
        # Admin/HOD can see all courses and COs
        courses_for_filter = Course.objects.all().order_by("code")
        course_outcomes = CourseOutcome.objects.all()
    else: # is_faculty
        # Faculty can only see courses they teach and COs for those courses
        taught_courses = user_profile.taught_courses.all()
        courses_for_filter = taught_courses.order_by("code")
        course_outcomes = CourseOutcome.objects.filter(course__in=taught_courses)

    # Get the selected course ID from the URL's GET parameters
    selected_course_id = request.GET.get('course')

    # If a course is selected in the filter, apply it to the queryset
    if selected_course_id:
        course_outcomes = course_outcomes.filter(course_id=selected_course_id)
    # --- END OF NEW LOGIC ---

    can_manage_outcomes = is_admin(request.user) or is_hod(request.user)

    context = {
        # Optimize the final query and pass it to the context
        'course_outcomes': course_outcomes.select_related("course").prefetch_related('po_mappings__program_outcome').order_by("course__code", "code"),
        # Pass the necessary data for the filter dropdown
        'all_courses': courses_for_filter,
        'selected_course_id': selected_course_id,
        'form_title': 'Course Outcomes', # Add form_title to context
        'can_manage_outcomes': can_manage_outcomes, # <-- Pass flag to template
    }
    return render(request, "academics/course_outcome_list.html", context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def course_outcome_create(request):
    if request.method == "POST":
        form = CourseOutcomeForm(request.POST)
        if form.is_valid():
            # If user is faculty, ensure they are assigned to the selected course
            if is_faculty(request.user) and not is_admin_or_hod(request.user):
                if (
                    form.cleaned_data["course"]
                    not in request.user.profile.taught_courses.all()
                ):
                    messages.error(
                        request,
                        "You can only create outcomes for courses you are assigned to.",
                    )
                    return render(
                        request,
                        "academics/course_outcome_form.html",
                        {"form": form, "form_title": "Create Course Outcome"},
                    )

            co = form.save()
            messages.success(
                request,
                f'Course Outcome "{co.code}" for {co.course.code} created successfully!',
            )
            return redirect("course_outcome_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CourseOutcomeForm()
        # If user is faculty, pre-filter courses in the form
        if is_faculty(request.user) and not is_admin_or_hod(request.user):
            form.fields["course"].queryset = (
                request.user.profile.taught_courses.all().order_by("code")
            )

    return render(
        request,
        "academics/course_outcome_form.html",
        {"form": form, "form_title": "Create Course Outcome"},
    )


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def course_outcome_delete(request, pk):
    co = get_object_or_404(CourseOutcome, pk=pk)

    # Permission check: Faculty can only delete COs for courses they teach
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if co.course not in request.user.profile.taught_courses.all():
            messages.error(
                request, "You do not have permission to delete this Course Outcome."
            )
            return redirect("course_outcome_list")

    if request.method == "POST":
        co.delete()
        messages.success(
            request,
            f'Course Outcome "{co.code}" for {co.course.code} deleted successfully!',
        )
        return redirect("course_outcome_list")
    return render(
        request, "academics/course_outcome_confirm_delete.html", {"course_outcome": co}
    )


# --- CO-PO Mapping View ---


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def copo_mapping_view(request, co_pk):
    course_outcome = get_object_or_404(CourseOutcome, pk=co_pk)

    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if course_outcome.course not in request.user.profile.taught_courses.all():
            messages.error(request, "You do not have permission to modify mappings for this Course Outcome.")
            return redirect("course_outcome_list")

    # --- THIS IS THE FIX ---
    # Filter Program Outcomes to only those in the same department as the Course Outcome
    all_program_outcomes = ProgramOutcome.objects.filter(
        department=course_outcome.course.department
    ).order_by("code")
    # --- END OF FIX ---

    if request.method == "POST":
        print(request.POST)  # Temporarily inspect POST data
        with transaction.atomic():
            # 1. Delete all existing mappings for this CO first.
            COPOMapping.objects.filter(course_outcome=course_outcome).delete()

            # 2. Loop through all POs and create new mappings for those that have a level selected.
            for po in all_program_outcomes:
                field_name = f"correlation_level_{po.id}"
                submitted_level_list = request.POST.getlist(field_name)
                submitted_level_str = submitted_level_list[0] if submitted_level_list else None
                # --- THIS IS THE CORRECTED LOGIC ---
                # Check if the submitted value is a valid integer (1, 2, or 3)
                if submitted_level_str and submitted_level_str in ['1', '2', '3']:
                    COPOMapping.objects.create(
                        course_outcome=course_outcome,
                        program_outcome=po,
                        correlation_level=int(submitted_level_str)
                    )
                    print(f"✅ Created mapping: CO={course_outcome.code}, PO={po.code}, Level={submitted_level_str}")  # 🐛 Confirm mapping creation
        
        messages.success(request, f"CO-PO mappings for {course_outcome.code} updated successfully!")
        return redirect("course_outcome_list")

    else:  # GET request
        existing_mappings = COPOMapping.objects.filter(course_outcome=course_outcome)
        existing_mappings_dict = {m.program_outcome_id: m.correlation_level for m in existing_mappings}

        context = {
            "course_outcome": course_outcome,
            "all_program_outcomes": all_program_outcomes,
            "correlation_choices": CorrelationLevel.choices,
            "existing_mappings_dict": existing_mappings_dict,
            "form_title": f"Map CO-PO: {course_outcome.code}"
        }
        return render(request, "academics/copo_mapping_form.html", context)


# --- Assessment Type Management Views ---


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def assessment_type_list(request):
    assessment_types = AssessmentType.objects.all().order_by("name")
    return render(
        request,
        "academics/assessment_type_list.html",
        {"assessment_types": assessment_types},
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def assessment_type_create(request):
    if request.method == "POST":
        form = AssessmentTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Assessment Type "{form.cleaned_data["name"]}" created successfully!',
            )
            return redirect("assessment_type_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssessmentTypeForm()
    return render(
        request,
        "academics/assessment_type_form.html",
        {"form": form, "form_title": "Create Assessment Type"},
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def assessment_type_update(request, pk):
    assessment_type = get_object_or_404(AssessmentType, pk=pk)
    if request.method == "POST":
        form = AssessmentTypeForm(request.POST, instance=assessment_type)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Assessment Type "{form.cleaned_data["name"]}" updated successfully!',
            )
            return redirect("assessment_type_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssessmentTypeForm(instance=assessment_type)
    return render(
        request,
        "academics/assessment_type_form.html",
        {"form": form, "form_title": "Update Assessment Type"},
    )


@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def assessment_type_delete(request, pk):
    assessment_type = get_object_or_404(AssessmentType, pk=pk)
    if request.method == "POST":
        assessment_type.delete()
        messages.success(
            request, f'Assessment Type "{assessment_type.name}" deleted successfully!'
        )
        return redirect("assessment_type_list")
    return render(
        request,
        "academics/assessment_type_confirm_delete.html",
        {"assessment_type": assessment_type},
    )


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def assessment_list(request):
    # Filter assessments based on user role
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        user_profile = request.user.profile
        taught_courses = user_profile.taught_courses.all()
        assessments = (
            Assessment.objects.filter(course__in=taught_courses)
            .select_related("course", "academic_year", "assessment_type")
            .prefetch_related("assesses_cos")
            .order_by("-academic_year__start_date", "course__code", "date")
        )
    else:  # Admin or HOD sees all
        assessments = (
            Assessment.objects.all()
            .select_related("course", "academic_year", "assessment_type")
            .prefetch_related("assesses_cos")
            .order_by("-academic_year__start_date", "course__code", "date")
        )

    return render(
        request, "academics/assessment_list.html", {"assessments": assessments}
    )


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def assessment_create(request):
    if request.method == "POST":
        form = AssessmentForm(request.POST)
        if form.is_valid():
            # Security check for faculty
            if is_faculty(request.user) and not is_admin_or_hod(request.user):
                if (form.cleaned_data["course"] not in request.user.profile.taught_courses.all()):
                    messages.error(request, "You can only create assessments for courses you are assigned to.")
                    return render(request, "academics/assessment_form.html", {"form": form, "form_title": "Create Assessment"})

            assessment = form.save()
            messages.success(request, f'Assessment "{assessment.name}" for {assessment.course.code} created successfully!')
            return redirect("assessment_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssessmentForm()
        # Prefilter course dropdown for faculty
        if is_faculty(request.user) and not is_admin_or_hod(request.user):
            form.fields["course"].queryset = (request.user.profile.taught_courses.all().order_by("code"))
    
    return render(request, "academics/assessment_form.html", {"form": form, "form_title": "Create Assessment"})


# ==============================================================================
# ASSESSMENT UPDATE VIEW (MODIFIED)
# ==============================================================================
@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def assessment_update(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)

    # Security check for faculty
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if assessment.course not in request.user.profile.taught_courses.all():
            messages.error(request, "You do not have permission to update this Assessment.")
            return redirect("assessment_list")

    if request.method == "POST":
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            assessment = form.save()
            messages.success(request, f'Assessment "{assessment.name}" for {assessment.course.code} updated successfully!')
            return redirect("assessment_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssessmentForm(instance=assessment)
        # Prefilter course dropdown for faculty
        if is_faculty(request.user) and not is_admin_or_hod(request.user):
            form.fields["course"].queryset = (request.user.profile.taught_courses.all().order_by("code"))
        
        # Pre-populate the course outcomes for the existing assessment
        if assessment.course:
            form.fields["assesses_cos"].queryset = (assessment.course.course_outcomes.all().order_by("code"))

    # --- THIS IS THE KEY ADDITION ---
    # Pass the list of currently selected CO IDs to the template context.
    # This is used by the JavaScript to pre-select the checkboxes on page load.
    selected_co_ids = list(assessment.assesses_cos.values_list('id', flat=True))

    return render(request, "academics/assessment_form.html", {
        "form": form, 
        "form_title": f"Update Assessment: {assessment.name}",
        "selected_co_ids": selected_co_ids # Pass the list to the template
    })


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def assessment_delete(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)

    # Permission check: Faculty can only delete assessments for courses they teach
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if assessment.course not in request.user.profile.taught_courses.all():
            messages.error(
                request, "You do not have permission to delete this Assessment."
            )
            return redirect("assessment_list")

    if request.method == "POST":
        assessment.delete()
        messages.success(
            request,
            f'Assessment "{assessment.name}" for {assessment.course.code} deleted successfully!',
        )
        return redirect("assessment_list")
    return render(
        request, "academics/assessment_confirm_delete.html", {"assessment": assessment}
    )


# --- Student Mark Entry View ---


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def student_mark_entry(request, assessment_pk):
    assessment = get_object_or_404(Assessment, pk=assessment_pk)

    # Permission check (existing code)
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if assessment.course not in request.user.profile.taught_courses.all():
            messages.error(
                request,
                "You do not have permission to enter marks for this assessment.",
            )
            return redirect("assessment_list")

    # Get all students (users with the 'STUDENT' role) for marks entry for now.
    enrolled_students = User.objects.filter(profile__role="STUDENT").order_by(
        "username"
    )

    # Initialize the formset (for both GET and POST)
    form_data = []
    for student in enrolled_students:
        existing_mark = StudentMark.objects.filter(
            assessment=assessment, student=student
        ).first()
        form_data.append(
            {
                "id": existing_mark.id if existing_mark else None,
                "student": student.id,
                "marks_obtained": existing_mark.marks_obtained if existing_mark else "",
            }
        )

    MarkFormSet = StudentMarkFormSet(initial=form_data, prefix="marks")

    if request.method == "POST":
        formset = StudentMarkFormSet(
            request.POST, prefix="marks"
        )  # Re-initialize with POST data
        if formset.is_valid():
            # Save the formset (existing custom loop)
            for form in formset:
                marks_obtained = form.cleaned_data.get("marks_obtained")
                student = form.cleaned_data.get("student")

                if student and marks_obtained is not None:
                    mark_instance = StudentMark.objects.filter(
                        assessment=assessment, student=student
                    ).first()

                    if mark_instance:
                        mark_instance.marks_obtained = marks_obtained
                        mark_instance.save()
                    else:
                        StudentMark.objects.create(
                            assessment=assessment,
                            student=student,
                            marks_obtained=marks_obtained,
                        )
            messages.success(
                request, f"Student marks for {assessment.name} updated successfully!"
            )
            return redirect("assessment_list")
        else:
            # --- DEBUGGING LINES START ---
            print("====================================")
            print("Student Mark Formset is NOT valid!")
            print(
                "Overall Formset Errors:", formset.non_form_errors()
            )  # General formset errors
            for i, form in enumerate(formset):
                if form.errors:  # Check if individual form has errors
                    # Access the student directly from the current form being processed for better context
                    student_obj_for_error = None
                    try:
                        # Attempt to get the student object based on submitted data or instance
                        if "student" in form.cleaned_data:
                            student_obj_for_error = User.objects.get(
                                pk=form.cleaned_data["student"].pk
                            )
                        elif form.instance and form.instance.student:
                            student_obj_for_error = form.instance.student
                    except User.DoesNotExist:
                        pass  # Ignore if student not found (shouldn't happen)

                    print(
                        f"Form {i} Errors (for Student: {student_obj_for_error.username if student_obj_for_error else 'N/A'}):",
                        form.errors,
                    )
            print("====================================")
            # --- DEBUGGING LINES END ---
            messages.error(request, "Please correct the errors in the marks form.")
    else:
        # For GET requests, re-initialize the formset for display
        formset = StudentMarkFormSet(request.POST, prefix="marks")

    context = {
        "assessment": assessment,
        "formset": MarkFormSet,  # Pass the initialized formset (either empty or with POST data)
        "enrolled_students": enrolled_students,
    }
    return render(request, "academics/student_mark_entry_form.html", context)


# --- Attainment Calculation Engine ---

# UPDATE a single line in this function signature
def calculate_co_attainment_for_course(course_obj, academic_year_obj, success_threshold=60.0):
    """
    Calculates the attainment for each Course Outcome (CO) of a given course
    for a specific academic year.
    """
    course_outcomes = CourseOutcome.objects.filter(course=course_obj)

    for co in course_outcomes:
        # Find all assignments that assess this specific CO for the given academic year
        assignments_for_co = Assignment.objects.filter(
            assesses_cos=co,
            course__semester__academic_department__academic_year=academic_year_obj
        )
        
        if not assignments_for_co.exists():
            continue

        # Get all graded submissions for these assignments
        submissions = Submission.objects.filter(
            assignment__in=assignments_for_co,
            marks_obtained__isnull=False
        ).values('student').annotate(
            total_marks=Sum('marks_obtained'),
            max_marks=Sum('assignment__max_marks')
        )

        if not submissions:
            continue

        students_above_threshold = 0
        total_students_with_grades = submissions.count()

        for sub in submissions:
            if sub['max_marks'] > 0:
                percentage = (sub['total_marks'] / sub['max_marks']) * 100
                if percentage >= success_threshold:
                    students_above_threshold += 1

        if total_students_with_grades > 0:
            attainment_percentage = (students_above_threshold / total_students_with_grades) * 100
        else:
            attainment_percentage = 0

        # THIS IS THE FIX: Pass the academic_year_obj when creating the record
        CourseOutcomeAttainment.objects.update_or_create(
            course_outcome=co,
            academic_year=academic_year_obj,
            defaults={'attainment_percentage': attainment_percentage}
        )
    return True


# UPDATE a single line in this function signature
def calculate_po_attainment_for_department(department_obj, academic_year_obj):
    """
    Calculates the attainment for each Program Outcome (PO) of a given department
    for a specific academic year.
    """
    program_outcomes = ProgramOutcome.objects.filter(department=department_obj)

    for po in program_outcomes:
        print(f"[DEBUG] Processing PO: {po.code}")
        total_weighted_attainment = 0
        total_weight = 0
        # Initialize attainment_percentage for each PO to avoid UnboundLocalError
        attainment_percentage = 0  # Default value in case no valid calculations occur

        # Find all COs in this department that are mapped to this PO
        mappings = COPOMapping.objects.filter(
            program_outcome=po,
            course_outcome__course__department=department_obj,
            course_outcome__attainments__academic_year=academic_year_obj # Filter by year
        ).prefetch_related('course_outcome__attainments')

        print(f"[DEBUG] Total COPOMappings found for PO {po.code}: {mappings.count()}")

        for mapping in mappings:
            print(f"[DEBUG] Attempting to get attainment for CO: {mapping.course_outcome.code}")
            try:
                # Get the attainment for the specific academic year
                attainment_qs = mapping.course_outcome.attainments.filter(academic_year=academic_year_obj)
                if attainment_qs.exists():
                    attainment = attainment_qs.first()
                    print(f"[DEBUG] Attainment found: {attainment.attainment_percentage}%")
                    if attainment.attainment_percentage is not None:
                        weight = mapping.correlation_level
                        total_weighted_attainment += (attainment.attainment_percentage * weight)
                        total_weight += weight
                    else:
                        print(f"[DEBUG] Skipping: attainment percentage is None for CO {mapping.course_outcome.code}")
            except CourseOutcomeAttainment.DoesNotExist:
                continue

        if total_weight > 0:
            attainment_percentage = total_weighted_attainment / total_weight # Calculate first
            print(f"[DEBUG] Final PO attainment % for {po.code}: {attainment_percentage:.2f}%") # Then print
        else:
            attainment_percentage = 0
            print(f"[DEBUG] No valid mappings with attainment. PO attainment for {po.code} set to 0.00%")

        # THIS IS THE FIX: Pass the academic_year_obj when creating the record
        ProgramOutcomeAttainment.objects.update_or_create(
            program_outcome=po,
            academic_year=academic_year_obj,
            defaults={'attainment_percentage': attainment_percentage}
        )
    return True


# UPDATE the calls to the helper functions in this main view
@login_required
@user_passes_test(is_admin_or_hod)
def calculate_attainment_view(request):
    # Scope the dropdowns based on the user's role
    if is_hod(request.user):
        departments = Department.objects.filter(pk=request.user.profile.department.pk)
        courses = Course.objects.filter(department__in=departments)
    else: # Admin
        departments = Department.objects.all()
        courses = Course.objects.all()
    
    academic_years = AcademicYear.objects.all().order_by("-start_date")

    if request.method == "POST":
        calc_type = request.POST.get("calc_type")
        
        if calc_type == "co_by_course":
            course_id = request.POST.get("co_course")
            academic_year_id = request.POST.get("co_academic_year")
            if course_id and academic_year_id:
                course_obj = get_object_or_404(Course, pk=course_id)
                academic_year_obj = get_object_or_404(AcademicYear, pk=academic_year_id)
                calculate_co_attainment_for_course(course_obj, academic_year_obj)
                messages.success(request, f"CO Attainment calculated for {course_obj.code} in {academic_year_obj}!")
            else:
                messages.error(request, "Please select both a Course and an Academic Year.")

        elif calc_type == "po_by_department":
            department_id = request.POST.get("po_department")
            academic_year_id = request.POST.get("po_academic_year")
            if department_id and academic_year_id:
                department_obj = get_object_or_404(Department, pk=department_id)
                academic_year_obj = get_object_or_404(AcademicYear, pk=academic_year_id)
                calculate_po_attainment_for_department(department_obj, academic_year_obj)
                messages.success(request, f"PO Attainment calculated for {department_obj.name} in {academic_year_obj}!")
            else:
                 messages.error(request, "Please select both a Department and an Academic Year.")
        
        return redirect("calculate_attainment_view")

    context = {
        "courses": courses.order_by("code"),
        "departments": departments.order_by('name'),
        "academic_years": academic_years,
        "form_title": "Calculate Attainment"
    }
    return render(request, "academics/calculate_attainment_form.html", context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def co_attainment_report_list(request):
    user_profile = request.user.profile
    
    # --- Logic to scope the filter dropdowns based on user role ---
    # Base querysets
    co_attainments = CourseOutcomeAttainment.objects.all()
    academic_years_for_filter = AcademicYear.objects.all().order_by("-start_date")
    
    # Role-specific filtering
    if is_admin(user_profile.user):
        departments_for_filter = Department.objects.all().order_by("name")
        courses_for_filter = Course.objects.all().order_by("code")
    elif is_hod(user_profile.user):
        hod_department = user_profile.department
        departments_for_filter = Department.objects.filter(pk=hod_department.pk)
        courses_for_filter = Course.objects.filter(department=hod_department).order_by("code")
        co_attainments = co_attainments.filter(course_outcome__course__department=hod_department)
    else: # is_faculty
        courses_for_filter = user_profile.taught_courses.all().order_by("code")
        departments_for_filter = Department.objects.none()
        co_attainments = co_attainments.filter(course_outcome__course__in=user_profile.taught_courses.all())

    # Apply filters from GET parameters
    selected_academic_year_id = request.GET.get("academic_year")
    selected_department_id = request.GET.get("department")
    selected_course_id = request.GET.get("course")

    # Filter CO attainment base queryset
    if selected_department_id:
        courses_for_filter = Course.objects.filter(department_id=selected_department_id).order_by("code")
    else:
        if is_admin(user_profile.user):
            courses_for_filter = Course.objects.all().order_by("code")

    if selected_academic_year_id:
        co_attainments = co_attainments.filter(academic_year_id=selected_academic_year_id)

    if selected_course_id:
        co_attainments = co_attainments.filter(course_outcome__course_id=selected_course_id)
    elif selected_department_id:
        co_attainments = co_attainments.filter(course_outcome__course__department_id=selected_department_id)

    context = {
        "co_attainments": co_attainments.select_related(
            "course_outcome__course", "course_outcome__course__department", "academic_year"
        ).order_by("-academic_year__start_date", "course_outcome__course__code", "course_outcome__code"),
        "academic_years": academic_years_for_filter,
        "courses": courses_for_filter,
        "departments": departments_for_filter,
        "selected_academic_year_id": selected_academic_year_id,
        "selected_course_id": selected_course_id,
        "selected_department_id": selected_department_id,
        "form_title": "Course Outcome Attainment Report",
    }
    return render(request, "academics/co_attainment_report_list.html", context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def po_attainment_report_list(request):
    user_profile = request.user.profile

    # --- START: Logic to scope dropdowns and initial queryset ---
    # Base querysets
    po_attainments = ProgramOutcomeAttainment.objects.all()
    academic_years_for_filter = AcademicYear.objects.all().order_by("-start_date")
    departments_for_filter = Department.objects.all().order_by("name")

    # Filter based on user's role
    if is_hod(user_profile.user):
        hod_department = user_profile.department
        po_attainments = po_attainments.filter(program_outcome__department=hod_department)
        departments_for_filter = departments_for_filter.filter(pk=hod_department.pk)
    # --- END: Role-based filtering ---

    is_hod_user = is_hod(user_profile.user)


    # Apply filters from GET parameters
    selected_academic_year_id = request.GET.get("academic_year")
    selected_department_id = request.GET.get("department")

    if selected_academic_year_id:
        po_attainments = po_attainments.filter(academic_year_id=selected_academic_year_id)
    if selected_department_id:
        po_attainments = po_attainments.filter(program_outcome__department_id=selected_department_id)

    context = {
        "po_attainments": po_attainments.select_related(
            "program_outcome__department", "academic_year"
        ).order_by("-academic_year__start_date", "program_outcome__department__name", "program_outcome__code"),
        "academic_years": academic_years_for_filter,
        "departments": departments_for_filter, # Add departments for the filter
        "selected_academic_year_id": selected_academic_year_id,
        "selected_department_id": selected_department_id, # Pass to template
        "is_hod": is_hod_user,
        "form_title": "Program Outcome Attainment Report",
    }
    return render(request, "academics/po_attainment_report_list.html", context)


# --- Student Personal Views ---


@login_required
@user_passes_test(is_student, login_url="/accounts/login/")  # Only Students can access
def student_personal_marks_view(request):
    student_user = request.user

    # Get all marks for the logged-in student
    student_marks = (
        StudentMark.objects.filter(student=student_user)
        .select_related(
            "assessment__course",
            "assessment__academic_year",
            "assessment__assessment_type",
        )
        .order_by(
            "-assessment__academic_year__start_date",
            "assessment__course__code",
            "assessment__date",
        )
    )

    # Calculate percentage for each mark
    for mark in student_marks:
        if mark.marks_obtained is not None and mark.assessment.max_marks:
            mark.percentage = (mark.marks_obtained / mark.assessment.max_marks) * 100
        else:
            mark.percentage = None

    context = {
        "student_user": student_user,
        "student_marks": student_marks,
        "form_title": "My Assessment Marks",
    }
    return render(request, "academics/student_marks_report.html", context)


@login_required
@user_passes_test(is_student, login_url="/accounts/login/")
def student_personal_attainment_view(request):
    student_user = request.user

    # Get courses where student has marks
    courses_with_student_marks = Course.objects.filter(
        assessments__student_marks__student=student_user
    ).distinct()

    # Fix: Get academic years through assessments
    academic_years = AcademicYear.objects.filter(
        assessments__student_marks__student=student_user
    ).distinct()

    # CO Attainments
    co_attainments = (
        CourseOutcomeAttainment.objects.filter(
            course_outcome__course__in=courses_with_student_marks,
            academic_year__in=academic_years,
        )
        .select_related(
            "course_outcome__course",
            "course_outcome__course__department",
            "academic_year",
        )
        .order_by(
            "-academic_year__start_date",
            "course_outcome__course__code",
            "course_outcome__code",
        )
    )

    # PO Attainments
    po_attainments = (
        ProgramOutcomeAttainment.objects.filter(academic_year__in=academic_years)
        .select_related("program_outcome", "academic_year")
        .order_by("-academic_year__start_date", "program_outcome__code")
    )

    context = {
        "student_user": student_user,
        "co_attainments": co_attainments,
        "po_attainments": po_attainments,
        "form_title": "My Attainment Overview",
    }
    return render(request, "academics/student_attainment_report.html", context)


# --- Data Export Views ---


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def export_co_attainment_csv(request):
    selected_academic_year_id = request.GET.get("academic_year")
    selected_course_id = request.GET.get("course")

    co_attainments = CourseOutcomeAttainment.objects.all()

    # Apply same filtering logic as in co_attainment_report_list
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        user_profile = request.user.profile
        taught_courses = user_profile.taught_courses.all()
        co_attainments = co_attainments.filter(
            course_outcome__course__in=taught_courses
        )

    if selected_academic_year_id:
        co_attainments = co_attainments.filter(
            academic_year__id=selected_academic_year_id
        )
    if selected_course_id:
        co_attainments = co_attainments.filter(
            course_outcome__course__id=selected_course_id
        )

    co_attainments = co_attainments.select_related(
        "course_outcome__course", "course_outcome__course__department", "academic_year"
    ).order_by(
        "-academic_year__start_date",
        "course_outcome__course__code",
        "course_outcome__code",
    )

    # Prepare CSV response
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="course_outcome_attainment_report.csv"'
    )

    writer = csv.writer(response)

    # Write CSV header
    writer.writerow(
        [
            "Academic Year",
            "Course Code",
            "Course Name",
            "Department",
            "CO Code",
            "CO Description",
            "Attainment Percentage",
        ]
    )

    # Write data rows
    for co_att in co_attainments:
        writer.writerow(
            [
                f"{co_att.academic_year.start_date.year}-{co_att.academic_year.end_date.year}",
                co_att.course_outcome.course.code,
                co_att.course_outcome.course.name,
                (
                    co_att.course_outcome.course.department.name
                    if co_att.course_outcome.course.department
                    else "N/A"
                ),
                co_att.course_outcome.code,
                co_att.course_outcome.description,
                (
                    f"{co_att.attainment_percentage:.2f}%"
                    if co_att.attainment_percentage is not None
                    else "N/A"
                ),
            ]
        )

    return response


@login_required
@user_passes_test(is_faculty)
def create_student_by_faculty(request):
    if request.method == 'POST':
        # Pass the user to the form to handle initial data for re-display on error
        form = StudentCreationForm(request.POST, faculty_user=request.user)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    user = form.save() 
                    # IMPORTANT: Get the department securely from the logged-in faculty's profile
                    # This prevents a user from maliciously changing the hidden form value.
                    UserProfile.objects.create(
                        user=user,
                        role=UserRole.STUDENT,
                        department=request.user.profile.department 
                    )
                messages.success(request, f"Student '{user.username}' created successfully.")
                return redirect('student_list')
            except Exception as e:
                messages.error(request, f"An error occurred while creating the student: {e}")
    else:
        # This part correctly passes the user to the form's __init__ method
        form = StudentCreationForm(faculty_user=request.user)

    context = {
        'form': form,
        'form_title': 'Create New Student'
    }
    return render(request, 'academics/create_student_form.html', context)


# Update the permission check to include HODs and Admins
@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url='/accounts/login/') # Use your existing permission check
def assignment_list(request):
    # --- START OF NEW LOGIC ---
    # Determine the queryset based on the user's role
    if is_admin(request.user):
        # Admins see all assignments from all courses
        assignments = Assignment.objects.all().select_related('course', 'course__department')
        form_title = 'All Assignments'
    elif is_hod(request.user):
        # HODs see all assignments in their department's courses
        hod_department = request.user.profile.department
        assignments = Assignment.objects.filter(course__department=hod_department).select_related('course')
        form_title = f'{hod_department.name} Department Assignments'
    else:
        # Default case for regular Faculty: only see assignments they created
        assignments = Assignment.objects.filter(created_by=request.user.profile).select_related('course')
        form_title = 'My Assignments'
    # --- END OF NEW LOGIC ---
    
    context = {
        'assignments': assignments.order_by('-created_at'), # Add ordering
        'form_title': form_title
    }
    return render(request, 'academics/assignment_list.html', context)


@login_required
@user_passes_test(is_faculty)
def assignment_create(request):
    if request.method == 'POST':
        form = AssignmentForm(request.POST, user=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.created_by = request.user.profile
            assignment.save()
            form.save_m2m()
            messages.success(request, f"Assignment '{assignment.title}' created successfully.")
            return redirect('assignment_list')
    else:
        form = AssignmentForm(user=request.user)
        
    return render(request, 'academics/assignment_form.html', {'form': form, 'form_title': 'Create New Assignment'})


@login_required
@user_passes_test(is_faculty)
def assignment_update(request, pk):
    # Ensure a faculty member can only edit their own assignments
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user.profile)
    
    if request.method == 'POST':
        print("POST DATA:", request.POST)
        # Pass user to the form to scope the course/rubric dropdowns
        form = AssignmentForm(request.POST, instance=assignment, user=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.created_by = request.user.profile  # Optional, keep if necessary
            assignment.save()
            form.save_m2m()
            messages.success(request, f"Assignment '{assignment.title}' updated successfully.")
            return redirect('assignment_list')
    else:
        form = AssignmentForm(instance=assignment, user=request.user)
        
    return render(request, 'academics/assignment_form.html', {
        'form': form, 
        'form_title': f'Update Assignment: {assignment.title}',
        'selected_co_ids': list(assignment.assesses_cos.values_list('id', flat=True))
    })


@login_required
@user_passes_test(is_faculty)
def assignment_delete(request, pk):
    # Ensure a faculty member can only delete their own assignments
    assignment = get_object_or_404(Assignment, pk=pk, created_by=request.user.profile)
    
    if request.method == 'POST':
        assignment_title = assignment.title
        assignment.delete()
        messages.success(request, f"Assignment '{assignment_title}' has been deleted.")
        return redirect('assignment_list')
        
    return render(request, 'academics/assignment_confirm_delete.html', {'assignment': assignment})



@login_required
@user_passes_test(is_faculty)
def rubric_list(request):
    rubrics = Rubric.objects.filter(created_by=request.user.profile)
    return render(request, 'academics/rubric_list.html', {'rubrics': rubrics, 'form_title': 'My Rubrics'})

@login_required
@user_passes_test(is_faculty)
def rubric_create(request):
    if request.method == 'POST':
        form = RubricForm(request.POST)
        formset = RubricCriterionFormSet(request.POST, prefix='criteria')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                rubric = form.save(commit=False)
                rubric.created_by = request.user.profile
                rubric.save()
                formset.instance = rubric
                formset.save()
            messages.success(request, f"Rubric '{rubric.name}' created successfully.")
            return redirect('rubric_list')
    else:
        form = RubricForm()
        formset = RubricCriterionFormSet(prefix='criteria')
        
    return render(request, 'academics/rubric_form.html', {'form': form, 'formset': formset, 'form_title': 'Create New Rubric'})

@login_required
@user_passes_test(is_faculty)
def rubric_update(request, pk):
    # Ensure faculty can only edit their own rubrics
    rubric = get_object_or_404(Rubric, pk=pk, created_by=request.user.profile)
    
    if request.method == 'POST':
        form = RubricForm(request.POST, instance=rubric)
        formset = RubricCriterionFormSet(request.POST, instance=rubric, prefix='criteria')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, f"Rubric '{rubric.name}' updated successfully.")
            return redirect('rubric_list')
    else:
        form = RubricForm(instance=rubric)
        formset = RubricCriterionFormSet(instance=rubric, prefix='criteria')
        
    return render(request, 'academics/rubric_form.html', {
        'form': form, 
        'formset': formset, 
        'form_title': f'Update Rubric: {rubric.name}'
    })


@login_required
@user_passes_test(is_faculty)
def rubric_delete(request, pk):
    # Ensure faculty can only delete their own rubrics
    rubric = get_object_or_404(Rubric, pk=pk, created_by=request.user.profile)
    if request.method == 'POST':
        rubric_name = rubric.name
        rubric.delete()
        messages.success(request, f"Rubric '{rubric_name}' has been deleted.")
        return redirect('rubric_list')
    return render(request, 'academics/rubric_confirm_delete.html', {'rubric': rubric})


@login_required
@user_passes_test(is_student)
def student_assignment_list(request):
    student_profile = request.user.profile
    # Get all courses the student is enrolled in
    enrolled_courses = student_profile.enrolled_courses.all()
    # Get all assignments for those courses
    assignments = Assignment.objects.filter(course__in=enrolled_courses).order_by('due_date')
    
    # Get submitted assignment IDs for this student to check status
    submitted_assignments_ids = Submission.objects.filter(student=student_profile).values_list('assignment_id', flat=True)

    context = {
        'assignments': assignments,
        'submitted_assignments_ids': submitted_assignments_ids,
        'form_title': 'My Assignments'
    }
    return render(request, 'academics/student_assignment_list.html', context)


@login_required
@user_passes_test(is_student)
def assignment_detail_and_submit(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    student_profile = request.user.profile
    
    # Security check: Ensure student is enrolled in the course for this assignment
    if assignment.course not in student_profile.enrolled_courses.all():
        messages.error(request, "You are not authorized to view this assignment.")
        return redirect('student_assignment_list')

    existing_submission = None
    rubric_scores = None # Initialize as None
    rubric_criteria = None # Initialize as None

    # --- NEW: Fetch rubric criteria if the assignment is rubric-based ---
    if assignment.assignment_type == 'rubric_based' and assignment.rubric:
        rubric_criteria = RubricCriterion.objects.filter(rubric=assignment.rubric)


    # Check if a submission already exists
    try:
        existing_submission = Submission.objects.get(assignment=assignment, student=student_profile)
        if existing_submission:
            rubric_scores = RubricScore.objects.filter(submission=existing_submission).select_related('criterion')
    except Submission.DoesNotExist:
        pass

    if request.method == 'POST':
        # Prevent re-submission
        if existing_submission:
            messages.warning(request, "You have already submitted this assignment.")
            return redirect('assignment_detail_and_submit', pk=pk)

        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = student_profile
            submission.save()
            messages.success(request, "Your assignment has been submitted successfully.")
            return redirect('assignment_detail_and_submit', pk=pk)
    else:
        form = SubmissionForm()
        
    context = {
        'assignment': assignment,
        'form': form,
        'existing_submission': existing_submission,
        'rubric_scores': rubric_scores, # --- NEW: Add scores to context ---
        'rubric_criteria': rubric_criteria, # --- NEW: Add criteria to context ---
    }
    return render(request, 'academics/student_assignment_detail.html', context)


@login_required
@user_passes_test(is_faculty)
def submission_list_for_assignment(request, assignment_pk):
    # The get_object_or_404 now includes the security check directly
    assignment = get_object_or_404(Assignment, pk=assignment_pk, created_by=request.user.profile)
    
    # The rest of the view logic remains the same
    enrolled_students = assignment.course.students.all().order_by('user__last_name', 'user__first_name')
    submissions = Submission.objects.filter(assignment=assignment)
    submissions_by_student = {submission.student.pk: submission for submission in submissions}
    
    student_submission_status = []
    for student in enrolled_students:
        student_submission_status.append({
            'student_profile': student,
            'submission': submissions_by_student.get(student.pk)
        })
        
    context = {
        'assignment': assignment,
        'student_submission_status': student_submission_status,
        'form_title': f"Submissions for: {assignment.title}"
    }
    return render(request, 'academics/submission_list.html', context)


@login_required
@user_passes_test(is_faculty)
def grade_submission(request, assignment_pk, student_pk):
    assignment = get_object_or_404(Assignment, pk=assignment_pk, created_by=request.user.profile)
    student = get_object_or_404(UserProfile, pk=student_pk, role=UserRole.STUDENT)

    if student not in assignment.course.students.all():
        messages.error(request, "This student is not enrolled in the course for this assignment.")
        return redirect('submission_list_for_assignment', assignment_pk=assignment.pk)

    submission, created = Submission.objects.get_or_create(
        assignment=assignment,
        student=student
    )
    
    is_rubric_based = assignment.assignment_type == 'rubric_based' and assignment.rubric
    rubric_formset = None
    RubricScoreFormSet = None
    queryset = None
    rubric_data = None

    if is_rubric_based:
        criteria = assignment.rubric.criteria.all().order_by('order')
        for criterion in criteria:
            RubricScore.objects.get_or_create(
                submission=submission,
                criterion=criterion,
                defaults={'score': 0}
            )
        queryset = RubricScore.objects.filter(submission=submission).select_related('criterion').order_by('criterion__order')
        RubricScoreFormSet = modelformset_factory(RubricScore, form=RubricScoreForm, extra=0)

    if request.method == 'POST':
        # --- PASS ASSIGNMENT TO THE FORM ---
        grading_form = GradingForm(request.POST, instance=submission, assignment=assignment)
        if is_rubric_based:
            rubric_formset = RubricScoreFormSet(request.POST, queryset=queryset, prefix='scores')

        if grading_form.is_valid() and (not is_rubric_based or rubric_formset.is_valid()):
            with transaction.atomic():
                graded_submission = grading_form.save(commit=False)

                if is_rubric_based:
                    rubric_formset.save()
                    total_score = RubricScore.objects.filter(submission=graded_submission).aggregate(total=Sum('score'))['total']
                    graded_submission.marks_obtained = total_score or 0
                
                # For non-rubric assignments, marks_obtained will come directly from the valid form
                
                graded_submission.graded_by = request.user.profile
                graded_submission.graded_at = timezone.now()
                graded_submission.save()
            
            messages.success(request, f"Grade for {student.user.username} has been saved.")
            return redirect('submission_list_for_assignment', assignment_pk=assignment.pk)
        else:
            messages.error(request, "Please correct the errors below.")
            if is_rubric_based:
                rubric_data = zip(rubric_formset, queryset)
    
    else: # GET request
        # --- PASS ASSIGNMENT TO THE FORM ---
        grading_form = GradingForm(instance=submission, assignment=assignment)
        if is_rubric_based:
            rubric_formset = RubricScoreFormSet(queryset=queryset, prefix='scores')
            rubric_data = zip(rubric_formset, queryset)

    context = {
        'submission': submission,
        'assignment': assignment,
        'student': student,
        'grading_form': grading_form,
        'rubric_data': rubric_data,
        'rubric_formset': rubric_formset,
        'form_title': f'Grade Submission for {student.user.get_full_name()}'
    }
    return render(request, 'academics/grade_submission.html', context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty)
def student_list(request):
    user_profile = request.user.profile
    
    # Start with the base queryset for all students
    student_profiles = UserProfile.objects.filter(role=UserRole.STUDENT).select_related('user', 'department').order_by('user__last_name', 'user__first_name')

    # Determine permissions
    can_edit_students = False
    if user_profile.role == 'ADMIN' or user_profile.role == 'FACULTY':
        can_edit_students = True

    # Filter the list based on role
    if user_profile.role == 'HOD':
        try:
            hod_academic_dept = AcademicDepartment.objects.get(hod=user_profile)
            student_profiles = student_profiles.filter(department=hod_academic_dept.department)
        except AcademicDepartment.DoesNotExist:
            student_profiles = UserProfile.objects.none() # HOD not assigned
    
    elif user_profile.role == 'FACULTY':
        # --- NEW, CORRECTED LOGIC FOR FACULTY ---
        # Faculty sees students from the departments of the courses they teach.
        
        # Find all courses taught by this faculty member
        taught_courses = user_profile.taught_courses.all()
        
        if taught_courses.exists():
            # Get a unique list of department IDs from those courses
            department_ids = taught_courses.values_list('department_id', flat=True).distinct()
            # Filter students who belong to any of those departments
            student_profiles = student_profiles.filter(department_id__in=department_ids)
        else:
            # If faculty is not assigned to any courses, they see no students
            student_profiles = UserProfile.objects.none()

    # Admins see all students, so no filter is applied.

    context = {
        'student_profiles': student_profiles,
        'can_edit_students': can_edit_students,
        'form_title': 'Student List'
    }
    return render(request, 'academics/student_list.html', context)


@login_required
@user_passes_test(is_faculty) # Only faculty can access this edit page
def student_update_by_faculty(request, pk):
    user_to_edit = get_object_or_404(User, pk=pk, profile__role=UserRole.STUDENT)
    faculty_profile = request.user.profile

    # Security Check: Ensure faculty can only edit students in their department(s)
    faculty_departments = faculty_profile.taught_courses.values_list('department', flat=True).distinct()
    if user_to_edit.profile.department_id not in faculty_departments:
        messages.error(request, "You do not have permission to edit this student.")
        return redirect('student_list')

    if request.method == 'POST':
        form = StudentUpdateByFacultyForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, f"Student '{user_to_edit.username}' updated successfully.")
            return redirect('student_list')
    else:
        form = StudentUpdateByFacultyForm(instance=user_to_edit)

    context = {
        'form': form,
        'form_title': f'Update Student: {user_to_edit.username}'
    }
    return render(request, 'academics/student_form.html', context)


@login_required
@user_passes_test(is_faculty) # Only faculty can access
def student_delete_by_faculty(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk, profile__role=UserRole.STUDENT)
    faculty_profile = request.user.profile

    # Security Check: Ensure faculty can only delete students from courses they teach
    faculty_departments = faculty_profile.taught_courses.values_list('department_id', flat=True).distinct()
    if user_to_delete.profile.department_id not in faculty_departments:
        messages.error(request, "You do not have permission to delete this student.")
        return redirect('student_list')

    if request.method == 'POST':
        # If the form is submitted, delete the user and their profile (cascade)
        deleted_username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"Student '{deleted_username}' has been deleted.")
        return redirect('student_list')

    # If it's a GET request, show the confirmation page
    context = {
        'student': user_to_delete,
        'form_title': f'Delete Student: {user_to_delete.username}'
    }
    return render(request, 'academics/student_confirm_delete.html', context)


# --- ADD THIS ENTIRE NEW VIEW ---
@login_required
@user_passes_test(is_faculty) # Only faculty or admins (who are also faculty) can enroll
def enroll_student_view(request, student_pk):
    student_profile = get_object_or_404(UserProfile, user__pk=student_pk, role=UserRole.STUDENT)
    
    if request.method == 'POST':
        form = EnrollStudentForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.cleaned_data['course']
            # Add the student to the course's ManyToMany relationship
            course.students.add(student_profile)
            messages.success(request, f"Successfully enrolled {student_profile.user.username} in {course.code}.")
            return redirect('student_list')
    else:
        form = EnrollStudentForm(user=request.user)

    context = {
        'form': form,
        'student_profile': student_profile,
        'form_title': f"Enroll {student_profile.user.username}"
    }
    return render(request, 'academics/enroll_student_form.html', context)


# --- ADD THIS ENTIRE NEW VIEW ---
@login_required
@user_passes_test(is_admin_or_hod_or_faculty) # Permissions for who can access this page
def bulk_enrollment_view(request):
    if request.method == 'POST':
        form = BulkEnrollmentForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.cleaned_data['course']
            students_to_enroll = form.cleaned_data['students']

            # Use the .add() method with the splat operator to add all students at once
            course.students.add(*students_to_enroll)
            
            messages.success(request, f"Successfully enrolled {students_to_enroll.count()} student(s) in {course.code}.")
            return redirect('bulk_enrollment') # Redirect to the same page to perform another action
    else:
        form = BulkEnrollmentForm(user=request.user)

    context = {
        'form': form,
        'form_title': "Bulk Enroll Students in a Course"
    }
    return render(request, 'academics/bulk_enrollment_form.html', context)


@login_required
def get_course_outcomes_api(request, course_id):
    """
    An API endpoint to fetch course outcomes for a given course ID.
    Returns data as JSON.
    """
    try:
        user_profile = request.user.profile
        course = get_object_or_404(Course, pk=course_id)

        # Security Check: Ensure the user has permission to access this course's COs
        is_admin_or_hod = user_profile.role in ['ADMIN', 'HOD'] or request.user.is_superuser
        is_assigned_faculty = course in user_profile.taught_courses.all()

        if not (is_admin_or_hod or is_assigned_faculty):
            return JsonResponse({'error': 'Permission denied to access course outcomes.'}, status=403)

        outcomes = CourseOutcome.objects.filter(course=course).values('id', 'code', 'description')
        return JsonResponse(list(outcomes), safe=False)
        
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found.'}, status=404)

# --- ADD THIS NEW VIEW FOR DYNAMIC DROPDOWNS ---
@login_required
@user_passes_test(is_admin) # Only admins need this API
def get_courses_by_department_api(request, department_id):
    """
    An API endpoint to fetch courses for a given department ID.
    """
    try:
        department = Department.objects.get(pk=department_id)
        courses = Course.objects.filter(department=department).values('id', 'code', 'name')
        return JsonResponse(list(courses), safe=False)
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)
        