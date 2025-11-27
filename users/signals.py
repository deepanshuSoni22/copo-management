from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, UserRole


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance: User, created: bool, **kwargs):
    """
    Ensure every User has a corresponding UserProfile.

    - On creation: create a profile and assign role based on user type
      (ADMIN if superuser, STUDENT by default otherwise).
    - On save: keep the profile in sync if it exists, without overriding
      non-admin roles accidentally.
    """
    if created:
        # Determine default role
        default_role = UserRole.ADMIN if instance.is_superuser else UserRole.STUDENT
        UserProfile.objects.create(user=instance, role=default_role)
    else:
        # For existing users, ensure profile exists (e.g., if created via script)
        try:
            profile = instance.profile
        except UserProfile.DoesNotExist:
            default_role = UserRole.ADMIN if instance.is_superuser else UserRole.STUDENT
            UserProfile.objects.create(user=instance, role=default_role)
        else:
            # If superuser, enforce ADMIN role; otherwise keep current role
            if instance.is_superuser and profile.role != UserRole.ADMIN:
                profile.role = UserRole.ADMIN
                profile.save(update_fields=["role"])