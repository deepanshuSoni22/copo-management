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
    path('course-outcomes/create/', views.course_outcome_create, name='course_outcome_create'),
    path('course-outcomes/<int:pk>/update/', views.course_outcome_update, name='course_outcome_update'),
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
]