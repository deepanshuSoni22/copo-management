# users/urls.py
from django.urls import path
from . import views # Import views from the current app
from users.models import UserProfile # Ensure UserProfile is imported for role checks if needed here

urlpatterns = [
    # Existing auth URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # NEW: User Management URLs
    path('management/', views.user_list, name='user_list'),
    path('management/create/', views.user_create, name='user_create'),
    path('management/<int:pk>/update/', views.user_update, name='user_update'),
    path('management/<int:pk>/delete/', views.user_delete, name='user_delete'),
]