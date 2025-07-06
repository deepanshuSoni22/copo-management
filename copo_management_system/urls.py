# copo_management_system/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from academics import views as academics_views # <--- ADD THIS NEW IMPORT

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='home/', permanent=False)),
    path('home/', academics_views.home_view, name='home'), # <--- THIS IS THE UPDATED LINE
    path('accounts/', include('users.urls')), # This includes login/logout from users
    # Include Academic Year URLs from the academics app
    path('academics/', include('academics.urls')), # All academics URLs will be prefixed with /academics/
]

# --- Add this block at the end ---
# This serves media files from MEDIA_ROOT during development (i.e., when DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)