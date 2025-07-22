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

# Create a superuser if one doesn't already exist.
# This uses the DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL,
# and DJANGO_SUPERUSER_PASSWORD environment variables you set on Render.
# The --noinput flag makes it non-interactive.
# The '|| true' ensures the script doesn't fail if the user already exists.
echo "Attempting to create or verify superuser using createsuperuser --noinput..."
python manage.py createsuperuser --noinput || true
echo "Superuser creation/verification step completed."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input
echo "Static files collected."

echo "Build process finished successfully."