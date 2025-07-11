# Generated by Django 5.2.3 on 2025-07-05 04:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("academics", "0001_initial"),
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="academicdepartment",
            name="hod",
            field=models.OneToOneField(
                blank=True,
                limit_choices_to={"role__in": ["HOD", "FACULTY"]},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="academic_department_headed",
                to="users.userprofile",
                verbose_name="Head of Department (for this Academic Year)",
            ),
        ),
        migrations.AddField(
            model_name="academicdepartment",
            name="academic_year",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="academic_departments",
                to="academics.academicyear",
            ),
        ),
        migrations.AddField(
            model_name="assessment",
            name="academic_year",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assessments",
                to="academics.academicyear",
            ),
        ),
        migrations.AddField(
            model_name="assessment",
            name="assessment_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assessments",
                to="academics.assessmenttype",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_assignments",
                to="users.userprofile",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="cia_component",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assignments",
                to="academics.ciacomponent",
            ),
        ),
        migrations.CreateModel(
            name="CoursePlan",
            fields=[
                (
                    "course",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="course_plan",
                        serialize=False,
                        to="academics.course",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="e.g., Course Plan for AI (V SEM A & B)",
                        max_length=255,
                    ),
                ),
                (
                    "classes_per_week",
                    models.PositiveIntegerField(
                        default=4,
                        help_text="Number of classes scheduled per week for this course.",
                    ),
                ),
                (
                    "total_hours_allotted",
                    models.PositiveIntegerField(
                        default=60,
                        help_text="Total hours allotted for the entire course.",
                    ),
                ),
                (
                    "assessment_ratio",
                    models.CharField(
                        blank=True,
                        help_text="The ratio of internal to external assessment marks, e.g., 60:40",
                        max_length=20,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course_coordinator",
                    models.ForeignKey(
                        blank=True,
                        help_text="Primary person responsible for the course plan.",
                        limit_choices_to={"role__in": ["FACULTY", "HOD"]},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="coordinated_course_plans",
                        to="users.userprofile",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_course_plans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "instructors",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Other instructors assigned to this course (if any).",
                        related_name="instructed_course_plans",
                        to="users.userprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course Plan",
                "verbose_name_plural": "Course Plans",
                "ordering": [
                    "-course__semester__academic_department__academic_year__start_date",
                    "course__code",
                ],
            },
        ),
        migrations.AddField(
            model_name="course",
            name="faculty",
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={"role": "FACULTY"},
                related_name="taught_courses",
                to="users.userprofile",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="students",
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={"role": "STUDENT"},
                related_name="enrolled_courses",
                to="users.userprofile",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assignments",
                to="academics.course",
            ),
        ),
        migrations.AddField(
            model_name="assessment",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assessments",
                to="academics.course",
            ),
        ),
        migrations.AddField(
            model_name="courseoutcome",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="course_outcomes",
                to="academics.course",
            ),
        ),
        migrations.AddField(
            model_name="copomapping",
            name="course_outcome",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="po_mappings",
                to="academics.courseoutcome",
            ),
        ),
        migrations.AddField(
            model_name="ciacomponent",
            name="cos_covered",
            field=models.ManyToManyField(
                blank=True, related_name="cia_assessed_by", to="academics.courseoutcome"
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="assesses_cos",
            field=models.ManyToManyField(
                blank=True,
                help_text="Select the Course Outcomes that this assignment assesses.",
                related_name="assessed_by_assignments",
                to="academics.courseoutcome",
            ),
        ),
        migrations.AddField(
            model_name="assessment",
            name="assesses_cos",
            field=models.ManyToManyField(
                blank=True,
                related_name="assessed_by_assessments",
                to="academics.courseoutcome",
            ),
        ),
        migrations.AddField(
            model_name="courseoutcomeattainment",
            name="academic_year",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="co_attainments",
                to="academics.academicyear",
            ),
        ),
        migrations.AddField(
            model_name="courseoutcomeattainment",
            name="course_outcome",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attainments",
                to="academics.courseoutcome",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="courses",
                to="academics.department",
            ),
        ),
        migrations.AddField(
            model_name="academicdepartment",
            name="department",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="academic_departments",
                to="academics.department",
            ),
        ),
        migrations.AddField(
            model_name="programoutcome",
            name="department",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="program_outcomes",
                to="academics.department",
            ),
        ),
        migrations.AddField(
            model_name="copomapping",
            name="program_outcome",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="co_mappings",
                to="academics.programoutcome",
            ),
        ),
        migrations.AddField(
            model_name="programoutcomeattainment",
            name="academic_year",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="po_attainments",
                to="academics.academicyear",
            ),
        ),
        migrations.AddField(
            model_name="programoutcomeattainment",
            name="program_outcome",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attainments",
                to="academics.programoutcome",
            ),
        ),
        migrations.AddField(
            model_name="rubric",
            name="created_by",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rubrics",
                to="users.userprofile",
            ),
        ),
        migrations.AddField(
            model_name="assignment",
            name="rubric",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assignments",
                to="academics.rubric",
            ),
        ),
        migrations.AddField(
            model_name="rubriccriterion",
            name="rubric",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="criteria",
                to="academics.rubric",
            ),
        ),
        migrations.AddField(
            model_name="rubricscore",
            name="criterion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="academics.rubriccriterion",
            ),
        ),
        migrations.AddField(
            model_name="semester",
            name="academic_department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="semesters",
                to="academics.academicdepartment",
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="semester",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="courses",
                to="academics.semester",
            ),
        ),
        migrations.AddField(
            model_name="studentmark",
            name="assessment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="student_marks",
                to="academics.assessment",
            ),
        ),
        migrations.AddField(
            model_name="studentmark",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assessment_marks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="assignment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="submissions",
                to="academics.assignment",
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="graded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="graded_submissions",
                to="users.userprofile",
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="student",
            field=models.ForeignKey(
                limit_choices_to={"role": "STUDENT"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="submissions",
                to="users.userprofile",
            ),
        ),
        migrations.AddField(
            model_name="rubricscore",
            name="submission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rubric_scores",
                to="academics.submission",
            ),
        ),
        migrations.AddField(
            model_name="weeklylessonplan",
            name="course_plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="weekly_lesson_plans",
                to="academics.courseplan",
            ),
        ),
        migrations.AddField(
            model_name="courseobjective",
            name="course_plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="course_objectives",
                to="academics.courseplan",
            ),
        ),
        migrations.AddField(
            model_name="ciacomponent",
            name="course_plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cia_components",
                to="academics.courseplan",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="courseoutcome",
            unique_together={("course", "code")},
        ),
        migrations.AlterUniqueTogether(
            name="assessment",
            unique_together={("name", "course", "academic_year")},
        ),
        migrations.AlterUniqueTogether(
            name="courseoutcomeattainment",
            unique_together={("course_outcome", "academic_year")},
        ),
        migrations.AlterUniqueTogether(
            name="academicdepartment",
            unique_together={("department", "academic_year")},
        ),
        migrations.AlterUniqueTogether(
            name="programoutcome",
            unique_together={("department", "code")},
        ),
        migrations.AlterUniqueTogether(
            name="copomapping",
            unique_together={("course_outcome", "program_outcome")},
        ),
        migrations.AlterUniqueTogether(
            name="programoutcomeattainment",
            unique_together={("program_outcome", "academic_year")},
        ),
        migrations.AlterUniqueTogether(
            name="semester",
            unique_together={("name", "academic_department")},
        ),
        migrations.AlterUniqueTogether(
            name="course",
            unique_together={("code", "semester")},
        ),
        migrations.AlterUniqueTogether(
            name="studentmark",
            unique_together={("assessment", "student")},
        ),
        migrations.AlterUniqueTogether(
            name="submission",
            unique_together={("assignment", "student")},
        ),
        migrations.AlterUniqueTogether(
            name="rubricscore",
            unique_together={("submission", "criterion")},
        ),
        migrations.AlterUniqueTogether(
            name="weeklylessonplan",
            unique_together={("course_plan", "order")},
        ),
        migrations.AlterUniqueTogether(
            name="courseobjective",
            unique_together={("course_plan", "order")},
        ),
        migrations.AlterUniqueTogether(
            name="ciacomponent",
            unique_together={("course_plan", "component_name")},
        ),
    ]
