# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy  # Used for reverse lookups in class-based views
from django.contrib import messages  # For displaying feedback messages

from django.contrib.auth.models import User  # Import Django's User model
from .models import UserProfile, UserRole  # Import your custom models and choices
from .forms import UserCreateForm, UserUpdateForm  # Import your new custom forms


# --- Existing Login/Logout Views ---
class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("home")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("login")


# --- Helper for Admin permission (from academics/views.py, copied here for self-containment) ---
def is_admin(user):
    return (
        user.is_authenticated and user.profile.role == UserRole.ADMIN
    )  # Use UserRole directly here


# --- Custom User Management Views ---


@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")  # Only Admin can manage users
def user_list(request):
    users = User.objects.all().select_related("profile").order_by("username")
    # Can filter by role here if desired:
    # role_filter = request.GET.get('role')
    # if role_filter:
    #    users = users.filter(profile__role=role_filter)
    context = {
        "users": users,
        "form_title": "User Management",
        "roles": UserRole.choices,  # Pass roles for filter options if needed
    }
    return render(request, "users/user_list.html", context)


@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")  # Only Admin
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"User '{user.username}' created successfully with role '{user.profile.get_role_display()}'!",
            )
            return redirect("user_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreateForm()
    context = {
        "form": form,
        "form_title": "Create New User",
    }
    return render(request, "users/user_form.html", context)


@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")  # Only Admin
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)

    # Prevent admin from changing their own superuser status or deleting themselves (can be refined)
    if user.is_superuser and request.user != user:
        messages.error(
            request,
            "Superuser status can only be managed by another superuser in Django admin directly.",
        )
        return redirect("user_list")
    if (
        request.user == user and request.user.is_superuser
    ):  # Prevent superuser from downgrading/deleting self
        messages.warning(
            request,
            "You cannot modify your own superuser status or delete yourself via this interface.",
        )
        # Optionally, restrict fields like is_superuser on the form based on request.user

    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            updated_user = form.save()
            messages.success(
                request,
                f"User '{updated_user.username}' updated successfully with role '{updated_user.profile.get_role_display()}'!",
            )
            return redirect("user_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserUpdateForm(
            instance=user, request=request
        )  # Pass request to the form
    context = {
        "form": form,
        "form_title": f"Update User: {user.username}",
        "target_user": user,
    }
    return render(request, "users/user_form.html", context)


@login_required
@user_passes_test(is_admin, login_url="/accounts/login/")  # Only Admin
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    # Prevent user from deleting themselves
    if request.user == user:
        messages.error(
            request, "You cannot delete your own user account via this interface."
        )
        return redirect("user_list")
    # Prevent deleting superusers via this interface (force to Django Admin if needed)
    if user.is_superuser:
        messages.error(
            request,
            "Superusers cannot be deleted via this interface. Please use Django admin.",
        )
        return redirect("user_list")

    if request.method == "POST":
        user.delete()
        messages.success(
            request, f"User '{user.username}' and their profile deleted successfully."
        )
        return redirect("user_list")
    context = {
        "target_user": user,
    }
    return render(request, "users/user_confirm_delete.html", context)
