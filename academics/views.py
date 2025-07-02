# academics/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages  # For displaying feedback messages
from django.views.generic import View  # For class-based views if preferred
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


# --- Existing Views (from previous step, ensure these are here or imported if you refactored) ---
# from django.contrib.auth.views import LoginView, LogoutView
# from django.urls import reverse_lazy
# class CustomLoginView(LoginView): ...
# class CustomLogoutView(LogoutView): ...
# @login_required
# def home_view(request): ...

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
        course_plan.delete()
        messages.success(request, f"Course Plan for '{course_plan.course.code}' deleted successfully.")
        return redirect('course_plan_list')
    
    context = {
        'course_plan': course_plan,
    }
    return render(request, 'academics/course_plan_confirm_delete.html', context)


# --- Program Outcome Management Views ---


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def program_outcome_list(request):
    program_outcomes = ProgramOutcome.objects.all().order_by("code")
    return render(
        request,
        "academics/program_outcome_list.html",
        {"program_outcomes": program_outcomes},
    )


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def program_outcome_create(request):
    if request.method == "POST":
        form = ProgramOutcomeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Program Outcome created successfully!")
            return redirect("program_outcome_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProgramOutcomeForm()
    return render(
        request,
        "academics/program_outcome_form.html",
        {"form": form, "form_title": "Create Program Outcome"},
    )


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def program_outcome_update(request, pk):
    program_outcome = get_object_or_404(ProgramOutcome, pk=pk)
    if request.method == "POST":
        form = ProgramOutcomeForm(request.POST, instance=program_outcome)
        if form.is_valid():
            form.save()
            messages.success(request, "Program Outcome updated successfully!")
            return redirect("program_outcome_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProgramOutcomeForm(instance=program_outcome)
    return render(
        request,
        "academics/program_outcome_form.html",
        {"form": form, "form_title": "Update Program Outcome"},
    )


@login_required
@user_passes_test(is_admin_or_superuser, login_url="/accounts/login/")
def program_outcome_delete(request, pk):
    program_outcome = get_object_or_404(ProgramOutcome, pk=pk)
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
@user_passes_test(is_admin_or_hod, login_url='/accounts/login/')
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
        if is_faculty(request.user) and not is_admin_or_hod(request.user):
            form.fields['course'].queryset = request.user.profile.taught_courses.all().order_by('code')

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

    context = {
        # Optimize the final query and pass it to the context
        'course_outcomes': course_outcomes.select_related("course").order_by("course__code", "code"),
        # Pass the necessary data for the filter dropdown
        'all_courses': courses_for_filter,
        'selected_course_id': selected_course_id,
        'form_title': 'Course Outcomes' # Add form_title to context
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
def course_outcome_update(request, pk):
    co = get_object_or_404(CourseOutcome, pk=pk)

    # Permission check: Faculty can only update COs for courses they teach
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if co.course not in request.user.profile.taught_courses.all():
            messages.error(
                request, "You do not have permission to update this Course Outcome."
            )
            return redirect("course_outcome_list")  # Redirect away if no permission

    if request.method == "POST":
        form = CourseOutcomeForm(request.POST, instance=co)
        if form.is_valid():
            co = form.save()
            messages.success(
                request,
                f'Course Outcome "{co.code}" for {co.course.code} updated successfully!',
            )
            return redirect("course_outcome_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CourseOutcomeForm(instance=co)
        # If user is faculty, pre-filter courses in the form for consistency
        if is_faculty(request.user) and not is_admin_or_hod(request.user):
            form.fields["course"].queryset = (
                request.user.profile.taught_courses.all().order_by("code")
            )

    return render(
        request,
        "academics/course_outcome_form.html",
        {"form": form, "form_title": "Update Course Outcome"},
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

    # Permission check (existing code)
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if course_outcome.course not in request.user.profile.taught_courses.all():
            messages.error(
                request,
                "You do not have permission to modify mappings for this Course Outcome.",
            )
            return redirect("course_outcome_list")

    all_program_outcomes = ProgramOutcome.objects.all().order_by("code")

    # Get existing mappings for this Course Outcome
    # This is needed for both GET (display) and POST (initial state for processing)
    existing_mappings = COPOMapping.objects.filter(
        course_outcome=course_outcome
    ).values("program_outcome_id", "correlation_level")

    if request.method == "POST":
        # --- MANUAL PROCESSING OF MAPPINGS (FROM PREVIOUS FIX) ---
        errors = {}  # To collect any custom errors during processing

        with transaction.atomic():
            for po in all_program_outcomes:
                field_name = f"correlation_level_{po.id}"
                submitted_level = request.POST.get(field_name)

                if submitted_level:
                    try:
                        submitted_level = int(submitted_level)
                    except ValueError:
                        errors[field_name] = "Invalid level."
                        submitted_level = CorrelationLevel.NONE.value
                else:
                    submitted_level = CorrelationLevel.NONE.value

                mapping_instance = COPOMapping.objects.filter(
                    course_outcome=course_outcome, program_outcome=po
                ).first()

                if submitted_level == CorrelationLevel.NONE.value:
                    if mapping_instance:
                        mapping_instance.delete()
                else:
                    if submitted_level < 0 or submitted_level > 3:
                        errors[field_name] = "Invalid correlation level."
                        continue

                    if mapping_instance:
                        mapping_instance.correlation_level = submitted_level
                        mapping_instance.save()
                    else:
                        COPOMapping.objects.create(
                            course_outcome=course_outcome,
                            program_outcome=po,
                            correlation_level=submitted_level,
                        )

            # --- Check for errors after manual processing ---
            if errors:
                messages.error(
                    request,
                    "There were errors processing some mappings. Please review.",
                )
                # Re-fetch existing mappings to show current state after partial saves/errors
                existing_mappings_dict = {
                    m["program_outcome_id"]: m["correlation_level"]
                    for m in COPOMapping.objects.filter(
                        course_outcome=course_outcome
                    ).values("program_outcome_id", "correlation_level")
                }

                context = {
                    "course_outcome": course_outcome,
                    # 'formset': MappingFormSet, # REMOVE THIS LINE
                    "all_program_outcomes": all_program_outcomes,
                    "correlation_choices": CorrelationLevel.choices,
                    "existing_mappings_dict": existing_mappings_dict,  # Pass current state
                    "form_errors": errors,  # Pass specific field errors
                }
                return render(request, "academics/copo_mapping_form.html", context)
            else:
                messages.success(
                    request,
                    f"CO-PO mappings for {course_outcome.code} updated successfully!",
                )
                return redirect("course_outcome_list")

    else:  # GET request
        # Prepare existing mappings in a dictionary for easy lookup in template
        existing_mappings_dict = {
            m["program_outcome_id"]: m["correlation_level"] for m in existing_mappings
        }

        context = {
            "course_outcome": course_outcome,
            # 'formset': formset, # REMOVE THIS LINE IF IT WAS THERE
            "all_program_outcomes": all_program_outcomes,
            "correlation_choices": CorrelationLevel.choices,
            "existing_mappings_dict": existing_mappings_dict,  # Pass for template pre-selection
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
            # Faculty specific validation: ensure they are assigned to the selected course
            if is_faculty(request.user) and not is_admin_or_hod(request.user):
                if (
                    form.cleaned_data["course"]
                    not in request.user.profile.taught_courses.all()
                ):
                    messages.error(
                        request,
                        "You can only create assessments for courses you are assigned to.",
                    )
                    return render(
                        request,
                        "academics/assessment_form.html",
                        {"form": form, "form_title": "Create Assessment"},
                    )

            assessment = form.save()
            messages.success(
                request,
                f'Assessment "{assessment.name}" for {assessment.course.code} created successfully!',
            )
            return redirect("assessment_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssessmentForm()
        # Prefilter course choices for faculty users
        if is_faculty(request.user) and not is_admin_or_hod(request.user):
            form.fields["course"].queryset = (
                request.user.profile.taught_courses.all().order_by("code")
            )
            # Consider dynamically updating assesses_cos queryset based on initial course selected, if any.
            # This would require JS on the frontend or passing initial data to the template.
    return render(
        request,
        "academics/assessment_form.html",
        {"form": form, "form_title": "Create Assessment"},
    )


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def assessment_update(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)

    # Permission check: Faculty can only update assessments for courses they teach
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        if assessment.course not in request.user.profile.taught_courses.all():
            messages.error(
                request, "You do not have permission to update this Assessment."
            )
            return redirect("assessment_list")

    if request.method == "POST":
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            assessment = form.save()
            messages.success(
                request,
                f'Assessment "{assessment.name}" for {assessment.course.code} updated successfully!',
            )
            return redirect("assessment_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssessmentForm(instance=assessment)
        # Prefilter course choices for faculty users
        if is_faculty(request.user) and not is_admin_or_hod(request.user):
            form.fields["course"].queryset = (
                request.user.profile.taught_courses.all().order_by("code")
            )
        # Filter assesses_cos queryset based on the instance's course
        if assessment.course:
            form.fields["assesses_cos"].queryset = (
                assessment.course.course_outcomes.all().order_by("code")
            )

    return render(
        request,
        "academics/assessment_form.html",
        {"form": form, "form_title": "Update Assessment"},
    )


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


# --- Attainment Calculation Functions ---


def calculate_co_attainment_for_course(course_obj, academic_year_obj):
    print(
        f"\n--- Starting CO Attainment Calculation for Course: {course_obj.code} ({course_obj.name}), Year: {academic_year_obj} ---"
    )  # DEBUG

    course_outcomes = CourseOutcome.objects.filter(course=course_obj).prefetch_related(
        "assessed_by_assessments__student_marks"
    )
    print(f"  Number of COs for this course: {course_outcomes.count()}")  # DEBUG

    if not course_outcomes.exists():
        print(
            "  No Course Outcomes found for this course. Skipping CO attainment."
        )  # DEBUG
        return False  # No COs to calculate for this course

    for co in course_outcomes:
        print(
            f"\n  Processing Course Outcome: {co.code} - {co.description[:30]}..."
        )  # DEBUG

        total_co_marks_possible = 0
        total_co_marks_obtained = 0

        # Get all assessments that assess this CO for the given academic year
        assessments_for_co = co.assessed_by_assessments.filter(
            course=course_obj,  # Ensure assessment is for the specific course
            academic_year=academic_year_obj,  # Ensure assessment is for the specific academic year
        ).distinct()

        print(
            f"    Number of Assessments linked to CO {co.code} (in this course/year): {assessments_for_co.count()}"
        )  # DEBUG

        if not assessments_for_co.exists():
            print(
                f"    No relevant assessments found for CO {co.code}. Attainment will be None."
            )  # DEBUG
            attainment_percentage = None
        else:
            # Aggregate marks from relevant assessments for this CO
            current_co_total_possible_marks = (
                0  # sum of max_marks * students who took it
            )
            current_co_total_obtained_marks = 0  # sum of actual marks obtained

            for assessment in assessments_for_co:
                print(
                    f"      - Processing Assessment: {assessment.name} (Max Marks: {assessment.max_marks})"
                )  # DEBUG

                # Get student marks only for this specific assessment
                student_marks_queryset = StudentMark.objects.filter(
                    assessment=assessment
                )
                num_students_with_marks = student_marks_queryset.count()

                print(
                    f"        Students with marks in this assessment: {num_students_with_marks}"
                )  # DEBUG

                if num_students_with_marks > 0:
                    sum_obtained_for_assessment = student_marks_queryset.aggregate(
                        total_marks=Sum("marks_obtained")
                    )["total_marks"]

                    if sum_obtained_for_assessment is not None:
                        current_co_total_obtained_marks += sum_obtained_for_assessment
                        current_co_total_possible_marks += (
                            assessment.max_marks * num_students_with_marks
                        )
                        print(
                            f"        Obtained: {sum_obtained_for_assessment}, Possible: {assessment.max_marks * num_students_with_marks}"
                        )  # DEBUG
                    else:
                        print(
                            "        No obtained marks sum (might be all None or 0 in DB, but count > 0)."
                        )  # DEBUG
                else:
                    print(
                        "        No students with marks found for this assessment."
                    )  # DEBUG

            # After iterating through all assessments for this CO
            total_possible_marks_from_assessments = current_co_total_possible_marks
            total_obtained_marks_from_assessments = current_co_total_obtained_marks

            print(
                f"    Total for CO {co.code}: Obtained={total_obtained_marks_from_assessments}, Possible={total_possible_marks_from_assessments}"
            )  # DEBUG

            if total_possible_marks_from_assessments > 0:
                attainment_percentage = (
                    total_obtained_marks_from_assessments
                    / total_possible_marks_from_assessments
                ) * 100
                attainment_percentage = round(attainment_percentage, 2)
                print(
                    f"    Calculated Attainment % for CO {co.code}: {attainment_percentage}"
                )  # DEBUG
            else:
                attainment_percentage = None
                print(
                    f"    Total possible marks for CO {co.code} is 0. Attainment set to None."
                )  # DEBUG

        # Create or update CO Attainment record
        co_attainment, created = CourseOutcomeAttainment.objects.update_or_create(
            course_outcome=co,
            academic_year=academic_year_obj,
            defaults={"attainment_percentage": attainment_percentage},
        )
        print(
            f"  CO Attainment record for {co.code} saved: {co_attainment.attainment_percentage}% (Created: {created})"
        )  # DEBUG

    print(
        f"\n--- Finished CO Attainment Calculation for Course: {course_obj.code} ---"
    )  # DEBUG
    return True


def calculate_po_attainment_for_academic_year(academic_year_obj):
    print(
        f"\n--- Starting PO Attainment Calculation for Year: {academic_year_obj} ---"
    )  # DEBUG
    # ... (rest of function as is, or add similar prints)
    program_outcomes = ProgramOutcome.objects.all()

    for po in program_outcomes:
        print(f"\n  Processing Program Outcome: {po.code}")  # DEBUG
        total_weighted_attainment = 0
        total_weight = 0

        # Get all relevant CO-PO mappings for COs associated with this academic year
        relevant_mappings = COPOMapping.objects.filter(
            program_outcome=po, course_outcome__course__academic_year=academic_year_obj
        ).select_related("course_outcome")

        print(
            f"    Number of relevant CO-PO mappings for PO {po.code}: {relevant_mappings.count()}"
        )  # DEBUG

        if not relevant_mappings.exists():
            po_attainment_percentage = None
            print(
                f"    No relevant mappings found for PO {po.code}. Attainment set to None."
            )  # DEBUG
        else:
            for mapping in relevant_mappings:
                print(
                    f"      - Processing mapping: {mapping.course_outcome.code} -> {mapping.program_outcome.code}"
                )  # DEBUG
                co_attainment_obj = CourseOutcomeAttainment.objects.filter(
                    course_outcome=mapping.course_outcome,
                    academic_year=academic_year_obj,
                ).first()

                if (
                    co_attainment_obj
                    and co_attainment_obj.attainment_percentage is not None
                ):
                    print(
                        f"        Found CO Attainment for {mapping.course_outcome.code}: {co_attainment_obj.attainment_percentage}% (Weight: {mapping.correlation_level})"
                    )  # DEBUG
                    weight = mapping.correlation_level
                    total_weighted_attainment += (
                        co_attainment_obj.attainment_percentage * weight
                    )
                    total_weight += weight
                else:
                    print(
                        f"        No valid CO Attainment found for {mapping.course_outcome.code}."
                    )  # DEBUG

            print(
                f"    Final Totals for PO {po.code}: Weighted={total_weighted_attainment}, Total Weight={total_weight}"
            )  # DEBUG

            if total_weight > 0:
                po_attainment_percentage = total_weighted_attainment / total_weight
                po_attainment_percentage = round(po_attainment_percentage, 2)
                print(
                    f"    Calculated Attainment % for PO {po.code}: {po_attainment_percentage}"
                )  # DEBUG
            else:
                po_attainment_percentage = None
                print(
                    f"    Total weight for PO {po.code} is 0. Attainment set to None."
                )  # DEBUG

        # Create or update PO Attainment record
        po_attainment, created = ProgramOutcomeAttainment.objects.update_or_create(
            program_outcome=po,
            academic_year=academic_year_obj,
            defaults={"attainment_percentage": po_attainment_percentage},
        )
        print(
            f"  PO Attainment record for {po.code} saved: {po_attainment.attainment_percentage}% (Created: {created})"
        )  # DEBUG

    print(
        f"\n--- Finished PO Attainment Calculation for Year: {academic_year_obj} ---"
    )  # DEBUG
    return True


# --- Views to Trigger Calculation ---


@login_required
@user_passes_test(
    is_admin_or_hod, login_url="/accounts/login/"
)  # Only Admin/HOD can trigger
def calculate_attainment_view(request):
    academic_years = AcademicYear.objects.all().order_by("-start_date")
    courses = Course.objects.all().order_by("code")

    if request.method == "POST":
        calc_type = request.POST.get("calc_type")

        # Get IDs from the CO calculation section's fields (new names)
        co_academic_year_id = request.POST.get("co_academic_year")
        co_course_id = request.POST.get("co_course")

        # Get ID from the PO calculation section's field (new name)
        po_academic_year_id = request.POST.get(
            "po_academic_year"
        )  # NEW: Changed to 'po_academic_year'

        # Initialize academic year objects based on which button was clicked
        academic_year_obj_for_co = None
        if co_academic_year_id:
            academic_year_obj_for_co = get_object_or_404(
                AcademicYear, pk=co_academic_year_id
            )

        academic_year_obj_for_po = None
        if po_academic_year_id:
            academic_year_obj_for_po = get_object_or_404(
                AcademicYear, pk=po_academic_year_id
            )

        if calc_type == "co_by_course":  # No need for 'and course_id' here, check below
            # Check if both Academic Year and Course are selected for CO calculation
            if (
                not academic_year_obj_for_co or not co_course_id
            ):  # Check for the course ID here too
                messages.error(
                    request,
                    "Please select both an Academic Year and a Course to calculate CO attainment.",
                )
            else:
                course_obj = get_object_or_404(Course, pk=co_course_id)
                with transaction.atomic():
                    success = calculate_co_attainment_for_course(
                        course_obj, academic_year_obj_for_co
                    )
                if success:
                    messages.success(
                        request,
                        f"CO Attainment calculated for Course {course_obj.code} in {academic_year_obj_for_co}!",
                    )
                else:
                    messages.error(
                        request, "Failed to calculate CO Attainment. Check logs."
                    )

        elif calc_type == "po_by_year":
            # Check if Academic Year is selected for PO calculation
            if not academic_year_obj_for_po:
                messages.error(
                    request,
                    "Please select an Academic Year to calculate PO attainment by Year.",
                )
            else:
                with transaction.atomic():
                    success = calculate_po_attainment_for_academic_year(
                        academic_year_obj_for_po
                    )
                if success:
                    messages.success(
                        request,
                        f"PO Attainment calculated for Academic Year {academic_year_obj_for_po}!",
                    )
                else:
                    messages.error(
                        request, "Failed to calculate PO Attainment. Check logs."
                    )
        else:
            messages.error(request, "Invalid calculation type or missing selections.")

        return redirect("calculate_attainment_view")  # Redirect back to the form

    context = {
        "academic_years": academic_years,
        "courses": courses,
    }
    return render(request, "academics/calculate_attainment_form.html", context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def co_attainment_report_list(request):
    academic_years = AcademicYear.objects.all().order_by("-start_date")
    courses = Course.objects.all().order_by("code")

    selected_academic_year_id = request.GET.get("academic_year")
    selected_course_id = request.GET.get("course")

    co_attainments = CourseOutcomeAttainment.objects.all()

    # Filter based on user role
    if is_faculty(request.user) and not is_admin_or_hod(request.user):
        user_profile = request.user.profile
        taught_courses = user_profile.taught_courses.all()
        co_attainments = co_attainments.filter(
            course_outcome__course__in=taught_courses
        )

    # Apply filters from GET parameters
    if selected_academic_year_id:
        co_attainments = co_attainments.filter(
            academic_year__id=selected_academic_year_id
        )
    if selected_course_id:
        co_attainments = co_attainments.filter(
            course_outcome__course__id=selected_course_id
        )

    # Optimize query with select_related and prefetch_related
    co_attainments = co_attainments.select_related(
        "course_outcome__course", "course_outcome__course__department", "academic_year"
    ).order_by(
        "-academic_year__start_date",
        "course_outcome__course__code",
        "course_outcome__code",
    )

    context = {
        "co_attainments": co_attainments,
        "academic_years": academic_years,
        "courses": courses,
        "selected_academic_year_id": selected_academic_year_id,
        "selected_course_id": selected_course_id,
        "form_title": "Course Outcome Attainment Report",
    }
    return render(request, "academics/co_attainment_report_list.html", context)


@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def po_attainment_report_list(request):
    academic_years = AcademicYear.objects.all().order_by("-start_date")

    selected_academic_year_id = request.GET.get("academic_year")

    po_attainments = ProgramOutcomeAttainment.objects.all()

    # Apply filters from GET parameters
    if selected_academic_year_id:
        po_attainments = po_attainments.filter(
            academic_year__id=selected_academic_year_id
        )

    # Optimize query with select_related
    po_attainments = po_attainments.select_related(
        "program_outcome", "academic_year"
    ).order_by("-academic_year__start_date", "program_outcome__code")

    context = {
        "po_attainments": po_attainments,
        "academic_years": academic_years,
        "selected_academic_year_id": selected_academic_year_id,
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
        # Pass user to the form to scope the course/rubric dropdowns
        form = AssignmentForm(request.POST, instance=assignment, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Assignment '{assignment.title}' updated successfully.")
            return redirect('assignment_list')
    else:
        form = AssignmentForm(instance=assignment, user=request.user)
        
    return render(request, 'academics/assignment_form.html', {
        'form': form, 
        'form_title': f'Update Assignment: {assignment.title}'
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