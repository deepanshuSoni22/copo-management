#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process for copo-app..."

# Install dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt
echo "Python dependencies installed."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate
echo "Database migrations completed."

# Ensure the superuser has correct permissions (even if it already exists)
echo "Ensuring superuser 'admin' has staff and superuser permissions..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model

User = get_user_model()
try:
    user = User.objects.get(username='${DJANGO_SUPERUSER_USERNAME}')
    if not user.is_staff or not user.is_superuser:
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"User '{user.username}' permissions updated to staff and superuser.")
    else:
        print(f"User '{user.username}' already has staff and superuser permissions.")
except User.DoesNotExist:
    # If user doesn't exist, create it.
    User.objects.create_superuser('${DJANGO_SUPERUSER_USERNAME}', '${DJANGO_SUPERUSER_EMAIL}', '${DJANGO_SUPERUSER_PASSWORD}')
    print("Superuser created as it did not exist.")
except Exception as e:
    print(f"An error occurred during superuser update/creation: {e}")
EOF
echo "Superuser permissions check/update completed."

# Backfill user profiles to ensure admin has a UserProfile (needed by views/templates)
echo "Backfilling UserProfile entries and enforcing ADMIN role for superusers..."
python manage.py backfill_user_profiles
echo "Backfill completed."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input
echo "Static files collected."

echo "Build process finished successfully."