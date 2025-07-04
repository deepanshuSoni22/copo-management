# academics/migrations/00XX_migrate_data_to_subjects.py

from django.db import migrations

def migrate_data_to_subjects(apps, schema_editor):
    """
    This function migrates data from the old Course model structure to the
    new Department -> Course(Program) -> Subject structure.
    """
    # Get the historical models for this migration
    Course_Program = apps.get_model('academics', 'Course')
    Subject = apps.get_model('academics', 'Subject')
    CourseOutcome = apps.get_model('academics', 'CourseOutcome')
    Assignment = apps.get_model('academics', 'Assignment')
    CoursePlan = apps.get_model('academics', 'CoursePlan')
    
    # We can't use the real UserProfile model here, so we get it from the registry
    UserProfile = apps.get_model('users', 'UserProfile')

    # Find all courses that need to be migrated (those with a semester, indicating they are subjects)
    old_courses_as_subjects = Course_Program.objects.filter(semester__isnull=False)

    for old_course in old_courses_as_subjects:
        # The parent program is the new Course model linked to the old course's department
        program = old_course.department.courses.first()

        if not program:
            # This is a fallback in case the program doesn't exist yet
            print(f"Warning: Could not find a parent Program for Department '{old_course.department.name}'. Skipping subject '{old_course.name}'.")
            continue

        # Create a new Subject object based on the old Course data
        new_subject = Subject.objects.create(
            course=program,
            name=old_course.name,
            code=old_course.code,
            semester=old_course.semester,
            credits=old_course.credits,
            prerequisites=old_course.prerequisites,
        )

        # Copy over the ManyToMany relationship for faculty
        faculty_profiles = old_course.faculty.all()
        new_subject.faculty.set(faculty_profiles)

        # Re-link child objects from the old Course to the new Subject
        CourseOutcome.objects.filter(course=old_course).update(subject=new_subject)
        Assignment.objects.filter(course=old_course).update(subject=new_subject)
        
        try:
            course_plan = CoursePlan.objects.get(course=old_course)
            course_plan.subject = new_subject
            course_plan.save()
        except CoursePlan.DoesNotExist:
            pass

class Migration(migrations.Migration):

    dependencies = [
        # IMPORTANT: Replace '0018_...' with the name of your PREVIOUS migration file
        ('academics', '0014_alter_assessment_max_marks_and_more'),  # ✅ Fixed
        ('users', '0005_remove_userprofile_department_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_data_to_subjects),
    ]