# COPO Management System - AI Coding Agent Instructions

## Project Overview
Django-based outcome-based education (OBE) system for managing Course Outcomes (CO) and Program Outcomes (PO) assessment in educational institutions. Tracks student performance, calculates attainment, and generates compliance reports.

## Architecture & Data Model

### Core Entity Hierarchy
```
AcademicYear → AcademicDepartment → Semester → Course → CourseOutcome
Department → ProgramOutcome
UserProfile (extends User) → role-based access (ADMIN/HOD/FACULTY/STUDENT)
```

### Critical Relationships
- **CO-PO Mapping**: `COPOMapping` links `CourseOutcome` to `ProgramOutcome` with correlation levels (0=None, 1=Low, 2=Medium, 3=High)
- **Assessment Chain**: `Course` → `Assessment` → `StudentMark` → `CourseOutcomeAttainment` → `ProgramOutcomeAttainment`
- **Course Plans**: Each `Course` has ONE `CoursePlan` (OneToOne) containing objectives, lesson plans, CIA components
- **Enrollment**: Students linked to courses via `Course.students` M2M field

### Key Design Patterns
- **Year-scoped data**: Most entities link to `AcademicYear` for temporal isolation
- **Department-scoped HODs**: HODs assigned via `AcademicDepartment` (not directly to `Department`) for year-specific management
- **Rubric-based grading**: Assignments can use reusable `Rubric` with multiple `RubricCriterion`, scored via `RubricScore` on each `Submission`

## Role-Based Access Control

### Permission Helpers (academics/views.py)
Always use these helper functions instead of raw role checks:
```python
is_admin(user)                    # ADMIN only
is_hod(user)                      # HOD only
is_faculty(user)                  # FACULTY or HOD
is_admin_or_hod(user)            # ADMIN or HOD
is_admin_or_hod_or_faculty(user) # ADMIN, HOD, or FACULTY
is_student(user)                  # STUDENT only
```

### View Decorators
```python
@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def your_view(request):
    # Scope querysets based on user role
    if is_hod(request.user):
        departments = Department.objects.filter(pk=request.user.profile.department.pk)
    else:  # Admin
        departments = Department.objects.all()
```

### Data Scoping Rules
- **HOD**: Can only access data for `user.profile.department`
- **Faculty**: Can only access courses in `user.profile.taught_courses.all()`
- **Students**: Access only their enrolled courses via `user.profile.enrolled_courses.all()`

## Attainment Calculation

### CO Attainment (Direct Assessment)
Function: `calculate_co_attainment_for_course(course_obj, academic_year_obj, success_threshold=60.0)`
- Aggregates `StudentMark` for assessments linked to each CO
- Calculates percentage of students meeting threshold
- Updates/creates `CourseOutcomeAttainment` records

### PO Attainment (Indirect via CO-PO Mapping)
Function: `calculate_po_attainment_for_department(department_obj, academic_year_obj)`
- Fetches all CO attainments for department courses
- Weighted average using `COPOMapping.correlation_level` as weights
- Formula: `SUM(CO_attainment * correlation_level) / SUM(correlation_level)`

### Critical Rules
- Always calculate CO before PO attainment
- Use `select_related()` and `prefetch_related()` to optimize attainment queries
- Attainment stored as `DecimalField(max_digits=5, decimal_places=2)` (percentage)

## Frontend Architecture

### Styling
- **Tailwind CSS 3.4**: Custom config in `tailwind.config.js`
- **Custom colors**: `brand-purple` (#604993), `brand-yellow` (#FBB816), `gray-default` (#767672)
- **Build command**: `npm run dev` (watch mode) or `npm run build` (production)
- **Font**: Poppins (extended in Tailwind config)

### Template Structure
- Base template: `copo_management_system/templates/base.html`
- Role-based sidebar navigation (lines 14-100+)
- All forms use Tailwind classes: `mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg...`

### Template Patterns
```django
{% load static %}
{% load academics_filters %}  {# Custom filters in academics/templatetags/ #}

{# Role-based content #}
{% if user.profile.role == 'FACULTY' %}
    {# Faculty-specific content #}
{% endif %}
```

## Development Workflow

### Database
- **PostgreSQL** (psycopg2-binary 2.9.10)
- Database: `copo_db`, User: `django_user` (see settings.py)
- Always run migrations after model changes: `python manage.py makemigrations && python manage.py migrate`

### Key Commands
```bash
# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# Development
python manage.py runserver          # Django dev server
npm run dev                         # Tailwind watch mode

# Static files
python manage.py collectstatic      # Collect to staticfiles/
```

### Media Files
- Student submissions upload to `submissions/YYYY/MM/DD/` (see `Submission.file`)
- Served via `MEDIA_URL='/submissions/'` in DEBUG mode

## Forms & Formsets

### Common Pattern
```python
from django.forms import inlineformset_factory

# In forms.py
CourseOutcomeFormSet = inlineformset_factory(
    Course, CourseOutcome,
    form=CourseOutcomeForm,
    extra=1, can_delete=True
)

# In views.py
if request.method == 'POST':
    formset = CourseOutcomeFormSet(request.POST, instance=course)
    if formset.is_valid():
        formset.save()
```

### Key Formsets
- `CourseOutcomeFormSet`: Manage COs when creating/editing Course
- `StudentMarkFormSet`: Bulk mark entry for assessments
- `RubricCriterionFormSet`: Define criteria for rubrics
- `WeeklyLessonPlanFormSet`, `CIAComponentFormSet`: Course plan components

## Common Pitfalls

### 1. Forgetting Role-Based Filtering
❌ BAD:
```python
courses = Course.objects.all()
```
✅ GOOD:
```python
if is_faculty(request.user):
    courses = request.user.profile.taught_courses.all()
elif is_hod(request.user):
    courses = Course.objects.filter(department=request.user.profile.department)
```

### 2. Missing select_related/prefetch_related
❌ BAD:
```python
co_attainments = CourseOutcomeAttainment.objects.all()  # N+1 queries
```
✅ GOOD:
```python
co_attainments = CourseOutcomeAttainment.objects.select_related(
    'course_outcome__course__department', 'academic_year'
).order_by('-academic_year__start_date')
```

### 3. Not Using Transactions for Attainment
```python
from django.db import transaction

@transaction.atomic
def calculate_co_attainment_for_course(course_obj, academic_year_obj):
    # Ensures all CO attainments saved or none
```

### 4. Hardcoded Semesters
Use `SEMESTER_CHOICES` from `academics/forms.py` (lines 98-110), not hardcoded strings.

## URL Naming Convention
All URLs use underscores: `course_outcome_list`, `copo_mapping_view`, `student_mark_entry`
Prefix patterns: `/academics/` for academic features, `/accounts/` for auth

## Testing & Debugging
- No automated tests currently exist
- Use Django admin (`/admin/`) for data inspection
- Enable DEBUG=True in settings.py for development (already set)
- Check `academics/models.py` for `unique_together` constraints to avoid integrity errors

## Key Files Reference
- **Models**: `academics/models.py` (700+ lines, 25+ models)
- **Views**: `academics/views.py` (2474 lines, function-based views)
- **Forms**: `academics/forms.py` (1124 lines)
- **URLs**: `academics/urls.py` (75+ routes)
- **Settings**: `copo_management_system/settings.py`
- **Base template**: `copo_management_system/templates/base.html`

## API Endpoints
Two helper APIs for dynamic dropdowns:
- `GET /academics/api/get-course-outcomes/<course_id>/` → JSON list of COs
- `GET /academics/api/get-courses-by-department/<department_id>/` → JSON list of courses

## When Adding Features
1. Check role permissions FIRST
2. Scope querysets by department/courses if HOD/Faculty
3. Use existing helper functions (`is_admin()`, etc.)
4. Add Tailwind classes to match existing forms
5. Use `@transaction.atomic` for multi-model updates
6. Add URL to `academics/urls.py` with underscore naming
7. Update sidebar in `base.html` if adding navigation item
8. Log significant actions using `audit_utils.log_action()`
9. Add validation using functions from `validation_utils.py`
10. Include docstrings for all new functions

## New Features & Utilities

### Audit Logging System
- **Model**: `AuditLog` tracks all CREATE, UPDATE, DELETE, CALCULATE, EXPORT, IMPORT actions
- **Usage**: Import from `academics.audit_utils`
  ```python
  from academics.audit_utils import log_create, log_update, log_delete
  
  # After creating an object
  log_create(request.user, new_course, request)
  
  # After updating
  log_update(request.user, course, changes={'name': 'old->new'}, request)
  
  # Before deleting
  log_delete(request.user, course, request)
  ```
- **View logs**: Admin panel `/admin/academics/auditlog/`

### Enhanced Validation
- **Module**: `academics/validation_utils.py`
- **Key functions**:
  - `validate_outcome_code()` - Validates CO/PO code format
  - `validate_duplicate_outcome()` - Prevents duplicate codes
  - `validate_correlation_level()` - Validates CO-PO mapping weights
  - `validate_assessment_marks()` - Validates marks against max marks
  - `validate_co_po_mapping_completeness()` - Checks mapping coverage
- **Form integration**: Validation is integrated into forms.py
  - CourseOutcomeForm validates CO code format and RBT levels
  - ProgramOutcomeForm validates PO code format
  - StudentMarkForm validates marks against assessment max_marks

### Export Functionality
- **Module**: `academics/export_utils.py`
- **PDF Export**:
  ```python
  from academics.export_utils import export_co_po_mapping_pdf, export_co_attainment_pdf
  
  # Export CO-PO mapping
  response = export_co_po_mapping_pdf(course, co_po_mappings)
  
  # Export CO attainment
  response = export_co_attainment_pdf(co_attainments, filters)
  ```
- **Excel Export**:
  ```python
  from academics.export_utils import export_co_attainment_excel, export_po_attainment_excel
  
  response = export_co_attainment_excel(co_attainments)
  response = export_po_attainment_excel(po_attainments)
  ```
- **Dependencies**: ReportLab (PDF), openpyxl (Excel) - added to requirements.txt

### Backup & Restore System
- **Module**: `academics/backup_utils.py`
- **Create Backup**:
  ```python
  from academics.backup_utils import create_backup, create_backup_download_response
  
  success, filepath, message = create_backup(backup_type='full')
  if success:
      response = create_backup_download_response(filepath)
  ```
- **Restore Backup**:
  ```python
  from academics.backup_utils import restore_from_backup
  
  success, message, stats = restore_from_backup(filepath, restore_mode='merge')
  ```
- **List Backups**: `list_available_backups()` returns all backup files with metadata
- **Auto-cleanup**: `delete_old_backups(days_to_keep=30)` removes old backups
- **Backup Directory**: `backups/` in project root (create if doesn't exist)

## Updated File Structure

```
academics/
├── models.py                  # +AuditLog model
├── views.py                   # (existing, 2474 lines)
├── forms.py                   # +Enhanced validation (1211 lines)
├── audit_utils.py             # NEW: Audit logging functions
├── validation_utils.py        # NEW: Validation helpers
├── export_utils.py            # NEW: PDF/Excel export functions
├── backup_utils.py            # NEW: Backup/restore utilities
└── templatetags/
    └── academics_filters.py
```
