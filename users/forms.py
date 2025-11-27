# users/forms.py
import csv
import io
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import UserProfile, UserRole  # Import your custom models
from academics.models import Department  # <-- Make sure to import Department


class UserProfileForm(forms.ModelForm):
    """
    Form for editing UserProfile fields (e.g., role).
    This will be used as an inline form or combined with UserForm.
    """

    role = forms.ChoiceField(
        choices=UserRole.choices,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="User Role",
    )

    class Meta:
        model = UserProfile
        fields = ["role"]


class UserCreateForm(UserCreationForm):
    """
    A form that creates a user, with additional fields for the UserProfile.
    """

    role = forms.ChoiceField(
        choices=UserRole.choices,
        initial=UserRole.STUDENT,  # Default new users to student
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="User Role",
    )

    # --- ADD THE DEPARTMENT FIELD HERE ---
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,  # Make it optional, as not all roles need a department
        widget=forms.Select(attrs={"class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm"}),
        label="Department"
    )

    class Meta(UserCreationForm.Meta):
        model = User  # Still uses Django's User model
        fields = UserCreationForm.Meta.fields + (
            "first_name",
            "last_name",
            "email",
        )  # Add optional name/email fields
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "password": forms.PasswordInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
        }

    # Custom save method to also create the UserProfile
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            # Create UserProfile instance
            UserProfile.objects.create(user=user, role=self.cleaned_data["role"], department=self.cleaned_data.get("department"))
        return user


class UserUpdateForm(UserChangeForm):
    role = forms.ChoiceField(
        choices=UserRole.choices,
        widget=forms.Select(
            attrs={
                "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
            }
        ),
        label="User Role",
    )

    # --- 1. ADD THE DEPARTMENT FIELD DEFINITION ---
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False, # Optional, as not all roles need a department
        widget=forms.Select(attrs={"class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm"}),
        label="Department"
    )

    class Meta(UserChangeForm.Meta):
        model = User
        # Explicitly list the fields you want to manage for the User model
        # Do NOT use UserChangeForm.Meta.fields directly, as it includes password and other fields
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )  # Specify exactly what fields to expose
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-base"
                }
            ),
        }
        exclude = (
            "password",
        )  # Ensure password field is excluded (already handled by default by UserChangeForm not having it by default)

    def __init__(self, *args, **kwargs):
        # NEW: Pop 'request' out of kwargs before passing to super()
        self.request = kwargs.pop("request", None)  # Store request if it exists

        super().__init__(*args, **kwargs)  # Now this won't receive 'request'

        # Populate the role field from the UserProfile instance
        if self.instance and hasattr(self.instance, "profile"):
            profile = self.instance.profile
            self.fields["role"].initial = profile.role
            self.fields["department"].initial = profile.department

        # Remove password-related fields as they are handled separately by Django's auth forms
        if "password" in self.fields:
            del self.fields["password"]

        # Now use self.request for conditional logic
        if (
            self.instance and self.instance.is_superuser
        ):  # User being edited is superuser
            if "is_superuser" in self.fields:
                self.fields["is_superuser"].disabled = True
                self.fields["is_superuser"].help_text = (
                    "Superuser status can only be changed in Django Admin."
                )
        # Only apply this field removal logic if self.request is present and it's not a superuser
        elif (
            self.request and not self.request.user.is_superuser
        ):  # Requesting user is not superuser
            if "is_superuser" in self.fields:
                del self.fields["is_superuser"]
            if (
                "groups" in self.fields
            ):  # Common to remove for non-superusers in custom forms
                del self.fields["groups"]
            if (
                "user_permissions" in self.fields
            ):  # Common to remove for non-superusers in custom forms
                del self.fields["user_permissions"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            # Update UserProfile instance
            user_profile, created = UserProfile.objects.update_or_create(
                user=user, defaults={"role": self.cleaned_data["role"], "department": self.cleaned_data.get("department")}
            )
        return user


class BulkUserUploadForm(forms.Form):
    """
        Form for uploading a CSV file to create multiple users at once.
        Expected CSV columns (flexible):
            - username, first_name, last_name, email, role, password
            - department_id (optional) OR department (optional, department name/code)
    """
    csv_file = forms.FileField(
        label='CSV File',
    help_text='Upload a CSV file with columns: username, first_name, last_name, email, role, [department_id|department], password',
        widget=forms.FileInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            raise ValidationError('File must be a CSV file.')
        
        # Check file size (max 5MB)
        if csv_file.size > 5 * 1024 * 1024:
            raise ValidationError('File size must not exceed 5MB.')
        
        return csv_file
    
    def parse_csv(self):
        """
        Parse the CSV file and return a list of user data dictionaries.
        Also returns a list of errors if any validation fails.
        """
        csv_file = self.cleaned_data['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        users_data = []
        errors = []

        required_columns = ['username', 'first_name', 'last_name', 'email', 'role']
        
        # Check if all required columns are present
        if not all(col in reader.fieldnames for col in required_columns):
            errors.append(f"CSV must contain these columns: {', '.join(required_columns)}")
            return users_data, errors
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
            # Validate username
            username = row.get('username', '').strip()
            if not username:
                errors.append(f"Row {row_num}: Username is required")
                continue
            
            if User.objects.filter(username=username).exists():
                errors.append(f"Row {row_num}: Username '{username}' already exists")
                continue
            
            # Validate email
            email = row.get('email', '').strip()
            if email and User.objects.filter(email=email).exists():
                errors.append(f"Row {row_num}: Email '{email}' already exists")
                continue
            
            # Validate role
            role = row.get('role', '').strip().upper()
            if role not in dict(UserRole.choices):
                errors.append(f"Row {row_num}: Invalid role '{role}'. Must be one of: {', '.join(dict(UserRole.choices).keys())}")
                continue
            
            # Get department (optional)
            # Resolve department by ID or by name/code
            department = None
            from academics.models import Department
            department_id = row.get('department_id', '').strip()
            department_name = row.get('department', '').strip()

            if department_id:
                try:
                    department = Department.objects.get(id=department_id)
                except Department.DoesNotExist:
                    errors.append(f"Row {row_num}: Department with ID '{department_id}' does not exist")
                    continue
            elif department_name:
                # Try name first, then code field if model has one
                try:
                    department = Department.objects.get(name__iexact=department_name)
                except Department.DoesNotExist:
                    # Fallback: try code if exists; if not, report error
                    try:
                        department = Department.objects.get(code__iexact=department_name)
                    except Exception:
                        errors.append(f"Row {row_num}: Department '{department_name}' not found by name or code")
                        continue
            
            # Get password (default to username if not provided)
            password = row.get('password', '').strip() or username
            
            users_data.append({
                'username': username,
                'first_name': row.get('first_name', '').strip(),
                'last_name': row.get('last_name', '').strip(),
                'email': email,
                'role': role,
                'department': department,
                'password': password,
                'row_num': row_num
            })
        
        return users_data, errors
