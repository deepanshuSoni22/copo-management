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
            # FIX: Use get_or_create to work with signals
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": self.cleaned_data["role"],
                    "department": self.cleaned_data.get("department")
                }
            )
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
        
        # FIX: Reset file pointer to beginning before reading
        csv_file.seek(0)
        
        try:
            decoded_file = csv_file.read().decode('utf-8-sig')  # FIX: Use utf-8-sig to handle BOM
        except UnicodeDecodeError:
            try:
                csv_file.seek(0)
                decoded_file = csv_file.read().decode('latin-1')  # Fallback encoding
                print("⚠️ WARNING: Used latin-1 encoding as fallback")
            except Exception as e:
                errors = [f"Failed to decode CSV file: {str(e)}"]
                return [], errors

        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        users_data = []
        errors = []

        # FIX: Updated required columns to match actual CSV format
        required_columns = ['username', 'first_name', 'last_name', 'email', 'role']
        
        # Check if all required columns are present
        if not reader.fieldnames:
            errors.append("CSV file appears to be empty or invalid")
            print("❌ ERROR: CSV has no fieldnames")
            return users_data, errors
        
        # FIX: Better debugging - log original fieldnames
        print(f"📋 Original CSV fieldnames: {reader.fieldnames}")
        print(f"📋 Fieldnames repr: {[repr(f) for f in reader.fieldnames]}")
        
        # Normalize fieldnames (strip whitespace and handle BOM)
        reader.fieldnames = [field.strip().lstrip('\ufeff') for field in reader.fieldnames]
        print(f"✅ Normalized fieldnames: {reader.fieldnames}")
        
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            error_msg = f"CSV must contain these columns: {', '.join(required_columns)}. Missing: {', '.join(missing_columns)}"
            errors.append(error_msg)
            print(f"❌ ERROR: {error_msg}")
            print(f"   Available columns: {reader.fieldnames}")
            return users_data, errors
        
        # Get valid role choices for validation
        valid_roles = [choice[0] for choice in UserRole.choices]  # ['ADMIN', 'HOD', 'FACULTY', 'STUDENT']
        print(f"✅ Valid roles: {valid_roles}")
        
        row_count = 0
        for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
            row_count += 1
            # Strip all values in the row
            row = {k: v.strip() if v else '' for k, v in row.items()}
            
            print(f"\n📝 Processing row {row_num}: {row.get('username', 'NO_USERNAME')}")
            
            # Validate username
            username = row.get('username', '')
            if not username:
                error_msg = f"Row {row_num}: Username is required"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")
                continue
            
            if User.objects.filter(username=username).exists():
                error_msg = f"Row {row_num}: Username '{username}' already exists"
                errors.append(error_msg)
                print(f"   ⚠️ {error_msg}")
                continue
            
            # Validate email
            email = row.get('email', '')
            if email and User.objects.filter(email=email).exists():
                error_msg = f"Row {row_num}: Email '{email}' already exists"
                errors.append(error_msg)
                print(f"   ⚠️ {error_msg}")
                continue
            
            # FIX: Validate role with proper uppercase conversion
            role = row.get('role', '').strip().upper()
            print(f"   🔍 Role before validation: '{row.get('role', '')}' -> after: '{role}'")
            
            if not role:
                error_msg = f"Row {row_num}: Role is required"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")
                continue
            
            if role not in valid_roles:
                error_msg = f"Row {row_num}: Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")
                continue
            
            print(f"   ✅ Role validated: {role}")
            
            # Get department (optional)
            department = None
            department_id = None
            from academics.models import Department
            
            dept_id_str = row.get('department_id', '')
            department_name = row.get('department', '')

            if dept_id_str:
                try:
                    department = Department.objects.get(id=int(dept_id_str))
                    department_id = department.id
                    print(f"   ✅ Department found by ID: {department.name}")
                except (ValueError, Department.DoesNotExist):
                    error_msg = f"Row {row_num}: Department with ID '{dept_id_str}' does not exist"
                    errors.append(error_msg)
                    print(f"   ❌ {error_msg}")
                    continue
            elif department_name:
                print(f"   🔍 Looking up department: '{department_name}'")
                try:
                    department = Department.objects.get(name__iexact=department_name)
                    department_id = department.id
                    print(f"   ✅ Department found (exact match): {department.name}")
                except Department.DoesNotExist:
                    try:
                        department = Department.objects.get(name__istartswith=department_name)
                        department_id = department.id
                        print(f"   ✅ Department found (partial match): {department.name}")
                    except Department.DoesNotExist:
                        error_msg = f"Row {row_num}: Department '{department_name}' not found"
                        errors.append(error_msg)
                        print(f"   ❌ {error_msg}")
                        continue
                    except Department.MultipleObjectsReturned:
                        matches = Department.objects.filter(name__istartswith=department_name).values_list('name', flat=True)
                        error_msg = f"Row {row_num}: Multiple departments match '{department_name}': {', '.join(matches)}"
                        errors.append(error_msg)
                        print(f"   ❌ {error_msg}")
                        continue
            else:
                print(f"   ℹ️ No department specified (optional)")

            # Get password (default to username if not provided)
            password = row.get('password', '') or username
            print(f"   ✅ Password set: {'custom' if row.get('password', '') else 'default (username)'}")
            
            user_dict = {
                'username': username,
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
                'email': email,
                'role': role,
                'department_id': department_id,
                'password': password,
            }
            users_data.append(user_dict)
            print(f"   ✅ User data prepared: {username} ({role})")

        print(f"\n📊 CSV Parsing Summary:")
        print(f"   Total rows processed: {row_count}")
        print(f"   Valid users: {len(users_data)}")
        print(f"   Errors: {len(errors)}")
        
        if errors:
            print(f"\n❌ Errors found:")
            for error in errors:
                print(f"   - {error}")
        
        return users_data, errors
