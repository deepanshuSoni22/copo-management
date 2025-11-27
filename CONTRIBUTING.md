# Contributing to COPO Management System

Thank you for your interest in contributing to the COPO Management System! This guide will help you get started with development.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Database Conventions](#database-conventions)
- [Testing Guidelines](#testing-guidelines)
- [Submitting Changes](#submitting-changes)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 12 or higher
- Node.js 16 or higher (for Tailwind CSS)
- Git
- Basic understanding of Django framework

### Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/deepanshuSoni22/copo-management.git
   cd copo-management
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node.js Dependencies**
   ```bash
   npm install
   ```

5. **Configure Database**
   
   Create a PostgreSQL database:
   ```sql
   CREATE DATABASE copo_db;
   CREATE USER django_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE copo_db TO django_user;
   ```
   
   Update `copo_management_system/settings.py` with your database credentials.

6. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Load Sample Data (Optional)**
   ```bash
   python manage.py loaddata sample_data.json
   ```

9. **Start Development Servers**
   
   Terminal 1 - Django:
   ```bash
   python manage.py runserver
   ```
   
   Terminal 2 - Tailwind CSS (watch mode):
   ```bash
   npm run dev
   ```

10. **Access the Application**
    - Main app: http://127.0.0.1:8000/
    - Admin panel: http://127.0.0.1:8000/admin/

## Project Structure

```
copo_management_system/
├── academics/                  # Main academic features app
│   ├── models.py              # Database models
│   ├── views.py               # View functions (2474 lines)
│   ├── forms.py               # Form definitions (1191 lines)
│   ├── urls.py                # URL routing
│   ├── audit_utils.py         # Audit logging utilities
│   ├── validation_utils.py    # Validation functions
│   ├── export_utils.py        # PDF/Excel export
│   ├── backup_utils.py        # Backup/restore functions
│   ├── templates/academics/   # HTML templates
│   └── templatetags/          # Custom template tags
├── users/                     # User management app
│   ├── models.py             # UserProfile model
│   ├── views.py              # Authentication views
│   └── forms.py              # User forms
├── copo_management_system/   # Project configuration
│   ├── settings.py           # Django settings
│   ├── urls.py               # Root URL configuration
│   └── templates/            # Base templates
├── static/                    # Static source files
│   ├── src/input.css         # Tailwind source
│   └── dist/output.css       # Compiled CSS
├── staticfiles/              # Collected static files
├── submissions/              # Student submission uploads
├── backups/                  # Database backups
└── requirements.txt          # Python dependencies
```

## Development Workflow

### Working on Features

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write clean, documented code
   - Follow existing patterns
   - Add docstrings to functions
   - Update relevant templates

3. **Test Your Changes**
   - Test all CRUD operations
   - Verify role-based access control
   - Check form validations
   - Test on different user roles (Admin, HOD, Faculty, Student)

4. **Update Documentation**
   - Add docstrings to new functions
   - Update `.github/copilot-instructions.md` if needed
   - Update README.md for major changes

5. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

## Coding Standards

### Python Code Style

- Follow PEP 8 guidelines
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use descriptive variable names

### Function Docstrings

Every function should have a docstring:

```python
def calculate_co_attainment(course, academic_year, threshold=60.0):
    """
    Calculate Course Outcome attainment for a specific course.
    
    Args:
        course (Course): The course object
        academic_year (AcademicYear): The academic year for calculation
        threshold (float): Success threshold percentage (default: 60.0)
        
    Returns:
        dict: Dictionary containing attainment results for each CO
        
    Raises:
        ValidationError: If course has no outcomes defined
    """
    # Implementation here
```

### View Function Patterns

Always use role-based permission checks:

```python
from django.contrib.auth.decorators import login_required, user_passes_test
from academics.views import is_admin_or_hod

@login_required
@user_passes_test(is_admin_or_hod, login_url="/accounts/login/")
def your_view(request):
    # Scope data based on user role
    if is_hod(request.user):
        courses = Course.objects.filter(
            department=request.user.profile.department
        )
    else:  # Admin
        courses = Course.objects.all()
    
    # Your view logic
```

### Form Validation

Add robust validation in `clean()` methods:

```python
def clean(self):
    cleaned_data = super().clean()
    field1 = cleaned_data.get('field1')
    field2 = cleaned_data.get('field2')
    
    # Add validation logic
    if field1 and field2 and field1 > field2:
        self.add_error('field2', 'Field2 must be greater than Field1')
    
    return cleaned_data
```

### Template Conventions

- Use Django template language properly
- Load required template tags at the top
- Use Tailwind CSS classes consistently
- Follow existing form styling patterns

```django
{% extends "base.html" %}
{% load static %}
{% load academics_filters %}

{% block title %}Your Page Title{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-6">
    <!-- Your content -->
</div>
{% endblock %}
```

## Database Conventions

### Model Design

1. **Use descriptive model names**: `CourseOutcome`, not `CO`
2. **Add helpful docstrings**: Explain the purpose of each model
3. **Use appropriate field types**: Don't use CharField for numbers
4. **Define relationships clearly**: Use appropriate `related_name`
5. **Add Meta options**: `ordering`, `verbose_name`, `unique_together`

### Migrations

- Always create migrations for model changes
- Review migration files before committing
- Test migrations on a copy of production data
- Never edit existing migrations that have been deployed

```bash
python manage.py makemigrations
python manage.py migrate
```

### Query Optimization

Always use `select_related()` and `prefetch_related()`:

```python
# BAD - N+1 queries
courses = Course.objects.all()
for course in courses:
    print(course.department.name)  # Triggers new query each time

# GOOD - Single query with JOIN
courses = Course.objects.select_related('department').all()
for course in courses:
    print(course.department.name)  # No extra queries
```

## Testing Guidelines

### Manual Testing Checklist

For each new feature, test:

1. **As Admin**:
   - Can create/edit/delete all entities
   - Can view all data
   - Can access all reports

2. **As HOD**:
   - Can only access own department data
   - Cannot access other departments
   - Can manage courses in own department

3. **As Faculty**:
   - Can only access assigned courses
   - Can enter marks for enrolled students
   - Can create assignments

4. **As Student**:
   - Can view own marks and assignments
   - Can submit assignments
   - Cannot access admin features

### Edge Cases to Test

- Empty states (no data)
- Maximum values (large numbers, long text)
- Special characters in input
- Concurrent edits by multiple users
- File uploads (size limits, formats)

## Submitting Changes

### Pull Request Process

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request**
   - Use descriptive PR title
   - Explain what changes you made
   - Link related issues
   - Add screenshots for UI changes

3. **PR Title Format**
   ```
   feat: Add CO attainment calculation
   fix: Resolve duplicate PO code validation
   docs: Update contribution guide
   style: Format code with Black
   refactor: Simplify assessment form logic
   ```

4. **Wait for Review**
   - Address review comments
   - Make requested changes
   - Update PR description if needed

### Commit Message Format

Use conventional commits:

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(academics): Add bulk student enrollment
fix(validation): Prevent duplicate CO codes
docs(readme): Add installation instructions
```

## Additional Resources

### Useful Commands

```bash
# Create new app
python manage.py startapp app_name

# Make migrations
python manage.py makemigrations app_name

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver

# Django shell
python manage.py shell

# Database shell
python manage.py dbshell

# Build Tailwind CSS
npm run build

# Watch Tailwind CSS
npm run dev
```

### Debugging Tips

1. **Use Django Debug Toolbar** (install if needed)
2. **Check Django logs** in terminal
3. **Use `print()` or `logging` for debugging**
4. **Test queries in Django shell**
5. **Use browser DevTools** for frontend issues

### Getting Help

- Check existing code for patterns
- Review `.github/copilot-instructions.md`
- Ask questions in pull requests
- Refer to Django documentation

## Code Review Guidelines

### For Authors

- Self-review your changes before requesting review
- Write clear PR descriptions
- Respond promptly to feedback
- Be open to suggestions

### For Reviewers

- Be constructive and respectful
- Explain why changes are needed
- Approve when code meets standards
- Test changes locally if possible

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to the COPO Management System! 🎉
