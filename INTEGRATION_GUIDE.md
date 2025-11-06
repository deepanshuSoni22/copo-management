# Integration Guide - Export, Backup, and Audit Features

## Overview

This guide explains how to integrate the newly created utility modules into the COPO Management System. These features are production-ready but need view functions, URL routes, and template updates.

---

## 1. Prerequisites

### Install Dependencies
```bash
cd c:\Users\DEEPANSHU\Documents\simple-version\copo_management_system
venv\Scripts\activate
pip install -r requirements.txt
```

### Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

This will:
- Create the `AuditLog` table
- Add database indexes to 8 models
- Apply any pending migrations

---

## 2. Audit Logging Integration

### Module Location
`academics/audit_utils.py`

### Step 1: Add Audit Logging to Existing Views

**Pattern**: Wrap create/update/delete operations with audit logging

#### Example - Course Creation View

**Before**:
```python
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            return redirect('course_list')
```

**After**:
```python
from academics.audit_utils import log_create

def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            log_create(request.user, course, request)  # Add this line
            return redirect('course_list')
```

#### Example - Course Update View

**Before**:
```python
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_list')
```

**After**:
```python
from academics.audit_utils import log_update

def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    old_name = course.name  # Capture old value
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            updated_course = form.save()
            changes = {'name': f'{old_name}->{updated_course.name}'}  # Track changes
            log_update(request.user, updated_course, changes, request)  # Add this line
            return redirect('course_list')
```

#### Example - Course Delete View

**Before**:
```python
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        return redirect('course_list')
```

**After**:
```python
from academics.audit_utils import log_delete

def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        log_delete(request.user, course, request)  # Add BEFORE delete
        course.delete()
        return redirect('course_list')
```

### Step 2: Add Audit Log Viewer

Create a new view in `academics/views.py`:

```python
@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")
def audit_log_list(request):
    """Display audit log with filtering options."""
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    
    # Optional: Add filtering
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    model_filter = request.GET.get('model')
    if model_filter:
        logs = logs.filter(model_name=model_filter)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'action_choices': AuditLog.ACTION_CHOICES,
    }
    return render(request, 'academics/audit_log_list.html', context)
```

Add URL in `academics/urls.py`:

```python
path('audit-logs/', views.audit_log_list, name='audit_log_list'),
```

Create template `academics/templates/academics/audit_log_list.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Audit Logs</h1>
    
    <!-- Filters -->
    <form method="get" class="mb-4 flex gap-4">
        <select name="action" class="px-4 py-2 border rounded">
            <option value="">All Actions</option>
            {% for value, label in action_choices %}
            <option value="{{ value }}">{{ label }}</option>
            {% endfor %}
        </select>
        <button type="submit" class="px-4 py-2 bg-brand-purple text-white rounded">Filter</button>
    </form>
    
    <!-- Logs Table -->
    <table class="w-full border">
        <thead>
            <tr class="bg-gray-100">
                <th class="p-2">Timestamp</th>
                <th class="p-2">User</th>
                <th class="p-2">Action</th>
                <th class="p-2">Model</th>
                <th class="p-2">Object</th>
                <th class="p-2">IP Address</th>
            </tr>
        </thead>
        <tbody>
            {% for log in logs %}
            <tr>
                <td class="p-2">{{ log.timestamp|date:"Y-m-d H:i:s" }}</td>
                <td class="p-2">{{ log.user.username }}</td>
                <td class="p-2">{{ log.get_action_display }}</td>
                <td class="p-2">{{ log.model_name }}</td>
                <td class="p-2">{{ log.object_repr }}</td>
                <td class="p-2">{{ log.ip_address }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <!-- Pagination -->
    <div class="mt-4">
        {% if logs.has_previous %}
        <a href="?page=1">&laquo; First</a>
        <a href="?page={{ logs.previous_page_number }}">Previous</a>
        {% endif %}
        
        <span>Page {{ logs.number }} of {{ logs.paginator.num_pages }}</span>
        
        {% if logs.has_next %}
        <a href="?page={{ logs.next_page_number }}">Next</a>
        <a href="?page={{ logs.paginator.num_pages }}">Last &raquo;</a>
        {% endif %}
    </div>
</div>
{% endblock %}
```

### Step 3: Add to Navigation

Update `base.html` sidebar (Admin section):

```html
{% if user.profile.role == 'ADMIN' %}
<li>
    <a href="{% url 'audit_log_list' %}" class="block px-4 py-2 hover:bg-gray-100">
        📋 Audit Logs
    </a>
</li>
{% endif %}
```

---

## 3. Export Functionality Integration

### Module Location
`academics/export_utils.py`

### Step 1: Add Export Views

Add to `academics/views.py`:

```python
from academics.export_utils import (
    export_co_po_mapping_pdf,
    export_co_attainment_pdf,
    export_co_attainment_excel,
    export_po_attainment_excel
)
from academics.audit_utils import log_export

@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def export_copo_mapping(request, course_id):
    """Export CO-PO mapping matrix as PDF."""
    course = get_object_or_404(Course, pk=course_id)
    
    # Get mappings
    co_po_mappings = COPOMapping.objects.filter(
        course_outcome__course=course
    ).select_related(
        'course_outcome',
        'program_outcome'
    ).order_by('course_outcome__code', 'program_outcome__code')
    
    # Generate PDF
    response = export_co_po_mapping_pdf(course, co_po_mappings)
    
    # Log export
    log_export(request.user, 'COPOMapping', f'CO-PO Matrix for {course.code}', request)
    
    return response

@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def export_co_attainment(request):
    """Export CO attainment report as PDF or Excel."""
    format_type = request.GET.get('format', 'pdf')
    
    # Get attainments with filters
    attainments = CourseOutcomeAttainment.objects.select_related(
        'course_outcome__course__department',
        'academic_year'
    ).order_by('-academic_year__start_date', 'course_outcome__course__code')
    
    # Apply filters from GET params
    dept_id = request.GET.get('department')
    if dept_id:
        attainments = attainments.filter(course_outcome__course__department_id=dept_id)
    
    year_id = request.GET.get('academic_year')
    if year_id:
        attainments = attainments.filter(academic_year_id=year_id)
    
    # Build filters dict for PDF
    filters = {
        'department': Department.objects.get(pk=dept_id).name if dept_id else 'All',
        'academic_year': AcademicYear.objects.get(pk=year_id).name if year_id else 'All',
    }
    
    # Generate export
    if format_type == 'excel':
        response = export_co_attainment_excel(attainments)
    else:
        response = export_co_attainment_pdf(attainments, filters)
    
    # Log export
    log_export(request.user, 'CourseOutcomeAttainment', f'CO Attainment ({format_type.upper()})', request)
    
    return response

@login_required
@user_passes_test(is_admin_or_hod_or_faculty, login_url="/accounts/login/")
def export_po_attainment(request):
    """Export PO attainment report as Excel."""
    attainments = ProgramOutcomeAttainment.objects.select_related(
        'program_outcome__department',
        'academic_year'
    ).order_by('-academic_year__start_date', 'program_outcome__code')
    
    # Apply filters
    dept_id = request.GET.get('department')
    if dept_id:
        attainments = attainments.filter(program_outcome__department_id=dept_id)
    
    response = export_po_attainment_excel(attainments)
    
    # Log export
    log_export(request.user, 'ProgramOutcomeAttainment', 'PO Attainment (Excel)', request)
    
    return response
```

### Step 2: Add URL Routes

In `academics/urls.py`:

```python
# Export URLs
path('export/copo-mapping/<int:course_id>/', views.export_copo_mapping, name='export_copo_mapping'),
path('export/co-attainment/', views.export_co_attainment, name='export_co_attainment'),
path('export/po-attainment/', views.export_po_attainment, name='export_po_attainment'),
```

### Step 3: Add Export Buttons to Templates

#### CO-PO Mapping Page (`copo_mapping_form.html`)

Add after the mapping table:

```html
<div class="mt-4">
    <a href="{% url 'export_copo_mapping' course.id %}" 
       class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
        📄 Export as PDF
    </a>
</div>
```

#### CO Attainment Report Page (`co_attainment_report_list.html`)

Add to page header:

```html
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">CO Attainment Report</h1>
    <div class="flex gap-2">
        <a href="{% url 'export_co_attainment' %}?format=pdf&{{ request.GET.urlencode }}" 
           class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
            📄 PDF
        </a>
        <a href="{% url 'export_co_attainment' %}?format=excel&{{ request.GET.urlencode }}" 
           class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
            📊 Excel
        </a>
    </div>
</div>
```

#### PO Attainment Report Page

Similar pattern:

```html
<a href="{% url 'export_po_attainment' %}?{{ request.GET.urlencode }}" 
   class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
    📊 Export Excel
</a>
```

---

## 4. Backup & Restore Integration

### Module Location
`academics/backup_utils.py`

### Step 1: Create Backup Views

Add to `academics/views.py`:

```python
from academics.backup_utils import (
    create_backup,
    create_backup_download_response,
    restore_from_backup,
    list_available_backups,
    delete_old_backups
)
from django.contrib import messages

@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")
def backup_create(request):
    """Create a database backup."""
    if request.method == 'POST':
        backup_type = request.POST.get('backup_type', 'full')
        success, filepath, message = create_backup(backup_type=backup_type)
        
        if success:
            messages.success(request, message)
            log_export(request.user, 'Backup', f'Created {backup_type} backup', request)
            # Offer download
            return create_backup_download_response(filepath)
        else:
            messages.error(request, f'Backup failed: {message}')
            return redirect('backup_manage')
    
    context = {
        'backup_types': ['full', 'selective'],
    }
    return render(request, 'academics/backup_create.html', context)

@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")
def backup_manage(request):
    """List and manage backups."""
    backups = list_available_backups()
    
    context = {
        'backups': backups,
    }
    return render(request, 'academics/backup_manage.html', context)

@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")
def backup_restore(request, filename):
    """Restore from backup."""
    if request.method == 'POST':
        restore_mode = request.POST.get('restore_mode', 'merge')
        filepath = os.path.join(settings.BASE_DIR, 'backups', filename)
        
        success, message, stats = restore_from_backup(filepath, restore_mode=restore_mode)
        
        if success:
            messages.success(request, f'Restore successful: {message}')
            log_import(request.user, 'Backup', f'Restored from {filename}', request)
        else:
            messages.error(request, f'Restore failed: {message}')
        
        return redirect('backup_manage')
    
    context = {
        'filename': filename,
        'restore_modes': ['merge', 'replace'],
    }
    return render(request, 'academics/backup_restore.html', context)
```

### Step 2: Add URL Routes

In `academics/urls.py`:

```python
# Backup URLs
path('backup/create/', views.backup_create, name='backup_create'),
path('backup/manage/', views.backup_manage, name='backup_manage'),
path('backup/restore/<str:filename>/', views.backup_restore, name='backup_restore'),
```

### Step 3: Create Templates

#### `backup_create.html`

```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Create Backup</h1>
    
    <form method="post" class="max-w-md">
        {% csrf_token %}
        
        <div class="mb-4">
            <label class="block mb-2 font-semibold">Backup Type</label>
            <select name="backup_type" class="w-full px-4 py-2 border rounded">
                <option value="full">Full Backup</option>
                <option value="selective">Selective Backup (Academic Data Only)</option>
            </select>
        </div>
        
        <button type="submit" class="px-6 py-2 bg-brand-purple text-white rounded hover:bg-purple-700">
            💾 Create Backup
        </button>
    </form>
</div>
{% endblock %}
```

#### `backup_manage.html`

```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">Manage Backups</h1>
        <a href="{% url 'backup_create' %}" class="px-4 py-2 bg-brand-purple text-white rounded">
            ➕ Create Backup
        </a>
    </div>
    
    <table class="w-full border">
        <thead>
            <tr class="bg-gray-100">
                <th class="p-2">Filename</th>
                <th class="p-2">Size</th>
                <th class="p-2">Created</th>
                <th class="p-2">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for backup in backups %}
            <tr>
                <td class="p-2">{{ backup.filename }}</td>
                <td class="p-2">{{ backup.size_mb }} MB</td>
                <td class="p-2">{{ backup.created|date:"Y-m-d H:i" }}</td>
                <td class="p-2">
                    <a href="{% url 'backup_restore' backup.filename %}" 
                       class="text-blue-600 hover:underline">
                        Restore
                    </a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

### Step 4: Add to Navigation

Update `base.html` sidebar (Admin section):

```html
{% if user.profile.role == 'ADMIN' %}
<li>
    <a href="{% url 'backup_manage' %}" class="block px-4 py-2 hover:bg-gray-100">
        💾 Backups
    </a>
</li>
{% endif %}
```

---

## 5. Testing Checklist

### Audit Logging Tests
- [ ] Create a course → Check audit log entry
- [ ] Update a course → Verify changes tracked
- [ ] Delete a course → Confirm deletion logged
- [ ] Filter audit logs by action type
- [ ] Filter audit logs by model name

### Export Tests
- [ ] Export CO-PO mapping as PDF → Verify formatting
- [ ] Export CO attainment as PDF → Check filters applied
- [ ] Export CO attainment as Excel → Verify data accuracy
- [ ] Export PO attainment as Excel → Confirm calculations

### Backup Tests
- [ ] Create full backup → Verify file created
- [ ] Create selective backup → Check file size smaller
- [ ] List backups → Confirm all backups shown
- [ ] Restore backup (merge mode) → No data loss
- [ ] Restore backup (replace mode) → WARNING: Use with test data only

---

## 6. Common Issues & Solutions

### Issue: PDF Export Fails

**Symptoms**: 500 error or blank PDF

**Solution**:
- Check ReportLab installed: `pip show reportlab`
- Verify course has CO-PO mappings
- Check for Unicode characters in course names

### Issue: Backup Directory Not Found

**Symptoms**: "Backup directory does not exist"

**Solution**:
```bash
mkdir c:\Users\DEEPANSHU\Documents\simple-version\copo_management_system\backups
```

### Issue: Audit Log Not Recording

**Symptoms**: No entries in audit log after actions

**Solution**:
- Verify migrations run: `python manage.py migrate`
- Check `log_create()` called AFTER `.save()`
- Ensure request object passed correctly

---

## 7. Performance Monitoring

### Check Query Count

Add Django Debug Toolbar:

```bash
pip install django-debug-toolbar
```

In `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # ...
]

INTERNAL_IPS = ['127.0.0.1']
```

In `urls.py`:

```python
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
```

### Monitor Export Times

Add timing to export views:

```python
import time

def export_co_attainment(request):
    start_time = time.time()
    
    # ... export logic ...
    
    elapsed = time.time() - start_time
    print(f"Export took {elapsed:.2f} seconds")
    
    return response
```

---

## 8. Security Considerations

### File Upload Security

In `settings.py`:

```python
# Restrict file uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Allowed file types for submissions
ALLOWED_SUBMISSION_EXTENSIONS = ['.pdf', '.docx', '.zip', '.txt']
```

### Backup Security

- Store backups outside web root
- Add `.gitignore` entry for `backups/` directory
- Implement periodic cleanup with `delete_old_backups(days_to_keep=30)`

### Audit Log Privacy

- Consider GDPR compliance for IP addresses
- Implement log retention policy
- Add admin-only access to audit logs

---

## 9. Deployment Checklist

### Before Deploying to Production

- [ ] Run all migrations
- [ ] Test all export formats with real data
- [ ] Create test backup and verify restore
- [ ] Check audit logging on all CRUD operations
- [ ] Verify role-based access controls
- [ ] Test with large datasets (>1000 records)
- [ ] Configure backup storage location
- [ ] Set up automated backup schedule (cron/Task Scheduler)

### Production Environment Variables

Add to `.env` or production settings:

```env
BACKUP_DIR=/path/to/secure/backups
MAX_EXPORT_ROWS=10000
AUDIT_LOG_RETENTION_DAYS=365
```

---

## 10. Next Steps

After completing this integration:

1. **Student Performance UI Enhancement** - Improve mark entry interface
2. **Automated Reports** - Schedule weekly attainment reports
3. **Email Notifications** - Alert on backup failures or low attainment
4. **Dashboard Widgets** - Add audit activity and backup status to admin dashboard

---

## Support

For integration issues:
- Check `CONTRIBUTING.md` for development setup
- Review `OPTIMIZATION_SUMMARY.md` for database performance
- Consult `IMPLEMENTATION_SUMMARY.md` for feature details

**Last Updated**: December 2024
