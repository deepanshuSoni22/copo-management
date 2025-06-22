# copo_management_system/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from academics import views as academics_views # <--- ADD THIS NEW IMPORT


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='home/', permanent=False)),
    path('home/', academics_views.home_view, name='home'), # <--- THIS IS THE UPDATED LINE
    path('accounts/', include('users.urls')), # This includes login/logout from users
    # Include Academic Year URLs from the academics app
    path('academics/', include('academics.urls')), # All academics URLs will be prefixed with /academics/
]