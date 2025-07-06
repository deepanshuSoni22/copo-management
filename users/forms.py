# users/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
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
