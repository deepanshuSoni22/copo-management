# academics/urls.py (Add this below Department URLs)
from django.urls import path
from . import views

urlpatterns = [
    # Academic Year URLs (existing)
    path('academic-years/', views.academic_year_list, name='academic_year_list'),
    path('academic-years/create/', views.academic_year_create, name='academic_year_create'),
    path('academic-years/<int:pk>/update/', views.academic_year_update, name='academic_year_update'),
    path('academic-years/<int:pk>/delete/', views.academic_year_delete, name='academic_year_delete'),

    # Department URLs (existing)
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/update/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

     # AcademicDepartment URLs (NEW)
    path('academic-departments/', views.academic_department_list, name='academic_department_list'),
    path('academic-departments/create/', views.academic_department_create, name='academic_department_create'),
    path('academic-departments/<int:pk>/update/', views.academic_department_update, name='academic_department_update'),
    path('academic-departments/<int:pk>/delete/', views.academic_department_delete, name='academic_department_delete'),

     # Semester Management URLs (NEW)
    path('semesters/', views.semester_list, name='semester_list'),
    path('semesters/create/', views.semester_create, name='semester_create'),
    path('semesters/<int:pk>/update/', views.semester_update, name='semester_update'),
    path('semesters/<int:pk>/delete/', views.semester_delete, name='semester_delete'),

    # CoursePlan Management URLs (NEW)
    path('course-plans/', views.course_plan_list, name='course_plan_list'),
    path('course-plans/create/', views.course_plan_create, name='course_plan_create'),
    path('course-plans/<int:pk>/update/', views.course_plan_update, name='course_plan_update'),
    path('course-plans/<int:pk>/delete/', views.course_plan_delete, name='course_plan_delete'),


    # Program Outcome URLs (existing)
    path('program-outcomes/', views.program_outcome_list, name='program_outcome_list'),
    path('program-outcomes/create/', views.program_outcome_create, name='program_outcome_create'),
    path('program-outcomes/<int:pk>/update/', views.program_outcome_update, name='program_outcome_update'),
    path('program-outcomes/<int:pk>/delete/', views.program_outcome_delete, name='program_outcome_delete'),

    # Course URLs (existing)
    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/update/', views.course_update, name='course_update'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),

    # Course Outcome URLs (existing)
    path('course-outcomes/', views.course_outcome_list, name='course_outcome_list'),
    path('course-outcomes/<int:pk>/delete/', views.course_outcome_delete, name='course_outcome_delete'),

    # CO-PO Mapping URL (NEW)
    path('course-outcomes/<int:co_pk>/map/', views.copo_mapping_view, name='copo_mapping_view'),

    # Assessment Type URLs (NEW)
    path('assessment-types/', views.assessment_type_list, name='assessment_type_list'),
    path('assessment-types/create/', views.assessment_type_create, name='assessment_type_create'),
    path('assessment-types/<int:pk>/update/', views.assessment_type_update, name='assessment_type_update'),
    path('assessment-types/<int:pk>/delete/', views.assessment_type_delete, name='assessment_type_delete'),

    # Assessment Instance URLs (NEW)
    path('assessments/', views.assessment_list, name='assessment_list'),
    path('assessments/create/', views.assessment_create, name='assessment_create'),
    path('assessments/<int:pk>/update/', views.assessment_update, name='assessment_update'),
    path('assessments/<int:pk>/delete/', views.assessment_delete, name='assessment_delete'),

    # Student Mark Entry URL (NEW)
    path('assessments/<int:assessment_pk>/marks/', views.student_mark_entry, name='student_mark_entry'),

    # Attainment Calculation URL (NEW)
    path('calculate-attainment/', views.calculate_attainment_view, name='calculate_attainment_view'),

    # Attainment Display URLs (NEW)
    path('co-attainment-report/', views.co_attainment_report_list, name='co_attainment_report_list'),
    path('po-attainment-report/', views.po_attainment_report_list, name='po_attainment_report_list'),

   # Student Personal Views (NEW)
    path('my-marks/', views.student_personal_marks_view, name='student_personal_marks_view'),
    path('my-attainment/', views.student_personal_attainment_view, name='student_personal_attainment_view'), # NEW

    path('export/co-attainment-csv/', views.export_co_attainment_csv, name='export_co_attainment_csv'), # NEW

    path('faculty/create-student/', views.create_student_by_faculty, name='faculty_create_student'),

    path('faculty/assignments/', views.assignment_list, name='assignment_list'),
    path('faculty/assignments/create/', views.assignment_create, name='assignment_create'),
    path('faculty/assignments/<int:pk>/update/', views.assignment_update, name='assignment_update'),
    path('faculty/assignments/<int:pk>/delete/', views.assignment_delete, name='assignment_delete'),
    path('faculty/assignments/<int:assignment_pk>/submissions/', views.submission_list_for_assignment, name='submission_list_for_assignment'),
    path('faculty/assignments/<int:assignment_pk>/grade/<int:student_pk>/', views.grade_submission, name='grade_submission'),

    path('faculty/rubrics/', views.rubric_list, name='rubric_list'),
    path('faculty/rubrics/create/', views.rubric_create, name='rubric_create'),
    path('faculty/rubrics/<int:pk>/update/', views.rubric_update, name='rubric_update'),
    path('faculty/rubrics/<int:pk>/delete/', views.rubric_delete, name='rubric_delete'),

    path('students/', views.student_list, name='student_list'),
    path('student/assignments/', views.student_assignment_list, name='student_assignment_list'),
    path('student/assignments/<int:pk>/', views.assignment_detail_and_submit, name='assignment_detail_and_submit'),
    path('students/<int:pk>/update/', views.student_update_by_faculty, name='student_update_by_faculty'),
    path('students/<int:pk>/delete/', views.student_delete_by_faculty, name='student_delete_by_faculty'),
    path('students/<int:student_pk>/enroll/', views.enroll_student_view, name='enroll_student'),
    path('students/bulk-enroll-page/', views.bulk_enrollment_view, name='bulk_enrollment'),

    path('api/get-course-outcomes/<int:course_id>/', views.get_course_outcomes_api, name='get_course_outcomes_api'),
]

