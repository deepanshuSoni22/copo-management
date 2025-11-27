from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from users.models import UserProfile, UserRole


class Command(BaseCommand):
    help = "Ensure all Users have a UserProfile; set ADMIN role for superusers."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for user in User.objects.all():
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": UserRole.ADMIN if user.is_superuser else UserRole.STUDENT,
                },
            )
            if created:
                created_count += 1
            else:
                # Enforce ADMIN role for superusers
                if user.is_superuser and profile.role != UserRole.ADMIN:
                    profile.role = UserRole.ADMIN
                    profile.save(update_fields=["role"])
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. Profiles created: {created_count}, admin roles updated: {updated_count}."
            )
        )