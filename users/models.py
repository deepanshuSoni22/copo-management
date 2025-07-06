# users/models.py

from django.db import models
from django.contrib.auth.models import User

# Enum for user roles
class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    HOD = 'HOD', 'Head of Department'
    FACULTY = 'FACULTY', 'Faculty'
    STUDENT = 'STUDENT', 'Student'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        verbose_name="User Role"
    )

    # This field is especially relevant for Students and HODs.
    department = models.ForeignKey(
        'academics.Department',  # Use 'app_name.ModelName' as a string
        on_delete=models.SET_NULL, # If a department is deleted, don't delete the user.
        null=True, 
        blank=True,
        related_name='user_profiles'
    )

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.get_role_display()})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
